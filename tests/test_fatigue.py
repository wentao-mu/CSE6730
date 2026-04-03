from src import fatigue
from src.players import Player


TEST_CONFIG = {
    "fatigue": {
        "accumulation_rates": {"low": 0.01, "medium": 0.02, "high": 0.04},
        "halftime_recovery": 0.05,
        "pressing_penalty_slope": 0.5,
        "min_effective_pressing": 0.6,
        "attacking_penalty_slope": 0.2,
        "min_attacking_multiplier": 0.75,
    }
}


def test_high_press_accumulates_faster_than_low():
    low = fatigue.accumulate_fatigue_level(0.0, "low", TEST_CONFIG, steps=3)
    high = fatigue.accumulate_fatigue_level(0.0, "high", TEST_CONFIG, steps=3)

    assert high > low


def test_recovery_and_penalty_are_clamped():
    recovered = fatigue.recover_fatigue_level(0.02, TEST_CONFIG)
    multiplier = fatigue.fatigue_penalty_multiplier(1.0, TEST_CONFIG)

    assert recovered == 0.0
    assert multiplier == 0.6


def test_calculate_fatigue_accepts_numeric_press_intensity():
    player = Player("Test", team=0, sideline=False)

    delta = fatigue.calculate_fatigue(player, 1.2, TEST_CONFIG)

    assert delta == TEST_CONFIG["fatigue"]["accumulation_rates"]["high"]
