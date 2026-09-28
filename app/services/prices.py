import os
import uuid
from datetime import datetime, timedelta, timezone
from urllib.parse import urlsplit

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.models.price import PriceObservation


class PriceSourceNotAllowedError(ValueError):
    pass


def _allowed_sources() -> dict[str, set[str]]:
    """Parse `source=host|host` entries; no entry means no source is trusted."""
    entries = (os.getenv("PRICE_SOURCE_ALLOWLIST") or "").split(",")
    allowed: dict[str, set[str]] = {}
    for entry in entries:
        source, separator, hosts = entry.strip().partition("=")
        if not source or not separator:
            continue
        allowed[source] = {host.strip().lower() for host in hosts.split("|") if host.strip()}
    return allowed


class PriceService:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        self.session_factory = session_factory

    async def record(
        self, *, subject_key: str, source: str, source_url: str, amount_minor: int,
        currency: str, observed_at: datetime | None = None, ttl: timedelta = timedelta(hours=6),
    ) -> str:
        parsed = urlsplit(source_url)
        allowed_hosts = _allowed_sources().get(source)
        if (
            not allowed_hosts or parsed.scheme != "https" or not parsed.hostname
            or parsed.hostname.lower() not in allowed_hosts
        ):
            raise PriceSourceNotAllowedError("price source is not allow-listed")
        now = observed_at or datetime.now(timezone.utc)
        if amount_minor < 0 or len(currency) != 3 or ttl <= timedelta():
            raise ValueError("invalid price observation")
        quote_id = uuid.uuid4().hex
        async with self.session_factory() as db:
            db.add(PriceObservation(
                id=quote_id, subject_key=subject_key, source=source, source_url=source_url,
                amount_minor=amount_minor, currency=currency.upper(), observed_at=now,
                expires_at=now + ttl, created_at=now, updated_at=now,
            ))
            await db.commit()
        return quote_id

    async def latest(self, subject_key: str) -> dict:
        now = datetime.now(timezone.utc)
        async with self.session_factory() as db:
            row = await db.scalar(select(PriceObservation).where(PriceObservation.subject_key == subject_key, PriceObservation.expires_at > now).order_by(PriceObservation.observed_at.desc()))
        if row is None:
            return {"status": "unknown", "subject_key": subject_key}
        return {
            "status": "fresh", "subject_key": subject_key, "amount_minor": row.amount_minor,
            "currency": row.currency, "source": row.source, "source_url": row.source_url,
            "observed_at": row.observed_at.isoformat(), "expires_at": row.expires_at.isoformat(),
        }
