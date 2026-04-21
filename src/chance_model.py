"""Chance creation helpers based on coarse pitch zones."""

def xg_by_zone(zone: str) -> float:
    """Return a simple xG prior for a shot from the given zone."""
    lookup = {
        "defensive": 0.01,
        "middle": 0.04,
        "attacking": 0.12,
    }
    return lookup.get(zone, 0.03)
