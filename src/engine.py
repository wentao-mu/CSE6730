from players import Player
from teams import Team
from match_state import MatchState
import random
import utils
import yaml

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

# Add players to team
team1 = Team(players_team1)
team2 = Team(players_team2)
teams = [team1, team2]
mstate = MatchState(teams) # holds all information on teams and players within those teams

# time step loop
# -----------------------------
max_time = 90*60 # Game is 90 minutes and we use seconds
time_per_step = max_time / tsteps # timestep in seconds

# Decide kickoff
mstate.kickoff() # gives possession attribute = True to one of the teams and False to other

for tstep in range(tsteps):
    # 1. Update fatigue of players based on current actions/defensive choices
    for team in mstate.teams:
        for player in team.playing:  # only update fatigue for players on the field
            player.fatigue += utils.calculate_fatigue(player, pressing_intensity)
            player.fatigue = min(player.fatigue, 1.0)  # cap fatigue at 1.0
    
    # 2. Handle substitutions if players are fatigued
    for team in mstate.teams:
        for player in team.playing:
            if player.fatigue > config["fatigue_threshold"] and len(team.sidelines) > 0:
                # Pick a random sideline player to swap in
                sub_in = random.choice(team.sidelines)
                team.swap_player(player, sub_in)
                player.swap_player()  # update sideline status
                sub_in.swap_player()  # update sideline status
    
    # 3. Update match events (possession, shots, scoring)
    # Possession can change based on defensive choices
    if utils.should_change_possession(mstate.possession):
        mstate.update_possession(1 - mstate.possession)
    
    # Attempt a shot if in possession
    scoring_team = mstate.teams[mstate.possession]
    if utils.attempt_shot(scoring_team):
        mstate.score[mstate.possession] += 1
    
    # 4. Update the match time
    mstate.time += time_per_step

    # Optional: log match state
    # utils.log_match_state(mstate)