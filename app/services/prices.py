import os
import uuid
from datetime import datetime, timedelta, timezone
from urllib.parse import urlsplit

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.models.price import PriceObservation, PriceWatch, PriceWatchAlert


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


def is_allowed_price_source(source: str, source_url: str) -> bool:
    parsed = urlsplit(source_url)
    allowed_hosts = _allowed_sources().get(source)
    return bool(
        allowed_hosts and parsed.scheme == "https" and parsed.hostname
        and parsed.hostname.lower() in allowed_hosts
    )


class PriceService:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        self.session_factory = session_factory

    async def record(
        self, *, subject_key: str, source: str, source_url: str, amount_minor: int,
        currency: str, observed_at: datetime | None = None, ttl: timedelta = timedelta(hours=6),
    ) -> str:
        if not is_allowed_price_source(source, source_url):
            raise PriceSourceNotAllowedError("price source is not allow-listed")
        now = observed_at or datetime.now(timezone.utc)
        if amount_minor < 0 or len(currency) != 3 or not currency.isalpha() or ttl <= timedelta():
            raise ValueError("invalid price observation")
        quote_id = uuid.uuid4().hex
        async with self.session_factory() as db:
            existing = await db.scalar(select(PriceObservation).where(
                PriceObservation.subject_key == subject_key,
                PriceObservation.source == source,
                PriceObservation.source_url == source_url,
                PriceObservation.amount_minor == amount_minor,
                PriceObservation.currency == currency.upper(),
            ).order_by(PriceObservation.observed_at.desc()))
            if existing is not None:
                existing.observed_at = now
                existing.expires_at = now + ttl
                existing.updated_at = now
                await db.commit()
                return existing.id
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

    async def unsubscribe(self, user_id: str, watch_id: str) -> bool:
        now = datetime.now(timezone.utc)
        async with self.session_factory() as db:
            watch = await db.scalar(select(PriceWatch).where(PriceWatch.id == watch_id, PriceWatch.user_id == user_id))
            if watch is None:
                return False
            if watch.active:
                watch.active = False
                watch.updated_at = now
                await db.commit()
            return True

    async def process_watches(self) -> int:
        """Advance dedupe state only for a fresh price below the chosen threshold."""
        now = datetime.now(timezone.utc)
        changed = 0
        async with self.session_factory() as db:
            watches = (await db.scalars(select(PriceWatch).where(PriceWatch.active.is_(True)))).all()
            for watch in watches:
                quote = await db.scalar(select(PriceObservation).where(
                    PriceObservation.subject_key == watch.subject_key,
                    PriceObservation.currency == watch.currency,
                    PriceObservation.expires_at > now,
                ).order_by(PriceObservation.observed_at.desc()))
                if quote is None or quote.amount_minor > watch.threshold_minor:
                    continue
                if watch.last_alerted_amount_minor is not None and quote.amount_minor >= watch.last_alerted_amount_minor:
                    continue
                watch.last_alerted_amount_minor = quote.amount_minor
                watch.last_alerted_at = now
                watch.updated_at = now
                db.add(PriceWatchAlert(id=uuid.uuid4().hex, watch_id=watch.id, user_id=watch.user_id, subject_key=watch.subject_key, amount_minor=quote.amount_minor, currency=quote.currency, created_at=now))
                changed += 1
            if changed:
                await db.commit()
        return changed

    async def list_alerts(self, user_id: str) -> list[dict]:
        async with self.session_factory() as db:
            rows = (await db.scalars(select(PriceWatchAlert).where(PriceWatchAlert.user_id == user_id).order_by(PriceWatchAlert.created_at.desc()).limit(100))).all()
        return [{"id": row.id, "subject_key": row.subject_key, "amount_minor": row.amount_minor, "currency": row.currency, "created_at": row.created_at.isoformat()} for row in rows]

    async def evaluate_budget(self, budget_minor: int, currency: str, subject_keys: list[str]) -> dict:
        quotes = [await self.latest(subject_key) for subject_key in subject_keys]
        missing = [quote["subject_key"] for quote in quotes if quote["status"] != "fresh"]
        mismatched = [quote["subject_key"] for quote in quotes if quote.get("currency") not in {None, currency}]
        if missing or mismatched:
            return {"status": "unknown", "budget_minor": budget_minor, "currency": currency, "missing": missing, "currency_mismatch": mismatched}
        total = sum(int(quote["amount_minor"]) for quote in quotes)
        return {"status": "feasible" if total <= budget_minor else "infeasible", "budget_minor": budget_minor, "currency": currency, "total_minor": total, "remaining_minor": budget_minor - total, "missing": [], "currency_mismatch": []}

    async def plan_budget(
        self, budget_minor: int, currency: str, required_keys: list[str], optional_keys: list[str],
        trip_days: int = 1, transport_keys: list[str] | None = None, daily_keys: list[str] | None = None,
    ) -> dict:
        """Plan with fresh one-off transport and per-day costs, never a guessed timetable."""
        transport_keys = transport_keys or []
        daily_keys = daily_keys or []
        quantities: dict[str, int] = {}
        for key in [*required_keys, *transport_keys]:
            quantities[key] = quantities.get(key, 0) + 1
        for key in daily_keys:
            quantities[key] = quantities.get(key, 0) + trip_days
        required_quotes = {key: await self.latest(key) for key in quantities}
        missing = [key for key, quote in required_quotes.items() if quote["status"] != "fresh"]
        mismatched = [
            key for key, quote in required_quotes.items()
            if quote.get("currency") not in {None, currency}
        ]
        included_required = [*required_keys, *transport_keys, *daily_keys]
        if missing or mismatched:
            return {
                "status": "unknown", "budget_minor": budget_minor, "currency": currency,
                "trip_days": trip_days, "missing": missing, "currency_mismatch": mismatched,
                "included": included_required, "excluded": optional_keys,
            }
        required_total = sum(int(required_quotes[key]["amount_minor"]) * quantity for key, quantity in quantities.items())
        breakdown = [
            {
                "subject_key": key, "quantity": quantity,
                "unit_minor": int(required_quotes[key]["amount_minor"]),
                "total_minor": int(required_quotes[key]["amount_minor"]) * quantity,
            }
            for key, quantity in quantities.items()
        ]
        if required_total > budget_minor:
            return {
                "status": "infeasible", "budget_minor": budget_minor, "currency": currency,
                "trip_days": trip_days, "total_minor": required_total,
                "remaining_minor": budget_minor - required_total, "missing": [], "currency_mismatch": [],
                "included": included_required, "excluded": optional_keys, "required_breakdown": breakdown,
            }
        remaining = budget_minor - required_total
        optional_quotes = [await self.latest(key) for key in optional_keys]
        unavailable = [quote["subject_key"] for quote in optional_quotes if quote["status"] != "fresh" or quote.get("currency") != currency]
        candidates = sorted(
            (quote for quote in optional_quotes if quote["subject_key"] not in unavailable),
            key=lambda quote: (int(quote["amount_minor"]), quote["subject_key"]),
        )
        included, excluded = included_required, list(unavailable)
        for quote in candidates:
            if int(quote["amount_minor"]) <= remaining:
                included.append(quote["subject_key"])
                remaining -= int(quote["amount_minor"])
            else:
                excluded.append(quote["subject_key"])
        return {
            "status": "feasible" if not excluded else "compromise", "budget_minor": budget_minor,
            "currency": currency, "trip_days": trip_days, "total_minor": budget_minor - remaining,
            "remaining_minor": remaining, "included": included, "excluded": excluded,
            "unavailable": unavailable, "required_breakdown": breakdown,
        }
