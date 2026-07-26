import pytest

from core.constants import ENGINE_VERSION, SCHEMA_VERSION
from core.run_service import (
    RunVersionCompatibilityError,
    assert_run_version_compatible,
)


def test_current_engine_and_schema_are_executable():
    assert_run_version_compatible({
        "engine_version": ENGINE_VERSION,
        "schema_version": SCHEMA_VERSION,
    })


def test_older_run_fails_closed_with_recorded_replay_guidance():
    with pytest.raises(RunVersionCompatibilityError) as caught:
        assert_run_version_compatible({
            "engine_version": "0.4.0",
            "schema_version": "0.3.0",
        })

    detail = str(caught.value)
    assert "recorded-only" in detail
    assert "Recorded replay remains available" in detail
    assert ENGINE_VERSION in detail
    assert SCHEMA_VERSION in detail


def test_pre_age_rebaseline_run_is_recorded_only_even_with_current_schema():
    """0.5.0 runs retain the prior age semantics and are not executable."""
    with pytest.raises(RunVersionCompatibilityError) as caught:
        assert_run_version_compatible({
            "engine_version": "0.5.0",
            "schema_version": SCHEMA_VERSION,
        })

    detail = str(caught.value)
    assert "recorded-only" in detail
    assert "stored engine='0.5.0'" in detail
    assert f"executable engine={ENGINE_VERSION!r}" in detail
