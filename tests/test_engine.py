import random

import pytest

from src.engine import build_default_match_state, run_match_segment


TEST_CONFIG = {
    "teams": {
        "team1": {"name": "Home", "num_players": 16, "pressing_level": "high"},
        "team2": {"name": "Away", "num_players": 16, "pressing_level": "low"},
    },
    "team": {"starters": 11},
    "match": {"regulation_minutes": 90, "regulation_steps": 4},
    "engine": {"base_turnover_probability": 0.1},
    "pressing": {
        "levels": {"low": 0.9, "medium": 1.0, "high": 1.2},
        "turnover_boost": 0.6,
        "recovery_boost": 0.3,
    },
    "fatigue": {
        "accumulation_rates": {"low": 0.02, "medium": 0.03, "high": 0.04},
        "halftime_recovery": 0.05,
        "pressing_penalty_slope": 0.5,
        "min_effective_pressing": 0.6,
        "attacking_penalty_slope": 0.2,
        "min_attacking_multiplier": 0.75,
    },
}


def no_event_transition(match_state, config, rng):
    del config, rng
    return {"type": "noop", "team": match_state.possession}


def test_run_match_segment_updates_fatigue_and_logs_halftime():
    state = build_default_match_state(TEST_CONFIG)

    events = run_match_segment(
        state,
        4,
        TEST_CONFIG,
        rng=random.Random(7),
        transition_callback=no_event_transition,
    )

    halftime_events = [event for event in state.event_log if event["type"] == "halftime"]

    assert len(events) == 4
    assert len(halftime_events) == 1
    assert state.time == pytest.approx(90 * 60)
    assert state.teams[0].fatigue > state.teams[1].fatigue
