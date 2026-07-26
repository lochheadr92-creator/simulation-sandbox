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
# Age thresholds are denominated in ticks at DAY_LENGTH_TICKS * 365 = 36,500
# ticks per year (the codebase's only time anchor). The pre-2026-07-26 values
# were 3,000 and 40,000 -- i.e. an "elder" at 13 months old. Corrected to real
# human ages.
#
# CHILD_MAX_AGE_TICKS is NOT re-scaled here, deliberately. The global minimum
# genesis age is 3,084 ticks, only 84 above the old 3,000 boundary, so raising
# it would reclassify live agents adult -> child and write a different
# life_stage into canonical state -- moving the frozen hash. It is re-scaled in
# Part B alongside the genesis distribution, where the hash moves under
# authorisation and the change is attributable. Until then the child stage
# stays unreachable, exactly as before: genesis spawns above it and there is no
# birth path.
CHILD_MAX_AGE_TICKS = 3000       # UNCHANGED in Part A -- see note above; still unreachable
ELDER_MIN_AGE_TICKS = 2372500    # 65 years * 36,500. Was 40,000 (= 13 months).
                                 # Hash-neutral: worst genesis max age across all
                                 # scenarios is 28,784 and the longest scenario is
                                 # 1,000 ticks, so nothing came near either value.
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

# --- Stage 6 Liveness Pass: passive shelter/structure wear ---
# A small, deterministic, weather-driven condition decrement for shelter and
# structure entities, floored at 0. Repair already RAISES condition, so this
# creates a real wear/repair loop and lets shared-shelter condition fall below
# the Stage 7D upkeep threshold organically. Tuned from the collective_groups
# measurement probe (see STAGE-6-LIVENESS-PASS.md).
STRUCTURE_WEAR_INTERVAL = 5           # ticks between wear steps (mirrors CARCASS_DECAY_INTERVAL)
STRUCTURE_WEAR_BASE = 4               # base condition lost per wear step (gentle: repairs keep pace)
STRUCTURE_WEAR_WEATHER_DIVISOR = 60   # extra wear = weather exposure // this (storms wear more)
STRUCTURE_WEAR_MIN_CONDITION = 0      # condition floor (never below this)

# --- Layer C, Variety Leg 1: upkeep drive (memory/CAPABILITY-LAYER-C-VARIETY-LEG1-UPKEEP.md) ---
# tend (any role) and repair (role=="builder", living_settlement_domain.py) use
# disjoint condition bands so the two never target the same shelter in the same
# state. Repair's own trigger stays the existing inline `750` (unmodified, sealed
# Stage 6 code); this constant duplicates that value intentionally, documented
# here as the shared band edge rather than refactoring the sealed line.
STRUCTURE_TEND_CONDITION_FLOOR = 750     # tend band: condition in [FLOOR, ceiling); repair owns condition < FLOOR
STRUCTURE_TEND_CONDITION_CEILING = 1000  # tend band upper bound (matches the codebase's fixed max_condition convention)
STRUCTURE_TEND_RESTORE_AMOUNT = 40       # condition gained per tend action (smaller than repair's +120: light maintenance, no wood/tool cost)
UPKEEP_IDLE_TAIL_TICKS = 5               # trailing decision_history entries checked for a REST streak (bounded by LIMITS.decision_receipts_retained=12)
# Base score placed between the two existing fallback tiers, not above both:
# EXPLORE's fallback (180) must still win while there is unknown ground nearby,
# so upkeep doesn't starve map exploration once a shelter is in the tend band
# (a shelter is in-band almost continuously, so a score above 180 made tend a
# permanently-preferred absorbing loop -- observed empirically via
# test_stage6e_living_settlement.py's scout losing visual contact with its
# WARN_DANGER target because it stopped wandering; see the leg contract's
# risk log). 120 sits strictly between REST (60) and EXPLORE (180), and well
# below the lowest survival-triggered base (1200).
TEND_STRUCTURE_BASE_SCORE = 120

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

# --- Effort transfer and self-restore energy (memory/FINDING-EFFORT-TRANSFER-ENERGY.md) ---
# EVIDENCE: NONE ON RECORD. These four values were inline literals with no
# rationale anywhere; the 2026-07-26 audit found no probe, contract or
# measurement that set any of them. Promoted to named constants and RATIFIED
# AS-IS (ruling A, 2026-07-26) -- naming them is hash-neutral, changing them is
# not. Do not read the names as endorsement of the numbers.
#
# Measured consequence of the pair, recorded so it is not rediscovered: the
# actor is charged unconditionally while the target's gain is capped by
# headroom, so a full target means the actor pays and the target receives
# nothing. That is the COMMON case -- 199 of 269 target writes clamped across
# the two frozen baselines, making cooperate net energy-NEGATIVE (-420 over 37
# events in living_settlement 320; -1650 over 232 in collective_groups 1000).
# Whether that gradient is intended is an OPEN RULING; revisit inside the Layer
# C social-density leg, where cooperate's economics actually matter.
#
# Shared deliberately between `cooperate` (living_agent_social.py) and `help`
# (living_agent_actions.py): they were duplicated literals of equal value
# modelling one concept -- an actor spending energy to benefit another. Sharing
# makes a future change hit both, which is the intent; split them here if they
# are ever meant to diverge, rather than letting the literals drift silently.
EFFORT_TRANSFER_TARGET_ENERGY_GAIN = 40  # energy the target gains, capped by min(1000, ...)
EFFORT_TRANSFER_ACTOR_ENERGY_COST = 20   # energy the actor spends, floored by max(0, ...) -- never observed to clamp (0 of 269)
HELP_TARGET_HEALTH_RESTORE = 50          # `help` only; health is a separate quantity from the energy pair above
REST_ENERGY_RESTORE = 80                 # `rest` self-restore: minted, not transferred -- energy is a non-conserved quantity by design


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
