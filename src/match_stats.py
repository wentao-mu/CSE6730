"""Aggregate statistics derived from an EventLog."""

from collections import Counter, defaultdict


class MatchStats:
    def __init__(self, event_log):
        self.event_log = event_log

    def shots(self):
        counter = Counter()
        for event in self.event_log.events:
            if event.event_type == "shot":
                counter[event.team] += 1
        return dict(counter)

    def goals(self):
        counter = Counter()
        for event in self.event_log.events:
            if event.event_type == "goal":
                counter[event.team] += 1
        return dict(counter)

    def total_xg(self):
        totals = defaultdict(float)
        for event in self.event_log.events:
            if event.event_type == "shot":
                totals[event.team] += event.xg
        return dict(totals)

    def possession_percentage(self):
        possession_counts = Counter()
        total = 0
        for event in self.event_log.events:
            if hasattr(event, "team"):
                possession_counts[event.team] += 1
                total += 1

        if total == 0:
            return {}

        return {team: count / total for team, count in possession_counts.items()}

    def zone_occupancy(self):
        zones = defaultdict(Counter)
        for event in self.event_log.events:
            zones[event.team][event.zone] += 1
        return {team: dict(zone_counts) for team, zone_counts in zones.items()}

    def xg_timeline(self):
        cumulative = defaultdict(float)
        timeline = []

        for event in sorted(self.event_log.events, key=lambda item: item.minute):
            if event.event_type == "shot":
                cumulative[event.team] += event.xg

            timeline.append(
                {
                    "minute": event.minute,
                    "team_a_xg": cumulative.get("A", 0.0),
                    "team_b_xg": cumulative.get("B", 0.0),
                }
            )

        return timeline

    def summary(self):
        return {
            "shots": self.shots(),
            "goals": self.goals(),
            "total_xg": self.total_xg(),
            "possession_percentage": self.possession_percentage(),
            "zone_occupancy": self.zone_occupancy(),
        }
