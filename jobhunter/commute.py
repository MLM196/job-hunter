"""Estimate the Dott ride time from the origin (Montpelier station) to a job.

Postcodes are geocoded with postcodes.io and the route distance comes from the
public OSRM bicycle router, so the estimate follows real streets. If either
service is down we fall back to straight-line distance times a detour factor.
"""

import math
import re
import time

import requests

from .models import Job
from .settings import DATA, load_json, save_json

POSTCODE_RE = re.compile(r"\b([A-Z]{1,2}\d[A-Z\d]?)\s*(\d[A-Z]{2})\b", re.I)
BRISTOL_OUTCODE_RE = re.compile(r"\b(BS\d{1,2})\b", re.I)
ROUTER = "https://routing.openstreetmap.de/routed-bike/route/v1/driving"
DETOUR_FACTOR = 1.35
CACHE_PATH = DATA / "geo_cache.json"


def find_postcode(*texts: str) -> str | None:
    for text in texts:
        if m := POSTCODE_RE.search(text or ""):
            return f"{m.group(1)} {m.group(2)}".upper()
    for text in texts:
        if m := BRISTOL_OUTCODE_RE.search(text or ""):
            return m.group(1).upper()
    return None


def haversine_km(lat1, lon1, lat2, lon2) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


class Commute:
    def __init__(self, cfg: dict, session: requests.Session):
        self.origin = (cfg["origin"]["lat"], cfg["origin"]["lon"])
        self.speed = cfg["commute"]["dott_speed_kmh"]
        self.overhead = cfg["commute"]["overhead_minutes"]
        self.session = session
        self.cache = load_json(CACHE_PATH, {"postcodes": {}, "routes": {}})

    def save(self) -> None:
        save_json(CACHE_PATH, self.cache)

    def geocode(self, postcode: str) -> tuple[float, float] | None:
        key = postcode.replace(" ", "").upper()
        if key in self.cache["postcodes"]:
            return tuple(self.cache["postcodes"][key]) if self.cache["postcodes"][key] else None
        is_outcode = " " not in postcode
        url = f"https://api.postcodes.io/{'outcodes' if is_outcode else 'postcodes'}/{key}"
        try:
            r = self.session.get(url, timeout=20)
            result = r.json().get("result") if r.ok else None
        except requests.RequestException:
            return None  # don't cache network failures
        coords = [result["latitude"], result["longitude"]] if result and result.get("latitude") else None
        self.cache["postcodes"][key] = coords
        return tuple(coords) if coords else None

    def route_km(self, lat: float, lon: float) -> float:
        key = f"{lat:.4f},{lon:.4f}"
        if key in self.cache["routes"]:
            return self.cache["routes"][key]
        olat, olon = self.origin
        try:
            r = self.session.get(f"{ROUTER}/{olon},{olat};{lon},{lat}", params={"overview": "false"}, timeout=20)
            time.sleep(1)  # the public router asks for at most one request a second
            routes = r.json().get("routes") if r.ok else None
            if routes:
                km = round(routes[0]["distance"] / 1000, 2)
                self.cache["routes"][key] = km
                return km
        except (requests.RequestException, ValueError):
            pass
        return round(haversine_km(olat, olon, lat, lon) * DETOUR_FACTOR, 2)

    def locate(self, job: Job) -> None:
        """Fill in the job's coordinates and ride estimate where we can."""
        if job.lat is None or job.lon is None:
            job.postcode = job.postcode or find_postcode(job.location, job.title, job.description)
            if job.postcode and (coords := self.geocode(job.postcode)):
                job.lat, job.lon = coords
        if job.lat is None or job.lon is None:
            return
        job.ride_km = self.route_km(job.lat, job.lon)
        job.ride_minutes = round(job.ride_km / self.speed * 60 + self.overhead)
