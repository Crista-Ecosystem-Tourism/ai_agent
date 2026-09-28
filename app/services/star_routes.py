from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlsplit

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.api.schemas import Place
from app.core.services.route import RouteService
from app.db.models.auth import User
from app.db.models.star_route import StarRouteCandidate, StarRouteSegment, StarRouteTranscript


class StarRouteNotFoundError(RuntimeError):
    pass


class StarRouteValidationError(ValueError):
    pass


class StarRouteRoutingUnavailable(RuntimeError):
    pass


class StarRouteService:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession], http_client: httpx.AsyncClient):
        self.session_factory = session_factory
        self.http_client = http_client

    async def register_transcript(self, editor_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        await self._require_editor(editor_id)
        source_url = self._https_url(payload["source_url"], "Ссылка на источник")
        now = datetime.now(timezone.utc)
        transcript = StarRouteTranscript(
            id=uuid.uuid4().hex,
            title=payload["title"].strip(),
            source_url=source_url,
            author_name=self._optional_text(payload.get("author_name"), 160),
            rights_basis=payload["rights_basis"],
            registered_by=editor_id,
            created_at=now,
            updated_at=now,
        )
        async with self.session_factory() as db:
            db.add(transcript)
            await db.commit()
        return self._transcript_payload(transcript)

    async def add_segment(self, editor_id: str, transcript_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        await self._require_editor(editor_id)
        if payload["end_seconds"] <= payload["start_seconds"]:
            raise StarRouteValidationError("Конец таймкода должен быть позже начала")
        now = datetime.now(timezone.utc)
        async with self.session_factory() as db:
            if await db.get(StarRouteTranscript, transcript_id) is None:
                raise StarRouteNotFoundError(transcript_id)
            segment = StarRouteSegment(
                id=uuid.uuid4().hex,
                transcript_id=transcript_id,
                start_seconds=payload["start_seconds"],
                end_seconds=payload["end_seconds"],
                excerpt=payload["excerpt"].strip(),
                extracted_place_name=payload["extracted_place_name"].strip(),
                created_at=now,
                updated_at=now,
            )
            db.add(segment)
            await db.commit()
        return self._segment_payload(segment)

    async def create_candidate(self, editor_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        await self._require_editor(editor_id)
        transcript_id = payload["transcript_id"]
        pois = payload["pois"]
        if len({poi["segment_id"] for poi in pois}) != len(pois):
            raise StarRouteValidationError("Нельзя использовать один сегмент для двух точек кандидата")
        normalized_pois = [self._normalize_poi(poi, index) for index, poi in enumerate(pois)]
        async with self.session_factory() as db:
            transcript = await db.get(StarRouteTranscript, transcript_id)
            if transcript is None:
                raise StarRouteNotFoundError(transcript_id)
            segments = list((await db.scalars(
                select(StarRouteSegment).where(
                    StarRouteSegment.transcript_id == transcript_id,
                    StarRouteSegment.id.in_([poi["segment_id"] for poi in normalized_pois]),
                )
            )).all())
            if {segment.id for segment in segments} != {poi["segment_id"] for poi in normalized_pois}:
                raise StarRouteValidationError("Каждая точка должна ссылаться на сегмент этого транскрипта")

        route = await RouteService.build_route([
            Place(
                id=poi.get("poi_id"), name=poi["name"], city=payload["destination"],
                latitude=poi["latitude"], longitude=poi["longitude"],
            )
            for poi in normalized_pois
        ], self.http_client)
        if route is None:
            raise StarRouteRoutingUnavailable("Маршрутный сервис временно недоступен")

        now = datetime.now(timezone.utc)
        candidate = StarRouteCandidate(
            id=uuid.uuid4().hex,
            transcript_id=transcript_id,
            title=payload["title"].strip(),
            destination=payload["destination"].strip(),
            pois=normalized_pois,
            route_geojson=route.geojson,
            status="review",
            created_at=now,
            updated_at=now,
        )
        async with self.session_factory() as db:
            db.add(candidate)
            await db.commit()
        return self._candidate_payload(candidate, segments, transcript)

    async def list_review_queue(self, editor_id: str) -> list[dict[str, Any]]:
        await self._require_editor(editor_id)
        async with self.session_factory() as db:
            candidates = list((await db.scalars(
                select(StarRouteCandidate)
                .where(StarRouteCandidate.status == "review")
                .order_by(StarRouteCandidate.created_at.asc())
            )).all())
            return await self._candidate_payloads(db, candidates)

    async def publish_candidate(self, editor_id: str, candidate_id: str) -> dict[str, Any]:
        await self._require_editor(editor_id)
        now = datetime.now(timezone.utc)
        async with self.session_factory() as db:
            candidate = await db.get(StarRouteCandidate, candidate_id)
            if candidate is None:
                raise StarRouteNotFoundError(candidate_id)
            if candidate.status != "review":
                raise StarRouteValidationError("Опубликовать можно только кандидат на review")
            if not candidate.pois or not candidate.route_geojson:
                raise StarRouteValidationError("Кандидату нужны POI и рассчитанная геометрия")
            transcript = await db.get(StarRouteTranscript, candidate.transcript_id)
            if transcript is None:
                raise StarRouteValidationError("Кандидат потерял источник транскрипта")
            candidate.status = "published"
            candidate.reviewed_by = editor_id
            candidate.reviewed_at = now
            candidate.published_at = now
            candidate.updated_at = now
            segments = list((await db.scalars(
                select(StarRouteSegment).where(
                    StarRouteSegment.transcript_id == candidate.transcript_id,
                    StarRouteSegment.id.in_([poi["segment_id"] for poi in candidate.pois]),
                )
            )).all())
            if len(segments) != len(candidate.pois):
                raise StarRouteValidationError("Кандидат потерял ссылку на транскриптный сегмент")
            await db.commit()
        return self._candidate_payload(candidate, segments, transcript)

    async def list_published(self) -> list[dict[str, Any]]:
        async with self.session_factory() as db:
            candidates = list((await db.scalars(
                select(StarRouteCandidate)
                .where(StarRouteCandidate.status == "published")
                .order_by(StarRouteCandidate.published_at.desc())
            )).all())
            return await self._candidate_payloads(db, candidates)

    async def _candidate_payloads(self, db: AsyncSession, candidates: list[StarRouteCandidate]) -> list[dict[str, Any]]:
        if not candidates:
            return []
        transcript_ids = {candidate.transcript_id for candidate in candidates}
        transcripts = {
            transcript.id: transcript
            for transcript in (await db.scalars(
                select(StarRouteTranscript).where(StarRouteTranscript.id.in_(transcript_ids))
            )).all()
        }
        segment_ids = {poi["segment_id"] for candidate in candidates for poi in candidate.pois}
        segments = {
            segment.id: segment
            for segment in (await db.scalars(
                select(StarRouteSegment).where(StarRouteSegment.id.in_(segment_ids))
            )).all()
        } if segment_ids else {}
        return [self._candidate_payload(candidate, [segments[poi["segment_id"]] for poi in candidate.pois], transcripts.get(candidate.transcript_id)) for candidate in candidates]

    async def _require_editor(self, user_id: str) -> None:
        async with self.session_factory() as db:
            user = await db.get(User, user_id)
            if user is None or not user.is_editor:
                raise PermissionError("Требуется роль редактора")

    @staticmethod
    def _https_url(value: str, label: str) -> str:
        parsed = urlsplit(value.strip())
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
            raise StarRouteValidationError(f"{label} должна быть HTTPS-ссылкой")
        return value.strip()

    def _normalize_poi(self, poi: dict[str, Any], position: int) -> dict[str, Any]:
        return {
            "position": position + 1,
            "segment_id": poi["segment_id"],
            "poi_id": self._optional_text(poi.get("poi_id"), 200),
            "name": poi["name"].strip(),
            "latitude": poi["latitude"],
            "longitude": poi["longitude"],
            "source_url": self._https_url(poi["source_url"], "Ссылка на POI"),
        }

    @staticmethod
    def _optional_text(value: Any, max_length: int) -> str | None:
        return value.strip()[:max_length] if isinstance(value, str) and value.strip() else None

    @staticmethod
    def _transcript_payload(transcript: StarRouteTranscript) -> dict[str, Any]:
        return {
            "id": transcript.id, "title": transcript.title, "source_url": transcript.source_url,
            "author_name": transcript.author_name, "rights_basis": transcript.rights_basis,
            "registered_at": transcript.created_at.isoformat(),
        }

    @staticmethod
    def _segment_payload(segment: StarRouteSegment) -> dict[str, Any]:
        return {
            "id": segment.id, "transcript_id": segment.transcript_id,
            "start_seconds": segment.start_seconds, "end_seconds": segment.end_seconds,
            "excerpt": segment.excerpt, "extracted_place_name": segment.extracted_place_name,
        }

    def _candidate_payload(
        self, candidate: StarRouteCandidate, segments: list[StarRouteSegment], transcript: StarRouteTranscript | None = None,
    ) -> dict[str, Any]:
        segment_by_id = {segment.id: segment for segment in segments}
        pois = [{
            **poi,
            "timecode": {
                "start_seconds": segment_by_id[poi["segment_id"]].start_seconds,
                "end_seconds": segment_by_id[poi["segment_id"]].end_seconds,
                "excerpt": segment_by_id[poi["segment_id"]].excerpt,
                "extracted_place_name": segment_by_id[poi["segment_id"]].extracted_place_name,
            },
        } for poi in candidate.pois]
        return {
            "id": candidate.id, "transcript_id": candidate.transcript_id,
            "source_url": transcript.source_url if transcript else None,
            "source_title": transcript.title if transcript else None,
            "source_author": transcript.author_name if transcript else None,
            "rights_basis": transcript.rights_basis if transcript else None,
            "title": candidate.title, "destination": candidate.destination, "pois": pois,
            "route_geojson": candidate.route_geojson, "status": candidate.status,
            "published_at": candidate.published_at.isoformat() if candidate.published_at else None,
        }
