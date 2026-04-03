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

    def __init__(self, name, team, sideline, position = None, location=None):
        self.name = name
        self.team = team # Not a team instance
        self.fatigue = 0
        self.position = position
        self.location = location
        self.sideline = sideline
        self.possession = False

    def __repr__(self):
        return (
            f"Player(name={self.name!r}, team={self.team}, fatigue={self.fatigue:.3f}, "
            f"sideline={self.sideline})"
        )

    def swap_player(self):
        """Called if the player starts playing or stops playing."""
        self.sideline = not self.sideline

    def update_fatigue(self, delta_fatigue):
        """Update fatigue. Negative delta corresponds to rest (timeouts, halftime, sideline), 
        and a positive delta corresponds to playtime, shots, and pressing (trying to get the
        ball back)."""
        self.fatigue += delta_fatigue

    def update_possession(self, has_possession=None):
        """Updates the possession of this player. Used by match_state.update(possession)."""
        if has_possession is None:
            self.possession = not self.possession
            return

        self.possession = bool(has_possession)
