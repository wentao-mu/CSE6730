"""
Fetch StatsBomb open data (matches + events) and store locally.

Pipeline:
    competitions → matches → events → saved JSON files
"""

from __future__ import annotations

import requests
import os
import json
from pathlib import Path
import argparse
import time


BASE_URL = "https://raw.githubusercontent.com/statsbomb/open-data/master/data"

COMPETITIONS_URL = f"{BASE_URL}/competitions.json"
MATCHES_URL = f"{BASE_URL}/matches"
EVENTS_URL = f"{BASE_URL}/events"

DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "statsbomb"



def fetch_json(url):
    """Fetch JSON from a URL with basic error handling."""
    r = requests.get(url)

    if r.status_code != 200:
        raise RuntimeError(f"Failed to fetch {url} (status {r.status_code})")

    return r.json()


def get_competitions():
    """Return all available competitions."""
    return fetch_json(COMPETITIONS_URL)


def filter_competitions(competitions, competition_name=None):
    """
    Optionally filter competitions by name.
    Example: "Premier League", "La Liga", "World Cup"
    """
    if not competition_name:
        return competitions

    return [
        c for c in competitions
        if competition_name.lower() in c["competition_name"].lower()
    ]


def get_matches(competition_id, season_id):
    """Fetch all matches for a competition + season."""
    url = f"{MATCHES_URL}/{competition_id}/{season_id}.json"
    return fetch_json(url)


def get_events(match_id):
    """Fetch event data for a match."""
    url = f"{EVENTS_URL}/{match_id}.json"
    return fetch_json(url)



def fetch_all(competition_filter=None, max_matches=None, delay=0.2):
    """
    Fetch:
    competitions → matches → events

    Parameters:
        competition_filter (str): filter competitions by name
        max_matches (int): limit total matches (for testing)
        delay (float): delay between requests (avoid hammering server)
    """

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    competitions = get_competitions()
    competitions = filter_competitions(competitions, competition_filter)

    print(f"Found {len(competitions)} competitions")

    total_downloaded = 0

    for comp in competitions:
        comp_id = comp["competition_id"]
        season_id = comp["season_id"]

        print(f"\nCompetition: {comp['competition_name']} ({comp_id})")
        print(f"Season: {comp['season_name']} ({season_id})")

        try:
            matches = get_matches(comp_id, season_id)
        except Exception as e:
            print(f"Skipping competition due to error: {e}")
            continue

        print(f"  Matches found: {len(matches)}")

        for match in matches:
            match_id = match["match_id"]
            output_file = DATA_DIR / f"{match_id}.json"

            # Skip if already downloaded
            if output_file.exists():
                continue

            try:
                events = get_events(match_id)

                with output_file.open("w", encoding="utf-8") as f:
                    json.dump(events, f)

                total_downloaded += 1

                print(f"    Downloaded match {match_id}")

                # Stop early if needed
                if max_matches and total_downloaded >= max_matches:
                    print("\nReached max_matches limit.")
                    return

                time.sleep(delay)

            except Exception as e:
                print(f"    Failed match {match_id}: {e}")

    print(f"\nDone. Downloaded {total_downloaded} matches.")



if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--competition",
        type=str,
        help="Filter by competition name (e.g., 'Premier League')"
    )
    parser.add_argument(
        "--max_matches",
        type=int,
        help="Limit number of matches to download"
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.2,
        help="Delay between requests (seconds)"
    )

    args = parser.parse_args()

    fetch_all(
        competition_filter=args.competition,
        max_matches=args.max_matches,
        delay=args.delay,
    )