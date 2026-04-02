class MatchState:
    """
    This class holds values and information that describe the state of the soccer match. This
    class does not contain logic, only values. Fucntions to alter these values are held by the
    engine.

    Parameters
    ----------
    
    """
    def __init__(self):
        self.teams = [0,1] # team 0 and team 1. Does not require an input
        self.score = [0, 0] # team 1's score, then team 2's score
        
