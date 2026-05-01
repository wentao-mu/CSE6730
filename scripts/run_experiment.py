#!/usr/bin/env python3
"""
run_experiment.py — Run N simulated matches and collect results into a CSV.

Usage examples:
    # 100 matches, both teams medium press, linear fatigue
    python scripts/run_experiment.py --n 100

    # 500 matches, home presses high, away presses low
    python scripts/run_experiment.py --n 500 --home-press high --away-press low

    # Compare all three pressing levels (runs 3 batches)
    python scripts/run_experiment.py --n 300 --sweep-press

    # Custom output path and fatigue model
    python scripts/run_experiment.py --n 200 --fatigue threshold -o output/threshold_run.csv
"""

import argparse
import copy
import sys
import os
import random
import time
import pandas as pd

# allow imports from project root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.engine import load_config, run_match
from src.transitions import load_transition_matrix, build_transition_function


def summarize_state(state) -> dict:
    """Convert MatchState into a flat row used by experiment analysis."""
    home_shots = 0
    away_shots = 0
    home_xg = 0.0
    away_xg = 0.0
    possession_samples = 0
    home_possession_samples = 0

    for event in state.event_log:
        possession = event.get("possession")
        if possession in (0, 1):
            possession_samples += 1
            if possession == 0:
                home_possession_samples += 1

        if event.get("type") != "shot":
            continue

        team_index = event.get("team", possession)
        if team_index == 0:
            home_shots += 1
            home_xg += float(event.get("xg", 0.0) or 0.0)
        elif team_index == 1:
            away_shots += 1
            away_xg += float(event.get("xg", 0.0) or 0.0)

    home_possession = (
        home_possession_samples / possession_samples if possession_samples else 0.5
    )

    return {
        "home_goals": state.score[0],
        "away_goals": state.score[1],
        "home_shots": home_shots,
        "away_shots": away_shots,
        "home_xg": home_xg,
        "away_xg": away_xg,
        "home_possession": home_possession,
    }


def base_experiment_config() -> dict:
    """Load config from YAML when available; otherwise use built-in defaults."""
    try:
        return load_config()
    except ModuleNotFoundError as exc:
        if exc.name != "yaml":
            raise

        # Fallback keeps experiments runnable even when PyYAML is unavailable
        # in the current interpreter (for example system python3).
        return {
            "teams": {
                "team1": {"name": "Team 1", "num_players": 20, "pressing_level": "medium"},
                "team2": {"name": "Team 2", "num_players": 20, "pressing_level": "medium"},
            },
            "team": {"starters": 11},
            "match": {"regulation_minutes": 90, "regulation_steps": 90},
            "pressing": {
                "levels": {"low": 0.9, "medium": 1.0, "high": 1.15},
                "turnover_boost": 0.5,
                "recovery_boost": 0.3,
            },
            "fatigue": {
                "accumulation_rates": {"low": 0.004, "medium": 0.006, "high": 0.009},
                "halftime_recovery": 0.18,
                "pressing_penalty_slope": 0.5,
                "min_effective_pressing": 0.65,
                "attacking_penalty_slope": 0.2,
                "min_attacking_multiplier": 0.75,
            },
            "engine": {"base_turnover_probability": 0.12},
            "pressing_intensity": "medium",
            "fatigue_threshold": 0.75,
            "fatigue_thresh": 0.75,
            "timesteps": 90,
        }


def simulate_batch(
    n: int,
    home_pressing: str,
    away_pressing: str,
    fatigue_model: str,
    use_calibrated_transitions: bool = False,
) -> pd.DataFrame:
    """Run n matches with the given settings and return a DataFrame of summaries."""
    base_config = base_experiment_config()
    rows = []
    transition_matrix = load_transition_matrix()
    transition_fn = build_transition_function(transition_matrix)
    if use_calibrated_transitions:
        matrix = load_transition_matrix()
        transition_fn = build_transition_function(matrix)
    for i in range(n):
        config = copy.deepcopy(base_config)
        config.setdefault("teams", {}).setdefault("team1", {})[
            "pressing_level"
        ] = home_pressing
        config.setdefault("teams", {}).setdefault("team2", {})[
            "pressing_level"
        ] = away_pressing
        config.setdefault("fatigue", {})["model"] = fatigue_model

        state = run_match(
            config=config,
            rng=random.Random(i), # reproducible: seed = run index
            transition_callback=transition_fn,
        )
        summary = summarize_state(state)
        # add experiment metadata
        summary["run"] = i
        summary["home_pressing"] = home_pressing
        summary["away_pressing"] = away_pressing
        summary["fatigue_model"] = fatigue_model
        rows.append(summary)

    return pd.DataFrame(rows)


def main():
    parser = argparse.ArgumentParser(
        description="Run soccer match simulations and save results to CSV."
    )
    parser.add_argument(
        "--n", type=int, default=100, help="Number of matches per configuration (default: 100)"
    )
    parser.add_argument(
        "--home-press",
        choices=["low", "medium", "high"],
        default="medium",
        help="Home team pressing style (default: medium)",
    )
    parser.add_argument(
        "--away-press",
        choices=["low", "medium", "high"],
        default="medium",
        help="Away team pressing style (default: medium)",
    )
    parser.add_argument(
        "--fatigue",
        choices=["linear", "threshold"],
        default="linear",
        help="Fatigue model (default: linear)",
    )
    parser.add_argument(
        "--sweep-press",
        action="store_true",
        help="Run all 3 pressing levels for the home team (low/medium/high) against medium away",
    )
    parser.add_argument(
        "-o", "--output",
        type=str,
        default="output/experiment_results.csv",
        help="Output CSV path (default: output/experiment_results.csv)",
    )
    parser.add_argument(
        "--use-calibrated",
        action="store_true",
        help="Use calibrated transition probabilities from data/calibration/transitions.json",
    )
    args = parser.parse_args()

    os.makedirs(os.path.dirname(args.output), exist_ok=True)

    if args.sweep_press:
        # run three batches: home = low, medium, high vs. away = medium
        dfs = []
        for level in ["low", "medium", "high"]:
            print(f"Running {args.n} matches: home={level} vs away=medium ...")
            t0 = time.time()
            df = simulate_batch(args.n, level, "medium", args.fatigue, use_calibrated_transitions=args.use_calibrated)
            elapsed = time.time() - t0
            print(f"  done in {elapsed:.1f}s")
            dfs.append(df)
        results = pd.concat(dfs, ignore_index=True)
    else:
        print(
            f"Running {args.n} matches: home={args.home_press} "
            f"vs away={args.away_press} ({args.fatigue} fatigue) ..."
        )
        t0 = time.time()
        results = simulate_batch(
            args.n, args.home_press, args.away_press, args.fatigue, use_calibrated_transitions=args.use_calibrated
        )
        elapsed = time.time() - t0
        print(f"  done in {elapsed:.1f}s")

    results.to_csv(args.output, index=False)
    print(f"\nSaved {len(results)} rows to {args.output}")

    # print quick summary to terminal
    print("\n--- Quick Summary ---")
    grouped = results.groupby("home_pressing").agg(
        avg_home_goals=("home_goals", "mean"),
        avg_away_goals=("away_goals", "mean"),
        avg_home_shots=("home_shots", "mean"),
        avg_away_shots=("away_shots", "mean"),
        avg_home_xg=("home_xg", "mean"),
        avg_away_xg=("away_xg", "mean"),
        avg_home_poss=("home_possession", "mean"),
    )
    print(grouped.round(3).to_string())


if __name__ == "__main__":
    main()
