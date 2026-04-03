"""Team-level state and behavior for pressing and fatigue."""

from __future__ import annotations

try:
    from . import fatigue
except ImportError:  # pragma: no cover - allows direct execution from src/
    import fatigue

class Team:
    """
    This class describes qualities of a team, such as players, score, and controlling players on 
    the field.

    Parameters
    ----------
    players : list
        A list of Player instances.
    """
    def __init__(self, players, name=None, pressing_level="medium", starters=11):
        self.name = name or "Unnamed Team"
        self.players = list(players)
        self.score = 0
        self.fatigue = 0.0
        self.pressing_level = fatigue.normalize_pressing_level(pressing_level)
        self.playing, self.sidelines = self.split_list(self.players, starters)
        self.possession = False

        for player in self.playing:
            player.sideline = False
        for player in self.sidelines:
            player.sideline = True

    @staticmethod
    def split_list(players, n):
        """
        Splits the list into two lists:
        - first n players go on the field
        - those on the sideline
        
        Parameters:
            players (list): input list
            n (int): number of players to take in the playing list
        
        Returns:
            tuple: (playing, sidelines)
        """
        n = max(0, min(n, len(players)))
        playing = list(players[:n])
        sidelines = list(players[n:])
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
        benching.swap_player()
        sending.swap_player()

    def effective_pressing(self, config=None):
        """Return the fatigue-adjusted pressing level multiplier."""
        pressing_params = (config or {}).get("pressing", {})
        levels = pressing_params.get(
            "levels",
            {"low": 0.9, "medium": 1.0, "high": 1.15},
        )
        base_press = float(levels[self.pressing_level])
        return base_press * fatigue.fatigue_penalty_multiplier(self.fatigue, config)

    def accumulate_fatigue(self, config=None, steps=1, halftime=False):
        """Update team fatigue using a linear accumulation model."""
        if halftime:
            self.fatigue = fatigue.recover_fatigue_level(self.fatigue, config)
        else:
            self.fatigue = fatigue.accumulate_fatigue_level(
                self.fatigue,
                self.pressing_level,
                config,
                steps=steps,
            )

        for player in self.playing:
            player.fatigue = self.fatigue

        return self.fatigue
