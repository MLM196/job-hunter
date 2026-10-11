from dataclasses import dataclass


@dataclass
class Job:
    source: str
    source_id: str
    title: str
    employer: str
    url: str
    location: str = ""
    postcode: str | None = None
    lat: float | None = None
    lon: float | None = None
    pay: str = ""
    hours: str = ""  # "part-time", "full-time" or "" when the advert doesn't say
    description: str = ""
    posted: str = ""
    ride_minutes: float | None = None
    ride_km: float | None = None

    @property
    def id(self) -> str:
        return f"{self.source}:{self.source_id}"

    @property
    def dedupe_key(self) -> tuple[str, str]:
        return (self.title.strip().lower(), self.employer.strip().lower())
