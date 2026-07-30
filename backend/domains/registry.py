"""Domain engine registry (Phase 3).

Maps a domain_id (as referenced by a Scenario's `enabled_domains` list) to
its singleton DomainEngine instance. The Core kernel looks domains up here
generically - it never imports PeopleDomain/AnimalDomain/EcologyDomain by
name. Adding a new domain in the future means adding one entry here; the
kernel does not change.
"""
from domains.people_domain import PeopleDomain
from domains.animal_domain import AnimalDomain
from domains.ecology_domain import EcologyDomain
from domains.lifecycle_domain import LifecycleDomain
from domains.weather_domain import WeatherDomain
from domains.living_settlement_domain import LivingSettlementDomain
from domains.association_domain import AssociationDomain
from domains.group_state_domain import GroupStateDomain
from domains.group_collective_domain import GroupCollectiveDomain
from domains.emotion_domain import EmotionDomain
from domains.group_goal_domain import GroupGoalDomain
from domains.group_norm_domain import GroupNormDomain
from domains.group_carriage_domain import GroupCarriageDomain

DOMAIN_REGISTRY = {
    "ecology": EcologyDomain(),
    "lifecycle": LifecycleDomain(),
    "people": PeopleDomain(),
    "animal": AnimalDomain(),
    "weather": WeatherDomain(),
    "living_settlement": LivingSettlementDomain(),
    "emotion": EmotionDomain(),
    "association": AssociationDomain(),
    "group_state": GroupStateDomain(),
    "group_collective": GroupCollectiveDomain(),
    "group_goal": GroupGoalDomain(),
    "group_norm": GroupNormDomain(),
    "group_carriage": GroupCarriageDomain(),
}
