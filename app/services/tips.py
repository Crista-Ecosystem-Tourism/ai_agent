from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Literal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.tip_policy import (
    TIP_DAILY_SUBMISSION_LIMIT,
    TIP_DAILY_REPORT_LIMIT,
    TIP_MAX_OPEN_DRAFTS,
    TIP_REPORT_REASONS,
    TIP_SUBMISSION_WINDOW_HOURS,
    clean_moderation_note,
    clean_tip_body,
)
from app.db.models.auth import User
from app.db.models.game import GameCity, GameContentRevision, GameQuest
from app.db.models.tip import GameTip, GameTipModerationAction, GameTipReport


class TipNotFoundError(RuntimeError):
    pass


class TipPermissionError(RuntimeError):
    pass


class TipTargetUnavailableError(RuntimeError):
    pass


class TipDuplicateReportError(RuntimeError):
    pass


class TipRateLimitError(RuntimeError):
    pass


class TipService:
    """Server-owned tips with immutable publication decisions and a readable audit trail."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        clock=lambda: datetime.now(timezone.utc),
    ):
        self.session_factory = session_factory
        self._clock = clock

    async def list_published(self, quest_id: str) -> list[dict]:
        async with self.session_factory() as db:
            if not await self._published_quest_exists(db, quest_id):
                raise TipTargetUnavailableError
            rows = (await db.execute(
                select(GameTip, User.name)
                .join(User, User.id == GameTip.author_id)
                .where(GameTip.quest_id == quest_id, GameTip.status == "published")
                .order_by(GameTip.reviewed_at.desc(), GameTip.id)
            )).all()
            return [self._tip_payload(tip, author_name) for tip, author_name in rows]

    async def list_mine(self, user_id: str) -> list[dict]:
        async with self.session_factory() as db:
            rows = (await db.execute(
                select(GameTip)
                .where(GameTip.author_id == user_id)
                .order_by(GameTip.updated_at.desc())
            )).scalars().all()
            return [self._tip_payload(tip, None, include_decision=True) for tip in rows]

    async def create_draft(self, user_id: str, quest_id: str, body: str) -> dict:
        cleaned_body = clean_tip_body(body)
        async with self.session_factory() as db:
            user = await db.scalar(select(User).where(User.id == user_id).with_for_update())
            if user is None:
                raise TipNotFoundError
            if not await self._published_quest_exists(db, quest_id):
                raise TipTargetUnavailableError
            open_drafts = await db.scalar(select(func.count()).select_from(GameTip).where(
                GameTip.author_id == user_id, GameTip.status == "draft",
            )) or 0
            if open_drafts >= TIP_MAX_OPEN_DRAFTS:
                raise TipRateLimitError
            now = self._clock()
            tip = GameTip(
                id=uuid.uuid4().hex,
                quest_id=quest_id,
                author_id=user_id,
                body=cleaned_body,
                status="draft",
                created_at=now,
                updated_at=now,
            )
            db.add(tip)
            self._record_action(db, tip.id, user_id, "draft_created", {"quest_id": quest_id}, now)
            await db.commit()
            return self._tip_payload(tip, None)

    async def update_draft(self, user_id: str, tip_id: str, body: str) -> dict:
        cleaned_body = clean_tip_body(body)
        async with self.session_factory() as db:
            tip = await db.scalar(select(GameTip).where(
                GameTip.id == tip_id, GameTip.author_id == user_id,
            ).with_for_update())
            if tip is None:
                raise TipNotFoundError
            if tip.status != "draft":
                raise ValueError("Можно редактировать только черновик")
            now = self._clock()
            tip.body = cleaned_body
            tip.updated_at = now
            self._record_action(db, tip.id, user_id, "draft_updated", {}, now)
            await db.commit()
            return self._tip_payload(tip, None)

    async def delete_draft(self, user_id: str, tip_id: str) -> None:
        async with self.session_factory() as db:
            tip = await db.scalar(select(GameTip).where(
                GameTip.id == tip_id, GameTip.author_id == user_id,
            ).with_for_update())
            if tip is None:
                raise TipNotFoundError
            if tip.status != "draft":
                raise ValueError("Можно удалить только черновик")
            now = self._clock()
            self._record_action(db, tip.id, user_id, "draft_deleted", {"quest_id": tip.quest_id}, now)
            await db.flush()
            await db.delete(tip)
            await db.commit()

    async def submit(self, user_id: str, tip_id: str) -> dict:
        async with self.session_factory() as db:
            user = await db.scalar(select(User).where(User.id == user_id).with_for_update())
            if user is None:
                raise TipNotFoundError
            tip = await db.scalar(select(GameTip).where(
                GameTip.id == tip_id, GameTip.author_id == user_id,
            ).with_for_update())
            if tip is None:
                raise TipNotFoundError
            if tip.status != "draft":
                raise ValueError("Отправить можно только черновик")
            now = self._clock()
            cutoff = now - timedelta(hours=TIP_SUBMISSION_WINDOW_HOURS)
            submission_count = await db.scalar(select(func.count()).select_from(GameTipModerationAction).where(
                GameTipModerationAction.actor_id == user_id,
                GameTipModerationAction.action == "submitted_for_review",
                GameTipModerationAction.created_at >= cutoff,
            )) or 0
            if submission_count >= TIP_DAILY_SUBMISSION_LIMIT:
                raise TipRateLimitError
            tip.status = "review"
            tip.submitted_at = now
            tip.updated_at = now
            self._record_action(db, tip.id, user_id, "submitted_for_review", {}, now)
            await db.commit()
            return self._tip_payload(tip, None)

    async def report(
        self, reporter_id: str, tip_id: str, reason: str, details: str | None = None,
    ) -> dict:
        if reason not in TIP_REPORT_REASONS:
            raise ValueError("Неизвестная причина жалобы")
        note = clean_moderation_note(details)
        async with self.session_factory() as db:
            reporter = await db.scalar(select(User).where(User.id == reporter_id).with_for_update())
            if reporter is None:
                raise TipNotFoundError
            tip = await db.scalar(select(GameTip).where(GameTip.id == tip_id).with_for_update())
            if tip is None or tip.status != "published":
                raise TipNotFoundError
            if tip.author_id == reporter_id:
                raise TipPermissionError
            cutoff = self._clock() - timedelta(hours=TIP_SUBMISSION_WINDOW_HOURS)
            report_count = await db.scalar(select(func.count()).select_from(GameTipModerationAction).where(
                GameTipModerationAction.actor_id == reporter_id,
                GameTipModerationAction.action == "tip_reported",
                GameTipModerationAction.created_at >= cutoff,
            )) or 0
            if report_count >= TIP_DAILY_REPORT_LIMIT:
                raise TipRateLimitError
            existing = await db.scalar(select(GameTipReport.id).where(
                GameTipReport.tip_id == tip_id,
                GameTipReport.reporter_id == reporter_id,
            ))
            if existing is not None:
                raise TipDuplicateReportError
            now = self._clock()
            report = GameTipReport(
                id=uuid.uuid4().hex,
                tip_id=tip.id,
                reporter_id=reporter_id,
                reason=reason,
                details=note,
                status="pending",
                created_at=now,
            )
            db.add(report)
            self._record_action(db, tip.id, reporter_id, "tip_reported", {"report_id": report.id, "reason": reason}, now, report.id)
            await db.commit()
            return {"id": report.id, "tip_id": tip_id, "status": report.status, "created_at": now.isoformat()}

    async def list_review_queue(self, editor_id: str) -> list[dict]:
        async with self.session_factory() as db:
            self._require_editor(await db.get(User, editor_id))
            rows = (await db.execute(
                select(GameTip, User.name)
                .join(User, User.id == GameTip.author_id)
                .where(GameTip.status == "review")
                .order_by(GameTip.submitted_at, GameTip.id)
            )).all()
            return [self._tip_payload(tip, author_name, include_decision=True) for tip, author_name in rows]

    async def decide(
        self,
        editor_id: str,
        tip_id: str,
        decision: Literal["publish", "reject", "hide"],
        note: str | None = None,
    ) -> dict:
        cleaned_note = clean_moderation_note(note)
        async with self.session_factory() as db:
            self._require_editor(await db.get(User, editor_id))
            tip = await db.scalar(select(GameTip).where(GameTip.id == tip_id).with_for_update())
            if tip is None:
                raise TipNotFoundError
            transitions = {"publish": ("review", "published"), "reject": ("review", "rejected"), "hide": ("published", "hidden")}
            expected_status, next_status = transitions[decision]
            if tip.status != expected_status:
                raise ValueError(f"Нельзя выполнить {decision} для заметки со статусом {tip.status}")
            now = self._clock()
            tip.status = next_status
            tip.updated_at = now
            tip.reviewed_at = now
            tip.reviewed_by_id = editor_id
            tip.decision_note = cleaned_note
            self._record_action(db, tip.id, editor_id, f"tip_{decision}", {"note": cleaned_note}, now)
            await db.commit()
            return self._tip_payload(tip, None)

    async def list_reports(self, editor_id: str, pending_only: bool = True) -> list[dict]:
        async with self.session_factory() as db:
            self._require_editor(await db.get(User, editor_id))
            query = (
                select(GameTipReport, GameTip, GameQuest.id, User.name)
                .join(GameTip, GameTip.id == GameTipReport.tip_id)
                .join(GameQuest, GameQuest.id == GameTip.quest_id)
                .join(User, User.id == GameTipReport.reporter_id)
                .order_by(GameTipReport.created_at.asc())
            )
            if pending_only:
                query = query.where(GameTipReport.status == "pending")
            rows = (await db.execute(query)).all()
            return [self._report_payload(report, tip, quest_id, reporter_name) for report, tip, quest_id, reporter_name in rows]

    async def resolve_report(
        self,
        editor_id: str,
        report_id: str,
        resolution: Literal["dismiss", "hide_tip"],
        note: str | None = None,
    ) -> dict:
        cleaned_note = clean_moderation_note(note)
        async with self.session_factory() as db:
            self._require_editor(await db.get(User, editor_id))
            report = await db.scalar(select(GameTipReport).where(GameTipReport.id == report_id).with_for_update())
            if report is None:
                raise TipNotFoundError
            if report.status != "pending":
                raise ValueError("Жалоба уже обработана")
            tip = await db.scalar(select(GameTip).where(GameTip.id == report.tip_id).with_for_update())
            now = self._clock()
            if resolution == "hide_tip":
                if tip is not None and tip.status == "published":
                    tip.status = "hidden"
                    tip.updated_at = now
                    tip.reviewed_at = now
                    tip.reviewed_by_id = editor_id
                    tip.decision_note = cleaned_note
                    self._record_action(db, tip.id, editor_id, "tip_hidden", {"source": "report", "report_id": report.id, "note": cleaned_note}, now, report.id)
                report.status = "resolved"
            else:
                report.status = "dismissed"
            report.resolved_at = now
            report.resolved_by_id = editor_id
            report.resolution_note = cleaned_note
            self._record_action(db, report.tip_id, editor_id, f"report_{resolution}", {"report_id": report.id, "note": cleaned_note}, now, report.id)
            await db.commit()
            return {"id": report.id, "status": report.status, "resolved_at": now.isoformat()}

    async def list_audit(self, editor_id: str, limit: int = 100) -> list[dict]:
        async with self.session_factory() as db:
            self._require_editor(await db.get(User, editor_id))
            rows = (await db.execute(
                select(GameTipModerationAction, User.name)
                .outerjoin(User, User.id == GameTipModerationAction.actor_id)
                .order_by(GameTipModerationAction.created_at.desc(), GameTipModerationAction.id.desc())
                .limit(min(max(limit, 1), 200))
            )).all()
            return [
                {"id": action.id, "tip_id": action.tip_id, "report_id": action.report_id,
                 "actor_name": actor_name, "action": action.action, "details": action.details,
                 "created_at": action.created_at.isoformat()}
                for action, actor_name in rows
            ]

    @staticmethod
    async def _published_quest_exists(db: AsyncSession, quest_id: str) -> bool:
        return bool(await db.scalar(
            select(GameQuest.id)
            .join(GameCity, GameCity.id == GameQuest.city_id)
            .join(GameContentRevision, GameContentRevision.id == GameQuest.content_revision_id)
            .where(
                GameQuest.id == quest_id,
                GameQuest.is_published.is_(True),
                GameCity.is_published.is_(True),
                GameContentRevision.is_published.is_(True),
            )
        ))

    @staticmethod
    def _require_editor(user: User | None) -> None:
        if user is None or not user.is_editor:
            raise TipPermissionError

    @staticmethod
    def _record_action(
        db: AsyncSession,
        tip_id: str | None,
        actor_id: str | None,
        action: str,
        details: dict,
        now: datetime,
        report_id: str | None = None,
    ) -> None:
        db.add(GameTipModerationAction(
            id=uuid.uuid4().hex, tip_id=tip_id, report_id=report_id, actor_id=actor_id,
            action=action, details=details, created_at=now,
        ))

    @staticmethod
    def _tip_payload(tip: GameTip, author_name: str | None, include_decision: bool = False) -> dict:
        payload = {
            "id": tip.id, "quest_id": tip.quest_id, "author_name": author_name,
            "body": tip.body, "status": tip.status, "created_at": tip.created_at.isoformat(),
            "updated_at": tip.updated_at.isoformat(),
            "submitted_at": tip.submitted_at.isoformat() if tip.submitted_at else None,
        }
        if include_decision:
            payload["decision_note"] = tip.decision_note
        return payload

    @staticmethod
    def _report_payload(report: GameTipReport, tip: GameTip, quest_id: str, reporter_name: str) -> dict:
        return {
            "id": report.id, "tip_id": report.tip_id, "quest_id": quest_id,
            "tip_body": tip.body, "reason": report.reason, "details": report.details,
            "status": report.status, "reporter_name": reporter_name,
            "created_at": report.created_at.isoformat(),
        }
