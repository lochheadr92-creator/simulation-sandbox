"""
Deterministic named RNG streams.

Doctrine: a single global seed/stream is dangerous because adding one new
random draw anywhere can shift every later draw ("adding flowers causes the
king to die"). Instead every call site asks for a NAMED stream. Stream names
should embed the calling entity and the simulation tick, so that:
  - streams are isolated from each other (no cross-contamination)
  - determinism does not depend on call ORDER, only on (run seed, name)
  - the same seed always reproduces the same sequence, restart-safe
"""
import hashlib
import random

RNG_POLICY_VERSION = "named-stream-v1"
RNG_NAMESPACE = "seed-only-v1"


class DeterministicRNG:
    def __init__(self, run_seed: str, namespace: str = RNG_NAMESPACE,
                 policy_version: str = RNG_POLICY_VERSION):
        if policy_version != RNG_POLICY_VERSION:
            raise ValueError(f"unsupported RNG policy: {policy_version}")
        if namespace != RNG_NAMESPACE:
            raise ValueError(f"unsupported RNG namespace: {namespace}")
        self.run_seed = str(run_seed)
        self.namespace = namespace
        self.policy_version = policy_version
        self._streams = {}

    def stream(self, name: str) -> random.Random:
        if name not in self._streams:
            digest = hashlib.sha256(f"{self.run_seed}::{name}".encode("utf-8")).hexdigest()
            seed_int = int(digest[:16], 16)
            self._streams[name] = random.Random(seed_int)
        return self._streams[name]
