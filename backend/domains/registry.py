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

DOMAIN_REGISTRY = {
    "ecology": EcologyDomain(),
    "people": PeopleDomain(),
    "animal": AnimalDomain(),
}
