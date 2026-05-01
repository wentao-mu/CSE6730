"""Chance creation helpers based on coarse pitch zones."""

def xg_by_zone(zone: str, quality_multiplier: float = 1.0) -> float:
    lookup = {
        "defensive": 0.01,
        "middle": 0.04,
        "attacking": 0.12,
    }
    base_xg = lookup.get(zone, 0.03)
    return max(0.0, base_xg * quality_multiplier)

def shot_quality_multiplier(attacking_team, defending_team, params=None) -> float:
    pressing_params = (params or {}).get("pressing", {})
    fatigue_params = (params or {}).get("fatigue", {})

    pressure_penalty_strength = float(pressing_params.get("shot_quality_penalty", 0.25))
    attacking_fatigue_strength = float(fatigue_params.get("shot_quality_fatigue_penalty", 0.10))

    effective_def_press = defending_team.effective_pressing(params)

    pressure_penalty = max(0.75, 1.0 - pressure_penalty_strength * max(0.0, effective_def_press - 1.0))
    fatigue_penalty = max(0.85, 1.0 - attacking_fatigue_strength * attacking_team.fatigue)

    return pressure_penalty * fatigue_penalty
