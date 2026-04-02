import random

class Team:
    """
    This class describes qualities of a team, such as players, score, and controlling players on 
    the field.

    Parameters
    ----------
    players : list
        A list of Player instances.
    """

    def __init__(self, players):
        self.players = players
        self.playing, self.sidelines = self.split_list(players, 11) # 11 players from a team play at a time.


    def split_list(players, n):
        """
        Splits the list into two lists:
        - n random players go on the field
        - those on the sideline
        
        Parameters:
            players (list): input list
            n (int): number of players to take in the playing list
        
        Returns:
            tuple: (playing, sidelines)
        """
        playing = random.sample(players, n)
        sidelines = [x for x in players if x not in playing]
        
        return playing, sidelines
    
    