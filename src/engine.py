from players import Player
from teams import Team
from match_state import MatchState
import pressing
import chance_model
import fatigue
import random
import utils
import yaml


def run_match_segment(mstate, tsteps_segment, pressing_intensity, config):
    """
    Run a segment of the match (regular time or overtime) for a given number of timesteps.

    Parameters
    ----------
    mstate : MatchState
        The current match state object (holds teams, players, score, possession, etc.)
    tsteps_segment : int
        Number of timesteps to run in this segment
    pressing_intensity : float
        Current pressing intensity level
    config : dict
        Configuration dictionary (e.g., fatigue_threshold)
    """
    time_per_step = (90*60) / tsteps_segment  # timestep in seconds
    halftime_flag = False  # Only relevant if running first 90 minutes

    for tstep in range(tsteps_segment):
        # 1. Update fatigue
        for team in mstate.teams:
            for player in team.playing:
                delta_fatigue = fatigue.calculate_fatigue(player, pressing_intensity)
                player.update_fatigue(delta_fatigue)
                player.fatigue = min(player.fatigue, 1.0)

        # 2. Handle substitutions (This will change)
        for team in mstate.teams:
            for player in team.playing:
                if player.fatigue > config["fatigue_threshold"] and len(team.sidelines) > 0:
                    sub_in = random.choice(team.sidelines)
                    team.swap_player(player, sub_in)
                    player.swap_player()
                    sub_in.swap_player()

        # 3. Update match events
        n_presses = pressing.press(mstate)
        for press_step in range(n_presses):
            if pressing.should_possession_change(mstate): # Not sure what parameters are needed. mstate is a placeholder
                prev_player, new_player = pressing.change_possession(mstate) # player who previously had possession, and player who now has possession respectively
                mstate.update_possession(prev_player, new_player)  # flip boolean possession

        scoring_team = mstate.teams[mstate.possession]
        if chance_model.attempt_shot(scoring_team):
            mstate.score[mstate.possession] += 1

        # 4. Update match time
        mstate.time += time_per_step

        # 5. Optional logging
        utils.log_match_state(mstate)

        # 6. Half-time logic
        if mstate.time > 90*60/2 and not halftime_flag:
            halftime_flag = True
            for team in mstate.teams:
                for player in team.players:
                    delta_fatigue = fatigue.calculate_fatigue(player, pressing_intensity)
                    player.update_fatigue(delta_fatigue)

# Main
# =============================

# config stuff
# -----------------------------
with open("config.yaml") as f:
    config = yaml.safe_load(f)

num_players_team1 = config["teams"]["team1"]["num_players"]
num_players_team2 = config["teams"]["team2"]["num_players"]

pressing_intensity = config["pressing_intensity"]
tsteps = config["timesteps"]

# initialization
# ------------------------------
# The Player class splits them into a field/sideline group within __init__
players_team1 = [Player(f"Team1_Player_{i}", team=0, sideline=True) for i in range(num_players_team1)]
players_team2 = [Player(f"Team2_Player_{i}", team=1, sideline=True) for i in range(num_players_team2)]

print(f"Team 1:\n{players_team1}")
print(f"Team 2:\nplayers_team2")

# Add players to team
team1 = Team(players_team1)
team2 = Team(players_team2)
teams = [team1, team2]
mstate = MatchState(teams) # holds all information on teams and players within those teams

# time step loop. Runs the whole game
# -----------------------------------
run_match_segment(mstate, tsteps, pressing_intensity, config)

# Run overtime
# ------------
print("\n=========\nOvertime.\n=========\n")
while mstate.score[0] == mstate.score[1]:
    run_match_segment(mstate, tsteps, pressing_intensity, config)