from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.models.suitcase import SuitcaseTrip, SuitcaseExpense, SuitcaseGoal


def _iso(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    return dt.isoformat()


DEFAULT_SUITCASE_GOALS: list[dict[str, Any]] = [
    {"title": "Стран посещено", "current": 0, "total": 30, "color": "#007AFF"},
    {"title": "Чудес света", "current": 0, "total": 7, "color": "#FF9500"},
    {"title": "Фотографий в коллекции", "current": 0, "total": 1000, "color": "#AF52DE"},
    {"title": "Часов в полёте", "current": 0, "total": 200, "color": "#34C759"},
]


class SuitcaseService:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        self.session_factory = session_factory

    async def get_workspace(self, user_id: str) -> dict[str, Any]:
        async with self.session_factory() as db:
            trip_rows = list(
                (
                    await db.execute(
                        select(SuitcaseTrip)
                        .where(SuitcaseTrip.user_id == user_id)
                        .order_by(SuitcaseTrip.start_date.desc())
                    )
                ).scalars().all()
            )
            trip_ids = [t.id for t in trip_rows]

            expenses: list[SuitcaseExpense] = []
            if trip_ids:
                expenses = list(
                    (
                        await db.execute(
                            select(SuitcaseExpense).where(SuitcaseExpense.trip_id.in_(trip_ids))
                        )
                    ).scalars().all()
                )

            goal_rows = list(
                (
                    await db.execute(
                        select(SuitcaseGoal)
                        .where(SuitcaseGoal.user_id == user_id)
                        .order_by(SuitcaseGoal.created_at.asc())
                    )
                ).scalars().all()
            )

        if not trip_rows and not goal_rows:
            for item in DEFAULT_SUITCASE_GOALS:
                await self.create_goal(user_id, item)
            return await self.get_workspace(user_id)

        return {
            "trips": [self._trip_out(t) for t in trip_rows],
            "expenses": [self._expense_out(e) for e in expenses],
            "goals": [self._goal_out(g) for g in goal_rows],
        }

    def _trip_out(self, t: SuitcaseTrip) -> dict[str, Any]:
        return {
            "id": t.id,
            "country": t.country,
            "city": t.city,
            "start_date": t.start_date,
            "end_date": t.end_date,
            "image": t.image,
            "mood": t.mood,
            "route_json": t.route_json,
            "impressions": t.impressions,
            "photos": t.photos,
            "is_archived": t.is_archived,
            "created_at": _iso(t.created_at),
            "updated_at": _iso(t.updated_at),
        }

    def _expense_out(self, e: SuitcaseExpense) -> dict[str, Any]:
        amt = e.amount
        if isinstance(amt, Decimal):
            amt = float(amt)
        return {
            "id": e.id,
            "trip_id": e.trip_id,
            "amount": amt,
            "category": e.category,
            "title": e.title,
            "date": e.date,
            "currency": e.currency,
            "created_at": _iso(e.created_at),
            "updated_at": _iso(e.updated_at),
        }

    def _goal_out(self, g: SuitcaseGoal) -> dict[str, Any]:
        return {
            "id": g.id,
            "title": g.title,
            "current": g.current,
            "total": g.total,
            "color": g.color,
            "created_at": _iso(g.created_at),
            "updated_at": _iso(g.updated_at),
        }

    async def _get_trip_owned(self, db: AsyncSession, trip_id: str, user_id: str) -> SuitcaseTrip | None:
        row = (await db.execute(select(SuitcaseTrip).where(SuitcaseTrip.id == trip_id))).scalar_one_or_none()
        if not row or row.user_id != user_id:
            return None
        return row

    async def create_trip(self, user_id: str, data: dict[str, Any]) -> dict[str, Any]:
        trip_id = uuid.uuid4().hex
        now = datetime.now(timezone.utc)
        async with self.session_factory() as db:
            trip = SuitcaseTrip(
                id=trip_id,
                user_id=user_id,
                country=data["country"],
                city=data["city"],
                start_date=data["start_date"],
                end_date=data["end_date"],
                image=data.get("image"),
                mood=data.get("mood"),
                route_json=data.get("route_json"),
                impressions=data.get("impressions"),
                photos=data.get("photos"),
                is_archived=bool(data.get("is_archived", False)),
                created_at=now,
                updated_at=now,
            )
            db.add(trip)
            await db.commit()
            await db.refresh(trip)
            return self._trip_out(trip)

    async def update_trip(self, trip_id: str, user_id: str, data: dict[str, Any]) -> dict[str, Any] | None:
        async with self.session_factory() as db:
            trip = await self._get_trip_owned(db, trip_id, user_id)
            if not trip:
                return None
            now = datetime.now(timezone.utc)
            for key in (
                "country",
                "city",
                "start_date",
                "end_date",
                "image",
                "mood",
                "route_json",
                "impressions",
                "photos",
                "is_archived",
            ):
                if key not in data:
                    continue
                setattr(trip, key, data[key])
            trip.updated_at = now
            await db.commit()
            await db.refresh(trip)
            return self._trip_out(trip)

    async def delete_trip(self, trip_id: str, user_id: str) -> bool:
        async with self.session_factory() as db:
            trip = await self._get_trip_owned(db, trip_id, user_id)
            if not trip:
                return False
            await db.execute(delete(SuitcaseTrip).where(SuitcaseTrip.id == trip_id))
            await db.commit()
            return True

    async def create_expense(self, user_id: str, trip_id: str, data: dict[str, Any]) -> dict[str, Any] | None:
        async with self.session_factory() as db:
            if not await self._get_trip_owned(db, trip_id, user_id):
                return None
            exp_id = uuid.uuid4().hex
            now = datetime.now(timezone.utc)
            amount = data["amount"]
            if isinstance(amount, (str, int)):
                amount = float(amount)
            exp = SuitcaseExpense(
                id=exp_id,
                trip_id=trip_id,
                amount=amount,
                category=data["category"],
                title=data["title"],
                date=data["date"],
                currency=data.get("currency"),
                created_at=now,
                updated_at=now,
            )
            db.add(exp)
            await db.commit()
            await db.refresh(exp)
            return self._expense_out(exp)

    async def update_expense(
        self, expense_id: str, user_id: str, data: dict[str, Any]
    ) -> dict[str, Any] | None:
        async with self.session_factory() as db:
            exp = (
                await db.execute(
                    select(SuitcaseExpense).where(SuitcaseExpense.id == expense_id)
                )
            ).scalar_one_or_none()
            if not exp:
                return None
            trip = await self._get_trip_owned(db, exp.trip_id, user_id)
            if not trip:
                return None
            now = datetime.now(timezone.utc)
            for key in ("amount", "category", "title", "date", "currency"):
                if key in data:
                    val = data[key]
                    if key == "amount" and val is not None:
                        val = float(val) if not isinstance(val, Decimal) else float(val)
                    setattr(exp, key, val)
            exp.updated_at = now
            await db.commit()
            await db.refresh(exp)
            return self._expense_out(exp)

    async def delete_expense(self, expense_id: str, user_id: str) -> bool:
        async with self.session_factory() as db:
            exp = (
                await db.execute(
                    select(SuitcaseExpense).where(SuitcaseExpense.id == expense_id)
                )
            ).scalar_one_or_none()
            if not exp:
                return False
            trip = await self._get_trip_owned(db, exp.trip_id, user_id)
            if not trip:
                return False
            await db.execute(delete(SuitcaseExpense).where(SuitcaseExpense.id == expense_id))
            await db.commit()
            return True

    async def create_goal(self, user_id: str, data: dict[str, Any]) -> dict[str, Any]:
        gid = uuid.uuid4().hex
        now = datetime.now(timezone.utc)
        async with self.session_factory() as db:
            g = SuitcaseGoal(
                id=gid,
                user_id=user_id,
                title=data["title"],
                current=int(data.get("current", 0)),
                total=int(data.get("total", 1)),
                color=data.get("color") or "#007AFF",
                created_at=now,
                updated_at=now,
            )
            db.add(g)
            await db.commit()
            await db.refresh(g)
            return self._goal_out(g)

    async def update_goal(
        self, goal_id: str, user_id: str, data: dict[str, Any]
    ) -> dict[str, Any] | None:
        async with self.session_factory() as db:
            g = (
                await db.execute(
                    select(SuitcaseGoal).where(
                        SuitcaseGoal.id == goal_id,
                        SuitcaseGoal.user_id == user_id,
                    )
                )
            ).scalar_one_or_none()
            if not g:
                return None
            now = datetime.now(timezone.utc)
            for key in ("title", "current", "total", "color"):
                if key in data and data[key] is not None:
                    if key in ("current", "total"):
                        setattr(g, key, int(data[key]))
                    else:
                        setattr(g, key, data[key])
            g.updated_at = now
            await db.commit()
            await db.refresh(g)
            return self._goal_out(g)

    async def delete_goal(self, goal_id: str, user_id: str) -> bool:
        async with self.session_factory() as db:
            res = await db.execute(
                delete(SuitcaseGoal).where(
                    SuitcaseGoal.id == goal_id,
                    SuitcaseGoal.user_id == user_id,
                )
            )
            await db.commit()
            return res.rowcount > 0
