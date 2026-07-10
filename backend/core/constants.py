"""Core-owned constants and simulation-time helpers. No wall-clock, ever."""

ENGINE_VERSION = "0.1.0"
SCHEMA_VERSION = "0.1.0"

GRID_WIDTH = 20
GRID_HEIGHT = 20
NUM_PEOPLE = 6
NUM_ANIMALS = 6
NUM_TREES = 16

REGROWTH_INTERVAL = 5
REGROWTH_AMOUNT = 6
SHELTER_COST = 10

DAY_LENGTH_TICKS = 100


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
