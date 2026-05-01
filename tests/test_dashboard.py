from pathlib import Path

import pandas as pd

from app import (
    apply_filters,
    available_experimental_factors,
    detect_event_level_columns,
    detect_factor_columns,
    detect_metric_columns,
    find_output_csvs,
    grouped_metric_summary,
    load_results_csv,
    summarize_match_state,
    summarize_numeric_columns,
)
from scripts.run_experiment import summarize_state


class FakeTeam:
    def __init__(self, fatigue, effective_pressing_value):
        self.fatigue = fatigue
        self._effective_pressing_value = effective_pressing_value

    def effective_pressing(self, config=None):
        return self._effective_pressing_value


class FakeState:
    score = [1, 0]
    teams = [FakeTeam(0.42, 0.91), FakeTeam(0.31, 0.87)]
    event_log = [
        {"type": "keep_possession", "possession": 0, "fatigue": [0.10, 0.08]},
        {"type": "shot", "team": 0, "possession": 0, "xg": 0.12, "fatigue": [0.30, 0.20]},
        {"type": "shot", "team": 1, "possession": 1, "xg": 0.08, "fatigue": [0.42, 0.31]},
    ]


def test_find_output_csvs_and_load_results_csv(tmp_path):
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    csv_path = output_dir / "experiment.csv"
    csv_path.write_text("home_xg,home_pressing\n0.12,high\n", encoding="utf-8")

    found = find_output_csvs(output_dir)
    loaded = load_results_csv(found[0])

    assert found == [csv_path]
    assert loaded.loc[0, "home_xg"] == 0.12


def test_detect_metric_and_factor_columns():
    df = pd.DataFrame(
        {
            "home_xg": [0.1, 0.2],
            "away_shots": [3, 4],
            "home_possession": [0.55, 0.45],
            "home_pressing": ["high", "low"],
            "fatigue_model": ["linear", "linear"],
        }
    )

    metrics = detect_metric_columns(df)
    factors = detect_factor_columns(df)

    assert metrics["xg"] == ["home_xg"]
    assert metrics["shots"] == ["away_shots"]
    assert metrics["possession"] == ["home_possession"]
    assert "home_pressing" in factors


def test_summaries_filters_and_event_detection():
    df = pd.DataFrame(
        {
            "run": [0, 1, 2],
            "home_xg": [0.1, 0.2, 0.3],
            "home_pressing": ["high", "high", "low"],
            "minute": [5, 10, 15],
            "event_type": ["shot", "turnover", "shot"],
        }
    )

    filtered = apply_filters(df, {"home_pressing": ["high"]})
    numeric_summary = summarize_numeric_columns(filtered)
    grouped = grouped_metric_summary(df, "home_xg", "home_pressing")
    factors = available_experimental_factors(df)
    event_columns = detect_event_level_columns(df)

    assert len(filtered) == 2
    assert "home_xg" in set(numeric_summary["metric"])
    assert grouped.loc[grouped["home_pressing"] == "high", "count"].item() == 2
    assert "home_pressing" in set(factors["factor"])
    assert {"minute", "event_type"}.issubset(event_columns)


def test_match_summaries_include_fatigue_and_effective_pressing():
    app_summary = summarize_match_state(FakeState(), config={})
    script_summary = summarize_state(FakeState(), config={})

    for summary in (app_summary, script_summary):
        assert summary["home_final_fatigue"] == 0.42
        assert summary["away_final_fatigue"] == 0.31
        assert summary["home_avg_fatigue"] > summary["away_avg_fatigue"]
        assert summary["home_effective_pressing"] == 0.91
        assert summary["away_effective_pressing"] == 0.87
