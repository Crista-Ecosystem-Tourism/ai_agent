"""Deterministic, dependency-free rules for weekly league seasons and rank changes."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time, timedelta, timezone
from math import ceil
from typing import Sequence


LEAGUE_RANK_MIN = 1
LEAGUE_RANK_MAX = 10
LEAGUE_MIN_PROMOTION_COHORT = 5
LEAGUE_PROMOTION_SHARE = 0.2


@dataclass(frozen=True)
class LeagueWeek:
    season_id: str
    starts_at: datetime
    ends_at: datetime


@dataclass(frozen=True)
class LeagueScore:
    user_id: str
    weekly_xp: int
    rank: int


@dataclass(frozen=True)
class LeagueRankChange:
    user_id: str
    place: int
    weekly_xp: int
    rank_before: int
    rank_after: int
    movement: str


def league_week(moment: datetime) -> LeagueWeek:
    """Return the ISO-calendar week containing an aware instant, bounded in UTC."""
    if moment.tzinfo is None or moment.utcoffset() is None:
        raise ValueError("League timestamps must be timezone-aware")
    utc_moment = moment.astimezone(timezone.utc)
    monday = utc_moment.date() - timedelta(days=utc_moment.weekday())
    starts_at = datetime.combine(monday, time.min, tzinfo=timezone.utc)
    iso_year, iso_week, _ = monday.isocalendar()
    return LeagueWeek(
        season_id=f"{iso_year}-W{iso_week:02d}",
        starts_at=starts_at,
        ends_at=starts_at + timedelta(days=7),
    )


def settle_weekly_ranks(scores: Sequence[LeagueScore]) -> list[LeagueRankChange]:
    """Settle a cohort once: top/bottom 20% move one rank; tied boundaries hold.

    XP ties share a place and are never split by an arbitrary user-ID ordering.
    Cohorts smaller than five do not promote or relegate anyone.
    """
    seen: set[str] = set()
    for score in scores:
        if not score.user_id or score.user_id in seen:
            raise ValueError("League members must have unique non-empty user IDs")
        seen.add(score.user_id)
        if score.weekly_xp < 0:
            raise ValueError("Weekly XP cannot be negative")
        if not LEAGUE_RANK_MIN <= score.rank <= LEAGUE_RANK_MAX:
            raise ValueError("League rank must be between 1 and 10")

    results: list[LeagueRankChange] = []
    cohorts: dict[int, list[LeagueScore]] = {}
    for score in scores:
        cohorts.setdefault(score.rank, []).append(score)

    for rank, cohort in sorted(cohorts.items()):
        ordered = sorted(cohort, key=lambda score: (-score.weekly_xp, score.user_id))
        move_slots = ceil(len(ordered) * LEAGUE_PROMOTION_SHARE)
        promotion_floor: int | None = None
        relegation_ceiling: int | None = None
        promotion_tie_crosses_cutoff = False
        relegation_tie_crosses_cutoff = False
        if len(ordered) >= LEAGUE_MIN_PROMOTION_COHORT:
            promotion_floor = ordered[move_slots - 1].weekly_xp
            relegation_ceiling = ordered[len(ordered) - move_slots].weekly_xp
            if promotion_floor == relegation_ceiling:
                promotion_floor = relegation_ceiling = None
            else:
                promotion_tie_size = sum(score.weekly_xp == promotion_floor for score in ordered)
                promotion_strictly_above = sum(score.weekly_xp > promotion_floor for score in ordered)
                promotion_tie_crosses_cutoff = (
                    promotion_strictly_above < move_slots
                    < promotion_strictly_above + promotion_tie_size
                )
                relegation_tie_size = sum(score.weekly_xp == relegation_ceiling for score in ordered)
                relegation_strictly_below = sum(score.weekly_xp < relegation_ceiling for score in ordered)
                relegation_tie_crosses_cutoff = (
                    relegation_strictly_below < move_slots
                    < relegation_strictly_below + relegation_tie_size
                )

        previous_xp: int | None = None
        place = 0
        for index, score in enumerate(ordered, start=1):
            if score.weekly_xp != previous_xp:
                place = index
                previous_xp = score.weekly_xp

            rank_after = rank
            # If a tie spans the transition boundary, the tied group holds;
            # otherwise the full group moves, even when it exceeds the quota.
            if promotion_floor is not None and (
                score.weekly_xp > promotion_floor
                or (score.weekly_xp == promotion_floor and not promotion_tie_crosses_cutoff)
            ):
                rank_after = min(LEAGUE_RANK_MAX, rank + 1)
            elif relegation_ceiling is not None and (
                score.weekly_xp < relegation_ceiling
                or (score.weekly_xp == relegation_ceiling and not relegation_tie_crosses_cutoff)
            ):
                rank_after = max(LEAGUE_RANK_MIN, rank - 1)

            movement = "promoted" if rank_after > rank else "relegated" if rank_after < rank else "held"
            results.append(LeagueRankChange(
                user_id=score.user_id,
                place=place,
                weekly_xp=score.weekly_xp,
                rank_before=rank,
                rank_after=rank_after,
                movement=movement,
            ))
    return results
