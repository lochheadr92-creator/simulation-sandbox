"""Scenario package - importing this module registers all built-in
scenarios (side-effect imports below) and re-exports the registry lookup
functions used by the rest of the app."""
from scenarios.registry import get_scenario, list_scenarios  # noqa: F401

from scenarios import wilderness_survival  # noqa: F401
from scenarios import desert_oasis  # noqa: F401
from scenarios import living_settlement  # noqa: F401
from scenarios import emergent_groups  # noqa: F401
