"""
Weights are stored in grams. The user's preferred unit ("kgs" or "lbs") is
only used at the API boundary.
"""

import math

UNITS = ("kgs", "lbs")

_GRAMS_PER_UNIT = {
    "kgs": 1000.0,
    "lbs": 453.59237,
}


def normalise_unit(unit: str | None) -> str:
    return unit if unit in UNITS else "kgs"


def to_number(value, default: float = 0.0) -> float:
    """Leniently parse user input into a non-negative float."""
    if value is None or value == "":
        return default
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    if math.isnan(number) or math.isinf(number) or number < 0:
        return default
    return number


def to_grams(weight, unit: str | None) -> float:
    return round(to_number(weight) * _GRAMS_PER_UNIT[normalise_unit(unit)], 2)


def from_grams(grams, unit: str | None) -> float:
    return round(to_number(grams) / _GRAMS_PER_UNIT[normalise_unit(unit)], 2)
