import random
import pytest

from src.match_state import MatchState
from src.players import Player
from src.teams import Team
from src.transitions import (
    next_zone,
    previous_zone,
    validate_transition_matrix,
    sample_transition,
    build_transition_function,
)


def build_test_state():
    players1 = [Player(f"A_{i}", team=0, sideline=i >= 11) for i in range(16)]
    players2 = [Player(f"B_{i}", team=1, sideline=i >= 11) for i in range(16)]

    team1 = Team(players1, name="A", pressing_level="medium", starters=11)
    team2 = Team(players2, name="B", pressing_level="medium", starters=11)

    state = MatchState([team1, team2], zone="midfield", possession=0)
    return state


def simple_matrix():
    return {
        "build_up": {"progress": 0.5, "turnover": 0.2, "shot": 0.1, "stay": 0.2},
        "midfield": {"progress": 0.4, "turnover": 0.3, "shot": 0.1, "stay": 0.2},
        "final_third": {"progress": 0.2, "turnover": 0.3, "shot": 0.3, "stay": 0.2},
    }


TEST_CONFIG = {
    "pressing": {
        "levels": {"low": 0.9, "medium": 1.0, "high": 1.2},
        "turnover_boost": 0.5,
        "recovery_boost": 0.3,
    },
    "fatigue": {
        "accumulation_rates": {"low": 0.01, "medium": 0.02, "high": 0.04},
        "halftime_recovery": 0.05,
        "pressing_penalty_slope": 0.5,
        "min_effective_pressing": 0.6,
        "attacking_penalty_slope": 0.2,
        "min_attacking_multiplier": 0.75,
    },
}


def test_next_zone_progression():
    assert next_zone("build_up") == "midfield"
    assert next_zone("midfield") == "final_third"
    assert next_zone("final_third") == "final_third"  # capped


def test_previous_zone_regression():
    assert previous_zone("final_third") == "midfield"
    assert previous_zone("midfield") == "build_up"
    assert previous_zone("build_up") == "build_up"  # capped



def test_validate_transition_matrix_valid():
    matrix = simple_matrix()
    validate_transition_matrix(matrix)  # should not raise


def test_validate_transition_matrix_invalid():
    bad_matrix = {
        "midfield": {"progress": 0.5, "turnover": 0.5}  # missing keys, sums to 1 but incomplete
    }

    bad_matrix["midfield"]["extra"] = 0.5  # sum = 1.5

    with pytest.raises(ValueError):
        validate_transition_matrix(bad_matrix)


def test_sample_transition_returns_valid_event():
    state = build_test_state()
    matrix = simple_matrix()

    rng = random.Random(42)

    event = sample_transition(state, TEST_CONFIG, rng, matrix)

    assert "type" in event
    assert event["type"] in {"turnover", "progress", "shot", "keep_possession"}


def test_turnover_changes_possession():
    state = build_test_state()

    matrix = {
        "midfield": {"turnover": 1.0}
    }

    rng = random.Random(1)

    prev_possession = state.possession

    event = sample_transition(state, TEST_CONFIG, rng, matrix)

    assert event["type"] == "turnover"
    assert state.possession != prev_possession


def test_progress_moves_zone_forward():
    state = build_test_state()

    matrix = {
        "midfield": {"progress": 1.0}
    }

    rng = random.Random(1)

    event = sample_transition(state, TEST_CONFIG, rng, matrix)

    assert event["type"] == "progress"
    assert state.zone == "final_third"


def test_shot_does_not_change_possession_or_zone():
    state = build_test_state()

    matrix = {
        "midfield": {"shot": 1.0}
    }

    rng = random.Random(1)

    prev_possession = state.possession
    prev_zone = state.zone

    event = sample_transition(state, TEST_CONFIG, rng, matrix)

    assert event["type"] == "shot"
    assert state.possession == prev_possession
    assert state.zone == prev_zone


def test_stay_keeps_state_same():
    state = build_test_state()

    matrix = {
        "midfield": {"stay": 1.0}
    }

    rng = random.Random(1)

    prev_possession = state.possession
    prev_zone = state.zone

    event = sample_transition(state, TEST_CONFIG, rng, matrix)

    assert event["type"] == "keep_possession"
    assert state.possession == prev_possession
    assert state.zone == prev_zone



def test_build_transition_function_integration():
    state = build_test_state()
    matrix = simple_matrix()

    transition_fn = build_transition_function(matrix)

    rng = random.Random(123)

    event = transition_fn(state, TEST_CONFIG, rng)

    assert "type" in event