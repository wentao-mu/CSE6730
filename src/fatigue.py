"""Fatigue accumulation and fatigue-driven performance effects."""

from __future__ import annotations

DEFAULT_ACCUMULATION_RATES = {
    "low": 0.004,
    "medium": 0.006,
    "high": 0.009,
}


def clamp(value, lower=0.0, upper=1.0):
    """Clamp a scalar to the closed interval [lower, upper]."""
    return max(lower, min(upper, value))


def normalize_pressing_level(pressing_level):
    """Map string or numeric intensity inputs onto low/medium/high."""
    if isinstance(pressing_level, str):
        normalized = pressing_level.strip().lower()
        if normalized not in DEFAULT_ACCUMULATION_RATES:
            raise ValueError(
                f"Unsupported pressing level {pressing_level!r}. "
                "Use low, medium, or high."
            )
        return normalized

    if pressing_level <= 0.9:
        return "low"
    if pressing_level >= 1.1:
        return "high"
    return "medium"


def _fatigue_params(params=None):
    return (params or {}).get("fatigue", {})


def accumulation_rate(pressing_level, params=None):
    """Return the per-step fatigue gain for a pressing level."""
    fatigue_params = _fatigue_params(params)
    rates = fatigue_params.get("accumulation_rates", DEFAULT_ACCUMULATION_RATES)
    return float(rates[normalize_pressing_level(pressing_level)])


def fatigue_penalty_multiplier(fatigue_level, params=None):
    """Convert fatigue into a multiplier for pressing effectiveness."""
    fatigue_params = _fatigue_params(params)
    slope = float(fatigue_params.get("pressing_penalty_slope", 0.5))
    minimum = float(fatigue_params.get("min_effective_pressing", 0.65))
    return clamp(1.0 - slope * fatigue_level, minimum, 1.0)


def attacking_fatigue_multiplier(fatigue_level, params=None):
    """Fatigue slightly reduces attacking execution quality."""
    fatigue_params = _fatigue_params(params)
    slope = float(fatigue_params.get("attacking_penalty_slope", 0.2))
    minimum = float(fatigue_params.get("min_attacking_multiplier", 0.75))
    return clamp(1.0 - slope * fatigue_level, minimum, 1.0)


def accumulate_fatigue_level(current_fatigue, pressing_level, params=None, steps=1):
    """Apply linear fatigue growth and return the updated fatigue value."""
    next_fatigue = current_fatigue + accumulation_rate(pressing_level, params) * steps
    return clamp(next_fatigue)


def recover_fatigue_level(current_fatigue, params=None):
    """Apply halftime recovery or bench recovery."""
    fatigue_params = _fatigue_params(params)
    recovery = float(fatigue_params.get("halftime_recovery", 0.18))
    return clamp(current_fatigue - recovery)


def calculate_fatigue(player, press_intensity, params=None):
    """Compatibility wrapper returning the fatigue delta for one step."""
    del player
    return accumulation_rate(press_intensity, params)
