import re

from .models import Job


def _words(words: list[str]) -> re.Pattern:
    alternatives = "|".join(re.escape(w) for w in sorted(words, key=len, reverse=True))
    return re.compile(rf"(?<![\w&])(?:{alternatives})s?(?![\w&])", re.I)


class JobFilter:
    def __init__(self, cfg: dict):
        search = cfg["search"]
        self.include = _words(search["title_include"])
        self.exclude = _words(search["title_exclude"])
        self.part_time_only = search["part_time_only"]
        self.max_minutes = cfg["commute"]["max_minutes"]
        self.keep_unknown_location = cfg["commute"]["include_unknown_location"]

    def role_reason(self, job: Job) -> str | None:
        """Cheap checks on title and hours. Returns why the job was rejected, or None."""
        if not self.include.search(job.title):
            return "not a bar/floor role"
        if m := self.exclude.search(job.title):
            return f"title mentions '{m.group(0)}'"
        if self.part_time_only:
            if job.hours == "full-time" and "part time" not in job.title.lower():
                return "full-time"
        return None

    def commute_reason(self, job: Job) -> str | None:
        if job.ride_minutes is None:
            return None if self.keep_unknown_location else "location unknown"
        if job.ride_minutes > self.max_minutes:
            return f"{job.ride_minutes} min ride"
        return None
