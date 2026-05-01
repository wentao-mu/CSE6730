"""
Data-driven transition model for soccer match simulation.

This module:
- Loads calibrated transition probabilities from data
- Applies pressing + fatigue modifiers
- Samples next event
- Updates match state accordingly
"""

from __future__ import annotations

import json
from pathlib import Path

try:
    from . import chance_model
except ImportError:
    import chance_model


ZONE_ORDER = ["build_up", "midfield", "final_third"]


def next_zone(zone: str) -> str:
    """Advance the ball to the next attacking zone."""
    if zone not in ZONE_ORDER:
        return zone
    idx = ZONE_ORDER.index(zone)
    return ZONE_ORDER[min(idx + 1, len(ZONE_ORDER) - 1)]


def previous_zone(zone: str) -> str:
    """Move the ball backward."""
    if zone not in ZONE_ORDER:
        return zone
    idx = ZONE_ORDER.index(zone)
    return ZONE_ORDER[max(idx - 1, 0)]


DEFAULT_TRANSITION_PATH = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "calibration"
    / "transitions.json"
)


def load_transition_matrix(path=None):
    """Load calibrated transition probabilities from disk."""
    path = Path(path) if path else DEFAULT_TRANSITION_PATH

    if not path.exists():
        raise FileNotFoundError(
            f"Transition matrix not found at {path}. Run calibrate.py first."
        )

    with path.open("r", encoding="utf-8") as f:
        matrix = json.load(f)

    validate_transition_matrix(matrix)
    return matrix


def validate_transition_matrix(matrix):
    """Ensure probabilities are valid."""
    for zone, probs in matrix.items():
        total = sum(probs.values())
        if not (0.99 <= total <= 1.01):
            raise ValueError(
                f"Probabilities for zone '{zone}' do not sum to 1 (got {total})"
            )



def sample_transition(match_state, config, rng, transition_matrix):
    """
    Sample next event based on:
    - current zone
    - calibrated probabilities
    - pressing + fatigue adjustments
    """

    from .pressing import apply_pressing_modifiers

    zone = match_state.zone
    if zone not in transition_matrix:
        raise ValueError(f"Zone '{zone}' not found in transition matrix.")

    attacking_team = match_state.teams[match_state.possession]
    defending_team = match_state.teams[1 - match_state.possession]

    base_probs = transition_matrix[zone]

    adjusted_probs = apply_pressing_modifiers(
        base_probs,
        attacking_team,
        defending_team,
        config,
    )

    events = list(adjusted_probs.keys())
    probabilities = list(adjusted_probs.values())
    event_type = rng.choices(events, probabilities)[0]

    return resolve_event(event_type, match_state, config, rng)



def resolve_event(event_type, match_state, config, rng):
    """
    Convert an abstract event into:
    - state updates
    - structured event output
    """

    if event_type == "turnover":
        prev_team = match_state.possession
        match_state.switch_possession()
        match_state.zone = previous_zone(match_state.zone)
        return {
            "type": "turnover",
            "from_team": prev_team,
            "to_team": match_state.possession,
            "zone": match_state.zone,
        }

    elif event_type == "progress":
        match_state.zone = next_zone(match_state.zone)
        return {
            "type": "progress",
            "team": match_state.possession,
            "zone": match_state.zone,
        }

    elif event_type == "shot":
        attacking_team = match_state.teams[match_state.possession]
        defending_team = match_state.teams[1 - match_state.possession]

        xg_zone_map = {
            "build_up": "defensive",
            "midfield": "middle",
            "final_third": "attacking",
        }
        xg_zone = xg_zone_map.get(match_state.zone, "middle")

        quality_multiplier = chance_model.shot_quality_multiplier(
            attacking_team,
            defending_team,
            config,
        )

        xg = chance_model.xg_by_zone(
            xg_zone,
            quality_multiplier=quality_multiplier,
        )

        is_goal = rng.random() < xg
        if is_goal:
            match_state.update_score(match_state.possession)

        return {
            "type": "shot",
            "team": match_state.possession,
            "zone": match_state.zone,
            "xg": xg,
            "goal": is_goal,
        }

    elif event_type in ("stay", "keep_possession"):
        return {
            "type": "keep_possession",
            "team": match_state.possession,
            "zone": match_state.zone,
        }

    else:
        raise ValueError(f"Unknown event type: {event_type}")


def build_transition_function(transition_matrix):
    """
    Returns a function compatible with engine.step()

    Usage:
        matrix = load_transition_matrix()
        transition_fn = build_transition_function(matrix)

        run_match(..., transition_callback=transition_fn)
    """

    def transition(match_state, config, rng):
        return sample_transition(match_state, config, rng, transition_matrix)

    return transition