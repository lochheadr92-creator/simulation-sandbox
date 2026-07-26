"""Age-in-years derived projection: conversion boundaries and non-canonicality.

`age_ticks` is the stored truth; `age_years` is derived read-only in the API
projection layer. These tests pin the conversion at its boundaries so a future
change to DAY_LENGTH_TICKS or the rounding rule cannot silently shift every
displayed age.
"""
from __future__ import annotations

import copy

from api.age_projection import (
    DAYS_PER_YEAR,
    TICKS_PER_YEAR,
    age_years,
    project_entity_age,
    project_entity_ages,
)
from core.constants import (
    CHILD_MAX_AGE_TICKS,
    DAY_LENGTH_TICKS,
    ELDER_MIN_AGE_TICKS,
    life_stage_for_age,
)
from scenarios import get_scenario
from world.generator import (
    GENESIS_ADULT_AGE_MAX_TICKS,
    _default_person_age_range,
    generate_world,
)


def test_ticks_per_year_derives_from_the_day_anchor():
    """The conversion is anchored to the codebase's only time unit, not a
    magic number: 100 ticks/day * 365 days = 36,500."""
    assert TICKS_PER_YEAR == DAY_LENGTH_TICKS * DAYS_PER_YEAR
    assert TICKS_PER_YEAR == 36_500


def test_conversion_boundaries():
    """Floor division -- completed whole years."""
    assert age_years(0) == 0                          # tick 0
    assert age_years(TICKS_PER_YEAR - 1) == 0         # one tick before a birthday
    assert age_years(TICKS_PER_YEAR) == 1             # exactly one year
    assert age_years(TICKS_PER_YEAR + 1) == 1         # one tick after a birthday
    assert age_years(2 * TICKS_PER_YEAR - 1) == 1     # one tick before the 2nd
    assert age_years(2 * TICKS_PER_YEAR) == 2
    # A large value: 65 years, the elder threshold.
    assert age_years(65 * TICKS_PER_YEAR) == 65
    assert age_years(1_000_000) == 27                 # 1,000,000 // 36,500


def test_conversion_is_integer_only():
    """No float arithmetic: results are exact ints, never 29.999-style drift."""
    for ticks in (0, 1, TICKS_PER_YEAR - 1, TICKS_PER_YEAR, 2_372_500, 10**9):
        result = age_years(ticks)
        assert isinstance(result, int) and not isinstance(result, bool)


def test_missing_or_invalid_age_yields_no_field_rather_than_a_fake_zero():
    """An entity with no age must not display as '0 years'."""
    assert age_years(None) is None
    assert age_years("40000") is None
    assert age_years(True) is None          # bool is an int subclass; must not count
    assert age_years(-1) is None
    assert "age_years" not in project_entity_age({"id": "tree-1", "type": "tree"})


def test_projection_does_not_mutate_the_source_entity():
    """Non-mutating, so a derived value can never leak into persisted state."""
    entity = {"id": "person-000", "type": "person", "age_ticks": 2 * TICKS_PER_YEAR}
    projected = project_entity_age(entity)
    assert projected["age_years"] == 2
    assert "age_years" not in entity, "projection mutated the caller's dict"
    assert projected is not entity


def test_project_entity_ages_across_a_list():
    entities = [
        {"id": "person-000", "type": "person", "age_ticks": TICKS_PER_YEAR * 30},
        {"id": "rock-1", "type": "rock"},
    ]
    projected = project_entity_ages(entities)
    assert projected[0]["age_years"] == 30
    assert "age_years" not in projected[1]
    assert all("age_years" not in e for e in entities), "source list was mutated"


def test_elder_threshold_is_a_real_human_age():
    """Guards the Part A re-scale: elder was 40,000 ticks (13 months)."""
    assert ELDER_MIN_AGE_TICKS == 65 * TICKS_PER_YEAR
    assert age_years(ELDER_MIN_AGE_TICKS) == 65


def test_child_threshold_and_default_genesis_band_use_real_human_ages():
    """Stage 2 re-scales the child boundary and default founder ages together.

    The lower bound equals the child threshold deliberately: lifecycle uses a
    strict `<`, so every founder is an adult while the child stage remains
    unreachable until a birth path exists.
    """
    assert CHILD_MAX_AGE_TICKS == 18 * TICKS_PER_YEAR
    assert GENESIS_ADULT_AGE_MAX_TICKS == 55 * TICKS_PER_YEAR
    assert _default_person_age_range() == (
        CHILD_MAX_AGE_TICKS,
        GENESIS_ADULT_AGE_MAX_TICKS,
    )
    assert CHILD_MAX_AGE_TICKS < GENESIS_ADULT_AGE_MAX_TICKS < ELDER_MIN_AGE_TICKS


def test_life_stage_boundaries_use_the_canonical_age_classifier():
    assert life_stage_for_age(CHILD_MAX_AGE_TICKS - 1) == "child"
    assert life_stage_for_age(CHILD_MAX_AGE_TICKS) == "adult"
    assert life_stage_for_age(ELDER_MIN_AGE_TICKS - 1) == "adult"
    assert life_stage_for_age(ELDER_MIN_AGE_TICKS) == "elder"


def test_default_world_generation_creates_only_adult_founders_in_realistic_band():
    world = generate_world("age-default-band", get_scenario("basic_survival"))
    people = [spec for spec in world["genesis_specs"] if spec["type"] == "person"]

    assert people, "fixture must generate people"
    assert all(
        CHILD_MAX_AGE_TICKS <= person["age_ticks"] <= GENESIS_ADULT_AGE_MAX_TICKS
        for person in people
    )
    assert {person["life_stage"] for person in people} == {"adult"}


def test_world_generation_derives_life_stage_from_range_and_profile_age_overrides():
    def generated_person(age_range, profile=None):
        scenario = copy.deepcopy(get_scenario("basic_survival"))
        scenario.world_gen["num_people"] = 1
        scenario.world_gen["person_age_range"] = age_range
        scenario.world_gen["person_profiles"] = [profile] if profile else []
        world = generate_world("age-override-band", scenario)
        return next(spec for spec in world["genesis_specs"] if spec["type"] == "person")

    child = generated_person((CHILD_MAX_AGE_TICKS - 1, CHILD_MAX_AGE_TICKS - 1))
    elder = generated_person((ELDER_MIN_AGE_TICKS, ELDER_MIN_AGE_TICKS))
    profile_elder = generated_person(
        (CHILD_MAX_AGE_TICKS, CHILD_MAX_AGE_TICKS),
        {"age_ticks": ELDER_MIN_AGE_TICKS, "life_stage": "child"},
    )

    assert (child["age_ticks"], child["life_stage"]) == (
        CHILD_MAX_AGE_TICKS - 1,
        "child",
    )
    assert (elder["age_ticks"], elder["life_stage"]) == (
        ELDER_MIN_AGE_TICKS,
        "elder",
    )
    assert (profile_elder["age_ticks"], profile_elder["life_stage"]) == (
        ELDER_MIN_AGE_TICKS,
        "elder",
    )


def test_world_generation_normalises_forged_life_stage_on_extra_people():
    scenario = copy.deepcopy(get_scenario("basic_survival"))
    scenario.world_gen["num_people"] = 0
    scenario.world_gen["extra_genesis_specs"] = [{
        "id": "extra-person",
        "type": "person",
        "position": {"x": 0, "y": 0},
        "age_ticks": ELDER_MIN_AGE_TICKS,
        "life_stage": "child",
    }]

    world = generate_world("age-extra-person", scenario)
    person = next(spec for spec in world["genesis_specs"] if spec["type"] == "person")

    assert (person["age_ticks"], person["life_stage"]) == (
        ELDER_MIN_AGE_TICKS,
        "elder",
    )
