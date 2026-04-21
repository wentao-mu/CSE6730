"""Simulation engine utilities with pressing and fatigue hooks wired in."""

from __future__ import annotations

from pathlib import Path
import random

try:
    from .match_state import MatchState
    from .players import Player
    from .teams import Team
    from . import chance_model
    from . import pressing
except ImportError:  # pragma: no cover - allows direct execution from src/
    from match_state import MatchState
    from players import Player
    from teams import Team
    import chance_model
    import pressing


DEFAULT_CONFIG_PATH = Path(__file__).resolve().parents[1] / "config" / "default_params.yaml"


def load_config(config_path=None):
    """Load YAML configuration for the simulator."""
    import yaml

    path = Path(config_path) if config_path else DEFAULT_CONFIG_PATH
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def build_default_match_state(config):
    """Create a minimal two-team match state from config."""
    starters = int(config.get("team", {}).get("starters", 11))
    teams = []

    for team_index, key in enumerate(("team1", "team2")):
        team_config = config.get("teams", {}).get(key, {})
        num_players = int(team_config.get("num_players", 20))
        team_name = team_config.get("name", f"Team {team_index + 1}")
        pressing_level = team_config.get("pressing_level", "medium")
        squad = [
            Player(
                f"{team_name.replace(' ', '_')}_{player_index + 1}",
                team=team_index,
                sideline=player_index >= starters,
            )
            for player_index in range(num_players)
        ]
        teams.append(
            Team(
                squad,
                name=team_name,
                pressing_level=pressing_level,
                starters=starters,
            )
        )

    return MatchState(teams)


def default_transition(match_state, config, rng):
    """Simple possession model used until calibrated transitions are integrated."""
    def zone_for_xg(zone):
        mapping = {
            "build_up": "defensive",
            "midfield": "middle",
            "final_third": "attacking",
            "defensive": "defensive",
            "middle": "middle",
            "attacking": "attacking",
        }
        return mapping.get(zone, "middle")

    attacking_team = match_state.teams[match_state.possession]
    defending_team = match_state.teams[1 - match_state.possession]
    engine_params = config.get("engine", {})
    base_turnover_probability = float(engine_params.get("base_turnover_probability", 0.12))
    turnover_probability = min(
        0.95,
        base_turnover_probability * pressing.turnover_modifier(defending_team, config),
    )

    if rng.random() < turnover_probability:
        previous_team = match_state.possession
        match_state.switch_possession()
        return {
            "type": "turnover",
            "from_team": previous_team,
            "to_team": match_state.possession,
        }

    base_shot_probability = float(engine_params.get("base_shot_probability", 0.08))
    shot_probability = min(
        0.8,
        max(0.0, base_shot_probability * pressing.attacking_success_modifier(attacking_team, config)),
    )

    if rng.random() < shot_probability:
        xg_zone = zone_for_xg(match_state.zone)
        xg = chance_model.xg_by_zone(xg_zone) * pressing.attacking_success_modifier(
            attacking_team,
            config,
        )
        xg = min(0.95, max(0.0, float(xg)))
        is_goal = rng.random() < xg
        if is_goal:
            match_state.update_score(match_state.possession)
        return {
            "type": "shot",
            "team": match_state.possession,
            "zone": match_state.zone,
            "xg": xg,
            "goal": is_goal,
        }

    return {"type": "keep_possession", "team": match_state.possession, "zone": match_state.zone}


def step(match_state, config, rng=None, transition_callback=None, seconds_per_step=60.0):
    """Advance the simulation by one discrete possession step."""
    rng = rng or random.Random()
    transition_callback = transition_callback or default_transition

    if match_state.possession is None:
        match_state.kickoff(rng)

    for team in match_state.teams:
        team.accumulate_fatigue(config)

    event = transition_callback(match_state, config, rng)
    match_state.advance_time(seconds_per_step)
    return match_state.log_event(
        event["type"],
        step=len(match_state.event_log),
        minute=match_state.minute,
        fatigue=match_state.fatigue_levels.copy(),
        possession=match_state.possession,
        **{key: value for key, value in event.items() if key != "type"},
    )


def run_match_segment(match_state, tsteps_segment, config, rng=None, transition_callback=None):
    """
    Run a segment of the match (for now, regulation time) for a given number of steps.
    """
    if tsteps_segment <= 0:
        raise ValueError("tsteps_segment must be positive.")

    rng = rng or random.Random()
    match_minutes = float(config.get("match", {}).get("regulation_minutes", 90))
    seconds_per_step = (match_minutes * 60.0) / tsteps_segment
    halftime_step = tsteps_segment // 2
    events = []

    if match_state.possession is None:
        match_state.kickoff(rng)

    for tstep in range(tsteps_segment):
        if tstep == halftime_step:
            for team in match_state.teams:
                team.accumulate_fatigue(config, halftime=True)
            match_state.log_event(
                "halftime",
                step=tstep,
                minute=match_state.minute,
                fatigue=match_state.fatigue_levels.copy(),
            )

        event = step(
            match_state,
            config,
            rng=rng,
            transition_callback=transition_callback,
            seconds_per_step=seconds_per_step,
        )
        events.append(event)

    return events


def run_match(config=None, rng=None, transition_callback=None):
    """Run one regulation match and return the final MatchState."""
    config = config or load_config()
    match_state = build_default_match_state(config)
    run_match_segment(
        match_state,
        int(config.get("match", {}).get("regulation_steps", config.get("timesteps", 90))),
        config,
        rng=rng,
        transition_callback=transition_callback,
    )
    return match_state


if __name__ == "__main__":
    state = run_match()
    print(f"Final score: {state.score}")
    print(f"Final fatigue: {state.fatigue_levels}")
