"""Shared match snapshot that the simulation engine mutates over time."""

from __future__ import annotations

import random

class MatchState:
    """
    This class holds values and information that describe the state of the soccer match. This
    class does not contain logic, only values. Fucntions to alter these values are held by the
    engine.

    Parameters
    ----------
    
    """
    def __init__(self, teams, zone="midfield", possession=None):
        if len(teams) != 2:
            raise ValueError("MatchState currently supports exactly two teams.")

        self.teams = list(teams)
        self.score = [self.teams[0].score, self.teams[1].score]
        self.time = 0.0
        self.zone = zone
        self.possession = possession
        self.event_log = []

        if self.possession is not None:
            self._sync_possession_flags()

    @property
    def minute(self):
        return self.time / 60.0

    @property
    def fatigue_levels(self):
        return [team.fatigue for team in self.teams]
        
    def kickoff(self, rng=None):
        """Decides the winner of the kickoff to determine initial possession."""
        rng = rng or random
        kickoff_winner = rng.choice([0, 1])
        self.possession = kickoff_winner
        self._sync_possession_flags()

    def _sync_possession_flags(self):
        for index, team in enumerate(self.teams):
            team.possession = index == self.possession

    def update_possession(self, prev_player=None, new_player=None):
        """
        Changes and updates the team with possession based on player possession.

        Parameters
        ----------
        prev_player : Player | int | None
            The previous ball holder or previous team index.
        new_player : Player | int | None
            The new ball holder or the new team index.
        """
        if self.possession is None and new_player is None:
            raise ValueError("Cannot infer a possession change before kickoff.")

        if hasattr(prev_player, "update_possession"):
            prev_player.update_possession(False)

        if isinstance(new_player, int):
            new_team_index = new_player
        elif hasattr(new_player, "team"):
            new_team_index = new_player.team
            new_player.update_possession(True)
        elif new_player is None:
            new_team_index = 1 - self.possession
        else:
            raise TypeError("new_player must be a Player instance, team index, or None.")

        self.possession = new_team_index
        self._sync_possession_flags()

    def update_score(self, scoring_team):
        if isinstance(scoring_team, int):
            team_index = scoring_team
        elif scoring_team == self.teams[0]:
            team_index = 0
        elif scoring_team == self.teams[1]:
            team_index = 1
        else:
            raise ValueError(f"A dog named {scoring_team} ran onto the field and scored. He is not a valid team!")

        self.teams[team_index].score += 1
        self.score[team_index] += 1

    def switch_possession(self):
        self.update_possession(new_player=1 - self.possession)

    def advance_time(self, seconds):
        self.time += seconds

    def log_event(self, event_type, **payload):
        event = {"type": event_type, **payload}
        self.event_log.append(event)
        return event
