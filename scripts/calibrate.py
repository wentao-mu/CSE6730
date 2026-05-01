"""
Calibrate transition probabilities from StatsBomb open data.

Pipeline:
    raw event JSON → zone + event classification → counts → probabilities → transitions.json
"""

from __future__ import annotations

import json
from pathlib import Path
from collections import defaultdict
import argparse

DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "statsbomb"
OUTPUT_PATH = Path(__file__).resolve().parents[1] / "data" / "calibration" / "transitions.json"


def get_zone(x: float) -> str:
    """
    Map StatsBomb x-coordinate (0–120) to coarse zones.
    """
    if x < 40:
        return "build_up"
    elif x < 80:
        return "midfield"
    return "final_third"


def has_location(event):
    return "location" in event and event["location"] is not None


def same_team(e1, e2):
    return e1.get("team", {}).get("id") == e2.get("team", {}).get("id")


def is_shot(event):
    return event.get("type", {}).get("name") == "Shot"


def is_pass(event):
    return event.get("type", {}).get("name") == "Pass"


def pass_completed(event):
    return event.get("pass", {}).get("outcome") is None


def is_turnover(e1, e2):
    """
    Possession changes between consecutive events.
    """
    if e2 is None:
        return False
    return not same_team(e1, e2)


def is_progress(e1, e2):
    """
    Forward movement in x direction.
    """
    if not (has_location(e1) and has_location(e2)):
        return False

    x1 = e1["location"][0]
    x2 = e2["location"][0]

    return x2 > x1 + 3  # threshold to avoid noise


def classify_event(e1, e2):
    """
    Assign one of:
    - shot
    - turnover
    - progress
    - stay
    """

    if is_shot(e1):
        return "shot"

    if is_turnover(e1, e2):
        return "turnover"

    if is_progress(e1, e2):
        return "progress"

    return "stay"



def process_match(events, counts):
    """
    Update counts dict with one match's events.
    """

    for i in range(len(events) - 1):
        e1 = events[i]
        e2 = events[i + 1]

        if not has_location(e1):
            continue

        x = e1["location"][0]
        zone = get_zone(x)

        event_type = classify_event(e1, e2)

        counts[zone][event_type] += 1
        counts[zone]["total"] += 1


def load_all_matches(data_dir, limit=None):
    """
    Load all JSON match files. Truncates if a limit is given.
    """
    # files = list(data_dir.glob("*.json"))
    files = sorted(data_dir.glob("*.json"))[:limit] if limit else list(data_dir.glob("*.json"))
    
    if not files:
        raise FileNotFoundError(f"No StatsBomb data found in {data_dir}")

    matches = []
    for f in files:
        with f.open("r", encoding="utf-8") as handle:
            matches.append(json.load(handle))

    return matches


def build_transition_matrix(counts):
    """
    Convert raw counts → normalized probabilities.
    """
    matrix = {}

    for zone, data in counts.items():
        total = data["total"]

        if total == 0:
            continue

        probs = {
            k: v / total
            for k, v in data.items()
            if k != "total"
        }

        # Ensure all expected keys exist
        for key in ("progress", "turnover", "shot", "stay"):
            probs.setdefault(key, 0.0)

        # Normalize (safety)
        s = sum(probs.values())
        if s > 0:
            probs = {k: v / s for k, v in probs.items()}

        matrix[zone] = probs

    return matrix


def main(limit=None):
    counts = defaultdict(lambda: defaultdict(int))
    matches = load_all_matches(DATA_DIR, limit=limit)

    if limit:
        matches = matches[:limit]

    print(f"Processing {len(matches)} matches...")

    for match in matches:
        process_match(match, counts)

    matrix = build_transition_matrix(counts)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    with OUTPUT_PATH.open("w", encoding="utf-8") as f:
        json.dump(matrix, f, indent=2)

    print("\nTransition matrix saved to:", OUTPUT_PATH)
    print("\n--- SAMPLE OUTPUT ---")
    for zone, probs in matrix.items():
        print(zone, {k: round(v, 3) for k, v in probs.items()})



if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, help="Limit number of matches for quick testing")
    args = parser.parse_args()

    main(limit=args.limit)