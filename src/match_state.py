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


    def update_possession(self, team):
        """Changes and updates the team with possession."""
        if self.possession == 0: # Changing from team 1 to 2
            self.possession = 1
            self.team[1].possession = True
            self.team[0].possession = False
        elif self.possession == 1: # changing from team 2 to 1
            self.possession = 0
            self.team[0].possession = True
            self.team[1].possession = False
        else:
            raise ValueError("The ball's possession was not in team 1 or 2.")

