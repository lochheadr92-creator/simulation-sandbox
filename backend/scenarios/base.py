"""Scenario definition contract (Phase 3).

A Scenario is pure data: world generation parameters, which domain engines
are enabled, and frontend presentation hints. It contributes NOTHING to
Core - the Core (kernel/commit_pipeline/hashing/rng/replay) never imports
this module and never branches on a scenario id. Only the generic
world generator and the kernel's generic domain-registry loop consume it,
both driven entirely by the fields below (never by scenario-specific
if/else branching).
"""
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Scenario:
    id: str
    name: str
    description: str

    # Which domain engines (by registry id, see domains/registry.py) activate
    # each tick for this scenario. The Core kernel iterates this list without
    # any knowledge of what "people"/"animal"/"ecology" mean.
    enabled_domains: list

    # Generic parameters consumed by world.generator.generate_world(). Every
    # field here is a plain number/string/tuple - no scenario-specific code
    # branches exist in the generator, only parameterized generation.
    world_gen: dict

    # Optional frontend-only hints (labels, etc.) - never read by Core or by
    # any domain engine, purely presentational.
    presentation: dict = field(default_factory=dict)
