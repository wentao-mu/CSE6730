"""Aggregate statistics derived from an EventLog."""

from collections import Counter, defaultdict

class MatchStats:
    def __init__(self, event_log):
        self.event_log = event_log

    def _events(self):
        if hasattr(self.event_log, "events"):
            return self.event_log.events
        return self.event_log

    @staticmethod
    def _get(event, *keys, default=None):
        for key in keys:
            if isinstance(event, dict):
                if key in event:
                    return event[key]
            elif hasattr(event, key):
                return getattr(event, key)
        return default

    @staticmethod
    def _timeline_key(team):
        if team == "A":
            return "team_a_xg"
        if team == "B":
            return "team_b_xg"
        return f"team_{team}_xg"

    def shots(self):
        counter = Counter()
        for event in self._events():
            if self._get(event, "event_type", "type") == "shot":
                team = self._get(event, "team", "possession")
                if team is not None:
                    counter[team] += 1
        return dict(counter)

    def goals(self):
        counter = Counter()
        for event in self._events():
            if self._get(event, "event_type", "type") == "goal":
                team = self._get(event, "team", "possession")
                if team is not None:
                    counter[team] += 1
        return dict(counter)

    def total_xg(self):
        totals = defaultdict(float)
        for event in self._events():
            if self._get(event, "event_type", "type") == "shot":
                team = self._get(event, "team", "possession")
                if team is not None:
                    totals[team] += float(self._get(event, "xg", default=0.0) or 0.0)
        return dict(totals)

    def possession_percentage(self):
        possession_counts = Counter()
        total = 0
        for event in self._events():
            team = self._get(event, "team", "possession")
            if team is not None:
                possession_counts[team] += 1
                total += 1

        if total == 0:
            return {}

        return {team: count / total for team, count in possession_counts.items()}

    def zone_occupancy(self):
        zones = defaultdict(Counter)
        for event in self._events():
            team = self._get(event, "team", "possession")
            zone = self._get(event, "zone")
            if team is None or zone is None:
                continue
            zones[team][zone] += 1
        return {team: dict(zone_counts) for team, zone_counts in zones.items()}

    def xg_timeline(self):
        cumulative = defaultdict(float)
        timeline = []

        events = sorted(
            self._events(),
            key=lambda item: float(self._get(item, "minute", default=0.0) or 0.0),
        )

        for event in events:
            event_type = self._get(event, "event_type", "type")
            team = self._get(event, "team", "possession")
            minute = float(self._get(event, "minute", default=0.0) or 0.0)

            if event_type == "shot" and team is not None:
                cumulative[team] += float(self._get(event, "xg", default=0.0) or 0.0)

            row = {"minute": minute}
            for tracked_team in sorted(cumulative, key=str):
                row[self._timeline_key(tracked_team)] = cumulative[tracked_team]
            timeline.append(row)

        return timeline

    def summary(self):
        return {
            "shots": self.shots(),
            "goals": self.goals(),
            "total_xg": self.total_xg(),
            "possession_percentage": self.possession_percentage(),
            "zone_occupancy": self.zone_occupancy(),
        }
