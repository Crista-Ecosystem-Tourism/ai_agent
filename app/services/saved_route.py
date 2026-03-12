import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy import select, insert, delete

from app.db.models.saved_route import SavedRoute


class SavedRouteService:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        self.session_factory = session_factory

    async def create(self, user_id: str, data: dict) -> str:
        route_id = uuid.uuid4().hex
        now = datetime.now(timezone.utc)
        async with self.session_factory() as db:
            await db.execute(
                insert(SavedRoute).values(
                    id=route_id,
                    user_id=user_id,
                    name=data["name"],
                    destination=data["destination"],
                    session_id=data.get("session_id"),
                    places=data["places"],
                    graph_geojson=data.get("graph_geojson"),
                    created_at=now,
                    updated_at=now,
                )
            )
            await db.commit()
        return route_id

    async def list_for_user(self, user_id: str) -> list[dict]:
        async with self.session_factory() as db:
            rows = (await db.execute(
                select(
                    SavedRoute.id, SavedRoute.name, SavedRoute.destination,
                    SavedRoute.created_at, SavedRoute.updated_at,
                )
                .where(SavedRoute.user_id == user_id)
                .order_by(SavedRoute.updated_at.desc())
            )).all()
            return [
                {
                    "id": r.id,
                    "name": r.name,
                    "destination": r.destination,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                    "updated_at": r.updated_at.isoformat() if r.updated_at else None,
                }
                for r in rows
            ]

    async def get_owned(self, route_id: str, user_id: str) -> Optional[dict]:
        async with self.session_factory() as db:
            row = (await db.execute(
                select(SavedRoute).where(SavedRoute.id == route_id)
            )).scalar_one_or_none()
            if not row or row.user_id != user_id:
                return None
            return {
                "id": row.id,
                "name": row.name,
                "destination": row.destination,
                "session_id": row.session_id,
                "places": row.places,
                "graph_geojson": row.graph_geojson,
                "created_at": row.created_at.isoformat() if row.created_at else None,
                "updated_at": row.updated_at.isoformat() if row.updated_at else None,
            }

    async def delete_owned(self, route_id: str, user_id: str) -> bool:
        async with self.session_factory() as db:
            row = (await db.execute(
                select(SavedRoute.user_id).where(SavedRoute.id == route_id)
            )).scalar_one_or_none()
            if not row or row != user_id:
                return False
            await db.execute(delete(SavedRoute).where(SavedRoute.id == route_id))
            await db.commit()
            return True
