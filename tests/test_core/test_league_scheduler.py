import asyncio
import unittest

from app.services.league_scheduler import league_settlement_loop


class _FakeLeagueService:
    def __init__(self, results):
        self.results = iter(results)
        self.calls = 0

    async def settle_expired_leagues(self):
        self.calls += 1
        result = next(self.results)
        if isinstance(result, Exception):
            raise result
        return result


class LeagueSettlementLoopTests(unittest.IsolatedAsyncioTestCase):
    async def test_retries_after_transient_failure_and_stops_on_cancellation(self):
        service = _FakeLeagueService([RuntimeError("temporary DB error"), 1])
        sleeps = 0

        async def cancel_after_second_iteration(_interval):
            nonlocal sleeps
            sleeps += 1
            if sleeps == 2:
                raise asyncio.CancelledError

        with self.assertLogs("app.services.league_scheduler", level="ERROR"):
            with self.assertRaises(asyncio.CancelledError):
                await league_settlement_loop(
                    service,
                    interval_seconds=5,
                    sleep=cancel_after_second_iteration,
                )

        self.assertEqual(2, service.calls)
        self.assertEqual(2, sleeps)


if __name__ == "__main__":
    unittest.main()
