"""Lifecycle-owned periodic settlement for expired weekly league seasons."""

from __future__ import annotations

import asyncio
import logging
from typing import Awaitable, Callable, Protocol


logger = logging.getLogger(__name__)
LEAGUE_SETTLEMENT_INTERVAL_SECONDS = 60


class LeagueSettlementService(Protocol):
    async def settle_expired_leagues(self) -> int: ...


async def league_settlement_loop(
    service: LeagueSettlementService,
    interval_seconds: int = LEAGUE_SETTLEMENT_INTERVAL_SECONDS,
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
) -> None:
    """Settle expired seasons periodically; cancellation cleanly stops the loop."""
    while True:
        try:
            closed_count = await service.settle_expired_leagues()
            if closed_count:
                logger.info("Settled %s expired weekly league season(s)", closed_count)
        except asyncio.CancelledError:
            raise
        except Exception:  # noqa: BLE001 - transient DB failures must not kill future attempts
            logger.exception("Weekly league settlement failed; will retry after the interval")
        await sleep(interval_seconds)
