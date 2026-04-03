"""Pressing logic and fatigue-aware probability modifiers."""

from __future__ import annotations

try:
    from . import fatigue
except ImportError:  # pragma: no cover - allows direct execution from src/
    import fatigue


def turnover_modifier(defending_team, params=None):
    """Multiplier applied to turnover probabilities created by pressure."""
    pressing_params = (params or {}).get("pressing", {})
    boost = float(pressing_params.get("turnover_boost", 0.5))
    effective_press = defending_team.effective_pressing(params)
    return max(0.1, 1.0 + (effective_press - 1.0) * boost)


def recovery_modifier(defending_team, params=None):
    """Multiplier applied to ball-recovery events for the pressing team."""
    pressing_params = (params or {}).get("pressing", {})
    boost = float(pressing_params.get("recovery_boost", 0.3))
    effective_press = defending_team.effective_pressing(params)
    return max(0.1, 1.0 + (effective_press - 1.0) * boost)


def attacking_success_modifier(attacking_team, params=None):
    """Fatigue slightly reduces the attacker's clean progression and shot quality."""
    return fatigue.attacking_fatigue_multiplier(attacking_team.fatigue, params)


def apply_pressing_modifiers(base_probabilities, attacking_team, defending_team, params=None):
    """
    Apply pressing and fatigue adjustments to a probability table and renormalize it.

    Expected keys include turnover, recovery, progress, shot, and stay, but the function
    only modifies keys that are present.
    """
    adjusted = {key: float(value) for key, value in base_probabilities.items()}

    if "turnover" in adjusted:
        adjusted["turnover"] *= turnover_modifier(defending_team, params)
    if "recovery" in adjusted:
        adjusted["recovery"] *= recovery_modifier(defending_team, params)

    attack_multiplier = attacking_success_modifier(attacking_team, params)
    for key in ("progress", "shot", "attack_success"):
        if key in adjusted:
            adjusted[key] *= attack_multiplier

    total = sum(adjusted.values())
    if total <= 0:
        raise ValueError("Adjusted probabilities must sum to a positive value.")

    return {key: value / total for key, value in adjusted.items()}


def should_possession_change(match_state, params=None, rng=None):
    """Compatibility helper for a simple fatigue-aware possession switch."""
    if match_state.possession is None:
        raise ValueError("Possession must be set before calling should_possession_change.")

    rng = rng or __import__("random").Random()
    defending_team = match_state.teams[1 - match_state.possession]
    engine_params = (params or {}).get("engine", {})
    base_turnover_probability = float(engine_params.get("base_turnover_probability", 0.12))
    probability = min(0.95, base_turnover_probability * turnover_modifier(defending_team, params))
    return rng.random() < probability


def press(match_state, params=None):
    """Compatibility hook for the old engine loop."""
    del match_state, params
    return 1


def change_possession(match_state):
    """Compatibility helper that swaps team possession and returns team indices."""
    previous_team = match_state.possession
    match_state.switch_possession()
    return previous_team, match_state.possession
