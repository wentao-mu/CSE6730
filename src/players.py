class Player:
    """
    A class describing the attributes of a player, and controlling the logic of fatigue, sideline, etc.

    Parameters
    ----------
    team : int
        An integer, 0 or 1, that labels which team the player is a part of.
    sideline : bool
        True if the player is on the sideline, false if they are not.
    """

    def __init__(self, team, sideline, position = None, location=None):
        self.team = team
        self.fatigue = 0
        self.position = position
        self.location = location
        self.sideline = sideline

    