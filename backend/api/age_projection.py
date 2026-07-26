"""Derived age-in-years projection. READ-ONLY. Never canonical.

`age_ticks` remains the stored truth: it is the only age the engine writes, the
only one that is persisted, and the only one that enters a canonical hash.
This module adds a *derived* `age_years` on the way out of the API so the
player sees a believable age instead of a five-digit tick count.

Nothing here is written back, persisted, hashed, or read by any domain. Adding
or changing it cannot move a frozen hash -- that is the whole point of putting
it in the projection layer rather than in lifecycle state.

Conversion anchor: the codebase's only time unit is
`DAY_LENGTH_TICKS = 100` (core/constants.py), so

    1 year = DAY_LENGTH_TICKS * 365 = 36,500 ticks

ROUNDING RULE: integer floor division -- completed whole years, the ordinary
human convention (you are 29 until your 30th birthday). No rounding to nearest,
no fractional years, no float arithmetic anywhere in the conversion.
"""
from __future__ import annotations

from core.constants import DAY_LENGTH_TICKS

DAYS_PER_YEAR = 365
TICKS_PER_YEAR = DAY_LENGTH_TICKS * DAYS_PER_YEAR  # 36,500


def age_years(age_ticks) -> int | None:
    """Completed whole years for an age in ticks. Floor division, integers only.

    Returns None when age_ticks is absent or not an integer, so the caller can
    omit the field rather than display a fabricated zero.
    """
    if isinstance(age_ticks, bool) or not isinstance(age_ticks, int):
        return None
    if age_ticks < 0:
        return None
    return age_ticks // TICKS_PER_YEAR


def project_entity_age(entity: dict) -> dict:
    """Return a shallow copy with `age_years` added when age_ticks is present.

    Non-mutating: the caller's dict is never touched, so this cannot leak into
    anything that later gets persisted.
    """
    if not isinstance(entity, dict):
        return entity
    years = age_years(entity.get("age_ticks"))
    if years is None:
        return entity
    projected = dict(entity)
    projected["age_years"] = years
    return projected


def project_entity_ages(entities):
    """Apply `project_entity_age` across a list of entity dicts."""
    return [project_entity_age(entity) for entity in entities]
