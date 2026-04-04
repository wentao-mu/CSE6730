#!/usr/bin/env python3
"""
plot_results.py — Read experiment CSV and produce summary charts.

Usage:
    python scripts/plot_results.py                           # defaults
    python scripts/plot_results.py -i output/my_run.csv      # custom input
    python scripts/plot_results.py --no-show                 # save only, don't open window
"""

import argparse
import os
import sys
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
matplotlib.rcParams.update({
    "figure.facecolor": "white",
    "axes.facecolor": "white",
    "savefig.dpi": 150,
    "font.size": 11,
})


def load_data(path: str) -> pd.DataFrame:
    if not os.path.exists(path):
        print(f"Error: {path} not found. Run run_experiment.py first.")
        sys.exit(1)
    df = pd.read_csv(path)
    print(f"Loaded {len(df)} rows from {path}")
    return df


def plot_xg_comparison(df: pd.DataFrame, output_dir: str):
    """Bar chart comparing mean home xG across pressing levels."""
    grouped = df.groupby("home_pressing")["home_xg"].agg(["mean", "std"])
    # ensure consistent ordering
    order = [lvl for lvl in ["low", "medium", "high"] if lvl in grouped.index]
    grouped = grouped.loc[order]

    fig, ax = plt.subplots(figsize=(6, 4))
    colors = {"low": "#4A90D9", "medium": "#F5A623", "high": "#D94A4A"}
    bars = ax.bar(
        grouped.index,
        grouped["mean"],
        yerr=grouped["std"],
        capsize=5,
        color=[colors.get(lvl, "#888888") for lvl in grouped.index],
        edgecolor="black",
        linewidth=0.6,
    )
    ax.set_xlabel("Home Pressing Style")
    ax.set_ylabel("Mean xG")
    ax.set_title("Home Team xG by Pressing Intensity")
    ax.set_ylim(bottom=0)
    fig.tight_layout()

    path = os.path.join(output_dir, "xg_by_pressing.png")
    fig.savefig(path)
    print(f"  Saved {path}")
    return fig


def plot_shots_comparison(df: pd.DataFrame, output_dir: str):
    """Grouped bar chart: home vs away shots by pressing level."""
    grouped = df.groupby("home_pressing")[["home_shots", "away_shots"]].mean()
    order = [lvl for lvl in ["low", "medium", "high"] if lvl in grouped.index]
    grouped = grouped.loc[order]

    fig, ax = plt.subplots(figsize=(6, 4))
    x = range(len(grouped))
    width = 0.35
    ax.bar(
        [i - width / 2 for i in x],
        grouped["home_shots"],
        width,
        label="Home shots",
        color="#4A90D9",
        edgecolor="black",
        linewidth=0.6,
    )
    ax.bar(
        [i + width / 2 for i in x],
        grouped["away_shots"],
        width,
        label="Away shots",
        color="#D94A4A",
        edgecolor="black",
        linewidth=0.6,
    )
    ax.set_xticks(list(x))
    ax.set_xticklabels(grouped.index)
    ax.set_xlabel("Home Pressing Style")
    ax.set_ylabel("Mean Shots per Match")
    ax.set_title("Shots per Match by Pressing Intensity")
    ax.legend()
    ax.set_ylim(bottom=0)
    fig.tight_layout()

    path = os.path.join(output_dir, "shots_by_pressing.png")
    fig.savefig(path)
    print(f"  Saved {path}")
    return fig


def plot_possession_comparison(df: pd.DataFrame, output_dir: str):
    """Bar chart of home possession % by pressing level."""
    grouped = df.groupby("home_pressing")["home_possession"].mean()
    order = [lvl for lvl in ["low", "medium", "high"] if lvl in grouped.index]
    grouped = grouped.loc[order]

    fig, ax = plt.subplots(figsize=(6, 4))
    colors = {"low": "#4A90D9", "medium": "#F5A623", "high": "#D94A4A"}
    ax.bar(
        grouped.index,
        grouped.values * 100,
        color=[colors.get(lvl, "#888888") for lvl in grouped.index],
        edgecolor="black",
        linewidth=0.6,
    )
    ax.set_xlabel("Home Pressing Style")
    ax.set_ylabel("Possession %")
    ax.set_title("Home Possession % by Pressing Intensity")
    ax.axhline(50, color="gray", linestyle="--", linewidth=0.8, alpha=0.6)
    ax.set_ylim(0, 100)
    fig.tight_layout()

    path = os.path.join(output_dir, "possession_by_pressing.png")
    fig.savefig(path)
    print(f"  Saved {path}")
    return fig


def plot_xg_distribution(df: pd.DataFrame, output_dir: str):
    """Overlaid histograms of home xG distributions by pressing level."""
    fig, ax = plt.subplots(figsize=(7, 4))
    colors = {"low": "#4A90D9", "medium": "#F5A623", "high": "#D94A4A"}

    for level in ["low", "medium", "high"]:
        subset = df[df["home_pressing"] == level]["home_xg"]
        if len(subset) == 0:
            continue
        ax.hist(
            subset,
            bins=20,
            alpha=0.45,
            label=f"{level} press",
            color=colors[level],
            edgecolor="black",
            linewidth=0.4,
        )
    ax.set_xlabel("Home xG")
    ax.set_ylabel("Frequency")
    ax.set_title("Distribution of Home xG by Pressing Intensity")
    ax.legend()
    fig.tight_layout()

    path = os.path.join(output_dir, "xg_distribution.png")
    fig.savefig(path)
    print(f"  Saved {path}")
    return fig


def main():
    parser = argparse.ArgumentParser(description="Plot experiment results.")
    parser.add_argument(
        "-i", "--input",
        default="output/experiment_results.csv",
        help="Path to experiment CSV (default: output/experiment_results.csv)",
    )
    parser.add_argument(
        "-o", "--output-dir",
        default="output/plots",
        help="Directory to save plots (default: output/plots)",
    )
    parser.add_argument(
        "--no-show",
        action="store_true",
        help="Don't display plots (just save to files)",
    )
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)
    df = load_data(args.input)

    print("\nGenerating plots...")
    plot_xg_comparison(df, args.output_dir)
    plot_shots_comparison(df, args.output_dir)
    plot_possession_comparison(df, args.output_dir)
    plot_xg_distribution(df, args.output_dir)

    print(f"\nAll plots saved to {args.output_dir}/")
    if not args.no_show:
        plt.show()


if __name__ == "__main__":
    main()
