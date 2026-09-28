"""Pull price observations from explicitly configured, allow-listed JSON feeds."""
import json
import logging
import os
from datetime import timedelta
from typing import Any

import httpx

from app.services.prices import PriceService, is_allowed_price_source

logger = logging.getLogger(__name__)

MAX_FEED_BYTES = 1_000_000
MAX_FEED_ITEMS = 200
MIN_TTL_SECONDS = 60
MAX_TTL_SECONDS = 86_400


def _configured_feeds() -> dict[str, str]:
    """Read `{source: feed_url}` from PRICE_SOURCE_FEEDS; bad config is inert."""
    raw = (os.getenv("PRICE_SOURCE_FEEDS") or "").strip()
    if not raw:
        return {}
    try:
        feeds = json.loads(raw)
    except json.JSONDecodeError:
        logger.error("PRICE_SOURCE_FEEDS is not valid JSON")
        return {}
    if not isinstance(feeds, dict):
        logger.error("PRICE_SOURCE_FEEDS must be a JSON object")
        return {}
    return {
        source: url
        for source, url in feeds.items()
        if isinstance(source, str) and isinstance(url, str) and is_allowed_price_source(source, url)
    }


class PriceFeedCollector:
    def __init__(self, prices: PriceService, http_client: httpx.AsyncClient):
        self.prices = prices
        self.http_client = http_client

    async def refresh(self) -> int:
        recorded = 0
        for source, feed_url in _configured_feeds().items():
            try:
                recorded += await self._refresh_feed(source, feed_url)
            except httpx.HTTPError:
                logger.exception("Price feed fetch failed for source %s", source)
            except (TypeError, ValueError):
                logger.exception("Price feed payload is invalid for source %s", source)
        return recorded

    async def _refresh_feed(self, source: str, feed_url: str) -> int:
        response = await self.http_client.get(
            feed_url,
            headers={"Accept": "application/json"},
            timeout=10.0,
            follow_redirects=False,
        )
        response.raise_for_status()
        content_length = response.headers.get("Content-Length")
        if content_length is not None and int(content_length) > MAX_FEED_BYTES:
            raise ValueError("price feed response is too large")
        if len(response.content) > MAX_FEED_BYTES:
            raise ValueError("price feed response is too large")
        payload: Any = response.json()
        items = payload.get("prices") if isinstance(payload, dict) else None
        if not isinstance(items, list) or len(items) > MAX_FEED_ITEMS:
            raise ValueError("price feed must contain a bounded prices list")

        recorded = 0
        for item in items:
            if not isinstance(item, dict):
                continue
            subject_key = item.get("subject_key")
            source_url = item.get("source_url")
            amount_minor = item.get("amount_minor")
            currency = item.get("currency")
            ttl_seconds = item.get("ttl_seconds", 21_600)
            if (
                not isinstance(subject_key, str) or not subject_key.strip() or len(subject_key) > 200
                or not isinstance(source_url, str) or not is_allowed_price_source(source, source_url)
                or isinstance(amount_minor, bool) or not isinstance(amount_minor, int)
                or not isinstance(currency, str) or not isinstance(ttl_seconds, int)
                or not MIN_TTL_SECONDS <= ttl_seconds <= MAX_TTL_SECONDS
            ):
                continue
            await self.prices.record(
                subject_key=subject_key.strip(),
                source=source,
                source_url=source_url,
                amount_minor=amount_minor,
                currency=currency,
                ttl=timedelta(seconds=ttl_seconds),
            )
            recorded += 1
        return recorded
