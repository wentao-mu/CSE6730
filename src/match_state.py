from teams import Team
import random

class MatchState:
    """
    This class holds values and information that describe the state of the soccer match. This
    class does not contain logic, only values. Fucntions to alter these values are held by the
    engine.

    Parameters
    ----------
    
    """
    def __init__(self, teams):
        self.teams = teams # [team1, team2]
        self.score = [teams[0].score, teams[1].score] # team 1's score, then team 2's score
        self.time = 0 # Clock starts at 0. Measured in seconds. Game is 90 minutes long, so the match stops when self.time = 5400 seconds
        self.possession = None # Must be updated at kickoff
        
    def kickoff(self):
        """Decides the winner of the kickoff to determine initial possession."""
        kickoff_winner = random([0,1]) # 0 for team 0, 1 for team 1
        self.possession = kickoff_winner


    def update_possession(self, prev_player, new_player):
        """
        Changes and updates the team with possession based on player possession.

        Parameters
        ----------
        prev_player : Player
            The Player instance that previously had possession of the soccer ball.
        new_player : Player
            The Player instance that now has possession of the ball.
        """
        prev_player.possession = False
        new_player.possession = True

        # 2. Update team possession
        self.teams[0].possession = (new_player.team == 0) # Gives possession to team 1 if the new player is on team 1
        self.teams[1].possession = (new_player.team == 1) # Gives possession to team 2 if player is on team 2

        # 3. Update MatchState.possession as a boolean (True if team 0 has it)
        self.possession = (new_player.team)

    def update_score(self, scoring_team):
        if scoring_team == self.teams[0]:
            self.teams[0].score += 1
        elif scoring_team == self.teams[1]:
            self.teams[1].score += 1
        else:
            raise ValueError(f"A dog named {scoring_team} ran onto the field and scored. He is not a valid team!")

