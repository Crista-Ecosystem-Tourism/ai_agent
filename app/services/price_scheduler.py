"""Lifecycle-owned polling for deduplicated price-watch alerts."""
import asyncio
import logging
from typing import Awaitable, Callable, Protocol
logger = logging.getLogger(__name__)
class PriceWatchService(Protocol):
    async def process_watches(self) -> int: ...
async def price_watch_loop(service: PriceWatchService, interval_seconds: int = 60, sleep: Callable[[float], Awaitable[None]] = asyncio.sleep) -> None:
    while True:
        try:
            count = await service.process_watches()
            if count: logger.info("Recorded %s price-watch alert(s)", count)
        except asyncio.CancelledError: raise
        except Exception: logger.exception("Price-watch processing failed; will retry")
        await sleep(interval_seconds)
