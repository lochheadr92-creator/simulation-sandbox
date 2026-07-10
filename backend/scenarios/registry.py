"""Scenario registration mechanism (Phase 3).

Future scenarios register themselves here at import time - adding a new
scenario means adding a new file under scenarios/ and importing it in
__init__.py; nothing else in the codebase (Core, domains, API routing)
needs to change.
"""

_REGISTRY = {}


def register_scenario(scenario) -> None:
    if scenario.id in _REGISTRY:
        raise ValueError(f"scenario id already registered: {scenario.id}")
    _REGISTRY[scenario.id] = scenario


def get_scenario(scenario_id: str):
    if scenario_id not in _REGISTRY:
        raise KeyError(scenario_id)
    return _REGISTRY[scenario_id]


def list_scenarios():
    return list(_REGISTRY.values())
