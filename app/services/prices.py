import os
import uuid
from datetime import datetime, timedelta, timezone
from urllib.parse import urlsplit

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.models.price import PriceObservation, PriceWatch


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

    async def subscribe(self, user_id: str, subject_key: str, threshold_minor: int, currency: str) -> dict:
        now = datetime.now(timezone.utc)
        async with self.session_factory() as db:
            watch = await db.scalar(select(PriceWatch).where(PriceWatch.user_id == user_id, PriceWatch.subject_key == subject_key, PriceWatch.currency == currency))
            if watch is None:
                watch = PriceWatch(id=uuid.uuid4().hex, user_id=user_id, subject_key=subject_key, threshold_minor=threshold_minor, currency=currency, active=True, created_at=now, updated_at=now)
                db.add(watch)
            else:
                watch.threshold_minor, watch.active, watch.updated_at = threshold_minor, True, now
            await db.commit()
            return {"id": watch.id, "subject_key": watch.subject_key, "threshold_minor": watch.threshold_minor, "currency": watch.currency, "active": watch.active}

    async def list_watches(self, user_id: str) -> list[dict]:
        async with self.session_factory() as db:
            rows = (await db.scalars(select(PriceWatch).where(PriceWatch.user_id == user_id).order_by(PriceWatch.created_at.desc()))).all()
        return [{"id": row.id, "subject_key": row.subject_key, "threshold_minor": row.threshold_minor, "currency": row.currency, "active": row.active} for row in rows]

    async def evaluate_budget(self, budget_minor: int, currency: str, subject_keys: list[str]) -> dict:
        quotes = [await self.latest(subject_key) for subject_key in subject_keys]
        missing = [quote["subject_key"] for quote in quotes if quote["status"] != "fresh"]
        mismatched = [quote["subject_key"] for quote in quotes if quote.get("currency") not in {None, currency}]
        if missing or mismatched:
            return {"status": "unknown", "budget_minor": budget_minor, "currency": currency, "missing": missing, "currency_mismatch": mismatched}
        total = sum(int(quote["amount_minor"]) for quote in quotes)
        return {"status": "feasible" if total <= budget_minor else "infeasible", "budget_minor": budget_minor, "currency": currency, "total_minor": total, "remaining_minor": budget_minor - total, "missing": [], "currency_mismatch": []}

    async def plan_budget(self, budget_minor: int, currency: str, required_keys: list[str], optional_keys: list[str]) -> dict:
        required = await self.evaluate_budget(budget_minor, currency, required_keys)
        if required["status"] != "feasible":
            return {**required, "included": required_keys, "excluded": optional_keys}
        remaining = required["remaining_minor"]
        optional_quotes = [await self.latest(key) for key in optional_keys]
        unavailable = [quote["subject_key"] for quote in optional_quotes if quote["status"] != "fresh" or quote.get("currency") != currency]
        candidates = sorted(
            (quote for quote in optional_quotes if quote["subject_key"] not in unavailable),
            key=lambda quote: (int(quote["amount_minor"]), quote["subject_key"]),
        )
        included, excluded = list(required_keys), list(unavailable)
        for quote in candidates:
            if int(quote["amount_minor"]) <= remaining:
                included.append(quote["subject_key"])
                remaining -= int(quote["amount_minor"])
            else:
                excluded.append(quote["subject_key"])
        return {"status": "feasible" if not excluded else "compromise", "budget_minor": budget_minor, "currency": currency, "total_minor": budget_minor - remaining, "remaining_minor": remaining, "included": included, "excluded": excluded, "unavailable": unavailable}
