from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from app.db.models.price import PriceObservation

class PriceService:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]): self.session_factory = session_factory
    async def latest(self, subject_key: str) -> dict:
        now = datetime.now(timezone.utc)
        async with self.session_factory() as db:
            row = await db.scalar(select(PriceObservation).where(PriceObservation.subject_key == subject_key, PriceObservation.expires_at > now).order_by(PriceObservation.observed_at.desc()))
        if row is None: return {"status": "unknown", "subject_key": subject_key}
        return {"status":"fresh", "subject_key":subject_key, "amount_minor":row.amount_minor, "currency":row.currency, "source":row.source, "source_url":row.source_url, "observed_at":row.observed_at.isoformat(), "expires_at":row.expires_at.isoformat()}
