"""Core-owned constants and simulation-time helpers. No wall-clock, ever."""

ENGINE_VERSION = "0.5.0"
SCHEMA_VERSION = "0.4.0"

# Phase 5A: versioned Core contracts. These are stored on every new run and
# fail closed when fork/replay code does not recognize them.
HASH_POLICY_VERSION = "tick-bound-v1"
LEGACY_HASH_POLICY_VERSION = "legacy-carry-v0"
FORK_SEMANTICS_VERSION = "fork-semantics-v1"

REGROWTH_INTERVAL = 5
REGROWTH_AMOUNT = 6
SHELTER_COST = 10

DAY_LENGTH_TICKS = 100

# --- Phase 2: behaviour enrichment constants ---
VISION_RADIUS = 4           # tiles an actor can perceive/discover per activation
CRITICAL_THRESHOLD = 900    # need level that force-interrupts any interruptible action
SEEK_THRESHOLD = 650        # need level that makes seeking the resource clearly urgent
GATHER_TICKS = 3            # multi-tick GATHER duration
BUILD_TICKS = 3             # multi-tick BUILD_SHELTER duration
GATHER_YIELD = 10           # wood units per completed gather
SLEEP_ENERGY_TARGET = 950   # sleep continues (multi-tick) until this energy is reached
FLEE_PERSIST_TICKS = 3      # animals keep fleeing this many ticks after a threat leaves range

# --- Phase 4A: retention policy ---
RECENT_HORIZON_TICKS = 200  # rejected proposals older than (current_tick - this) are pruned;
                            # accepted events/commit_frames are NEVER pruned (required for replay).

# --- Phase 4B: lifecycle (people ageing/health/injury/death) ---
CHILD_MAX_AGE_TICKS = 3000       # below this age: life_stage == "child" (purely observational, no spawn path exists)
ELDER_MIN_AGE_TICKS = 40000      # at/above this age: life_stage == "elder"
STARVATION_HEALTH_DECAY = 3      # health lost/tick while hunger >= CRITICAL_THRESHOLD
DEHYDRATION_HEALTH_DECAY = 4     # health lost/tick while thirst >= CRITICAL_THRESHOLD
EXPOSURE_HEALTH_DECAY = 2        # health lost/tick while night and not sheltered
AGE_DECLINE_HEALTH_DECAY = 1     # health lost/tick for elders, regardless of needs
HEALTH_REGEN = 2                 # health gained/tick when none of the above conditions apply
INJURY_HEALTH_THRESHOLD = 400    # health level at which a person is marked "injured" (foundation state)
MAX_HEALTH = 1000

# --- Phase 4B: minimal hunting/food-chain extension (animals) ---
ANIMAL_MAX_HEALTH = 100
HUNT_TICKS = 2                    # multi-tick HUNT_STRIKE duration (mirrors GATHER_TICKS)
HUNT_DAMAGE = 55                  # health removed per successful hunt strike (2 strikes -> dead from full health)
CARCASS_MEAT_YIELD = 30           # total meat units a fresh carcass holds
CARCASS_HARVEST_YIELD = 10        # meat units per completed harvest action (mirrors GATHER_YIELD)
CARCASS_DECAY_INTERVAL = 5        # ticks between decay steps (mirrors REGROWTH_INTERVAL)
CARCASS_DECAY_AMOUNT = 8          # meat units lost per decay step
MEAT_HUNGER_REDUCTION = 500       # hunger removed per meat unit eaten (vs 400 for foraged inventory)

# --- Phase 5B: giver-owned food transfer ---
FOOD_TRANSFER_QUANTITY = 1        # this phase permits exactly one meat unit per transfer
FOOD_TRANSFER_SURPLUS = 2         # giver retains one unit after a transfer

# --- Phase 5B3: food request/offer protocol (food-interaction-v1) ---
FOOD_INTERACTION_PROTOCOL_VERSION = "food-interaction-v1"
# Named expiry interval for food-interaction-v1: response allowed while
# current_tick < expires_tick; expires when processed at current_tick >= expires_tick.
# expires_tick = created_tick + FOOD_INTERACTION_EXPIRY_TICKS.
FOOD_INTERACTION_EXPIRY_TICKS = 3
FOOD_INTERACTION_RANGE = 1        # same adjacency range as 5B1 GIVE_FOOD


def time_phase(tick: int) -> str:
    t = tick % DAY_LENGTH_TICKS
    if t < 10:
        return "dawn"
    if t < 60:
        return "day"
    if t < 75:
        return "dusk"
    return "night"


def is_night(tick: int) -> bool:
    return time_phase(tick) == "night"
