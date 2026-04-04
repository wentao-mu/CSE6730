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
import sys
import os
import time
import pandas as pd

# allow imports from project root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.engine import run_match


def simulate_batch(
    n: int,
    home_pressing: str,
    away_pressing: str,
    fatigue_model: str,
) -> pd.DataFrame:
    """Run n matches with the given settings and return a DataFrame of summaries."""
    rows = []
    for i in range(n):
        stats = run_match(
            home_pressing=home_pressing,
            away_pressing=away_pressing,
            fatigue_model=fatigue_model,
            seed=i,  # reproducible: seed = run index
        )
        summary = stats.summary()
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
    args = parser.parse_args()

    os.makedirs(os.path.dirname(args.output), exist_ok=True)

    if args.sweep_press:
        # run three batches: home = low, medium, high vs. away = medium
        dfs = []
        for level in ["low", "medium", "high"]:
            print(f"Running {args.n} matches: home={level} vs away=medium ...")
            t0 = time.time()
            df = simulate_batch(args.n, level, "medium", args.fatigue)
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
            args.n, args.home_press, args.away_press, args.fatigue
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
