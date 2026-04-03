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
        self.possession = None # updated at kickoff to be true or false. Updated by MatchState


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
    
    
    def swap_player(self, benching, sending):
        """
        This function updates self.playing and self.sidelines to swap a player who is playing with someone on the sideline.

        Args
        ----
        benching : Player
            A Player instance that is currently on the field.
        sending : Player
            A Player instance that is currently on the sideline.
        """

        # Check that players are in the correct lists
        if benching not in self.playing:
            raise ValueError("Benching player is not currently playing.")
        if sending not in self.sidelines:
            raise ValueError("Sending player is not currently on the sidelines.")

        # Remove players from their current lists
        self.playing.remove(benching)
        self.sidelines.remove(sending)

        # Add them to the opposite lists
        self.playing.append(sending)
        self.sidelines.append(benching)