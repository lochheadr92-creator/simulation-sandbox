"""Core-owned constants and simulation-time helpers. No wall-clock, ever."""

ENGINE_VERSION = "0.3.0"
SCHEMA_VERSION = "0.2.0"

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
