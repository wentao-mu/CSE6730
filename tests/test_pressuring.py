import pytest

from src import pressing
from src.players import Player
from src.teams import Team


TEST_CONFIG = {
    "pressing": {
        "levels": {"low": 0.9, "medium": 1.0, "high": 1.2},
        "turnover_boost": 0.6,
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


def build_team(name, pressing_level, fatigue_level):
    players = [
        Player(f"{name}_{index}", team=0, sideline=index >= 11)
        for index in range(16)
    ]
    team = Team(players, name=name, pressing_level=pressing_level, starters=11)
    team.fatigue = fatigue_level
    return team


def test_effective_pressing_drops_as_fatigue_rises():
    fresh_team = build_team("Fresh", "high", 0.0)
    tired_team = build_team("Tired", "high", 0.7)

    assert tired_team.effective_pressing(TEST_CONFIG) < fresh_team.effective_pressing(TEST_CONFIG)


def test_apply_pressing_modifiers_normalizes_probabilities():
    attacking_team = build_team("Attack", "medium", 0.4)
    defending_team = build_team("Defend", "high", 0.1)
    base_probabilities = {
        "progress": 0.4,
        "turnover": 0.2,
        "shot": 0.1,
        "stay": 0.3,
    }

    adjusted = pressing.apply_pressing_modifiers(
        base_probabilities,
        attacking_team,
        defending_team,
        TEST_CONFIG,
    )

    assert pytest.approx(sum(adjusted.values())) == 1.0
    assert adjusted["turnover"] > base_probabilities["turnover"]
