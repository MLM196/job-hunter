"""Mitchells & Butlers careers site (Browns, Miller & Carter, All Bar One, Castle pubs, ...)."""

import re
import time

import requests
from bs4 import BeautifulSoup

from ..models import Job

BASE = "https://www.mbcareersandjobs.com"
FALLBACK_LIST_PATH = "/jobs?options=22427"  # the "View all" link on the Bristol page
MAX_PAGES = 10


def _soup(session: requests.Session, url: str) -> BeautifulSoup:
    r = session.get(url, timeout=30)
    r.raise_for_status()
    r.encoding = "utf-8"
    return BeautifulSoup(r.text, "html.parser")


def _text(tile, selector: str) -> str:
    el = tile.select_one(selector)
    return " ".join(el.get_text(" ", strip=True).split()) if el else ""


def _bristol_list_path(session: requests.Session) -> str:
    try:
        link = _soup(session, f"{BASE}/jobs-in-bristol").find("a", href=re.compile(r"^/jobs\?options="))
        return link["href"].split("&page=")[0] if link else FALLBACK_LIST_PATH
    except requests.RequestException:
        return FALLBACK_LIST_PATH


def fetch(cfg: dict, session: requests.Session) -> list[Job]:
    list_path = _bristol_list_path(session)
    jobs: dict[str, Job] = {}
    for page in range(1, MAX_PAGES + 1):
        soup = _soup(session, f"{BASE}{list_path}&page={page}")
        tiles = soup.select("div.attrax-vacancy-tile[data-jobid]")
        new = [t for t in tiles if t["data-jobid"] not in jobs]
        if not new:
            break
        for tile in new:
            link = tile.select_one("a.attrax-vacancy-tile__title")
            hours = _text(tile, ".attrax-vacancy-tile__option-hours .attrax-vacancy-tile__item-value").lower()
            location = _text(tile, ".attrax-vacancy-tile__location-freetext .attrax-vacancy-tile__item-value")
            jobs[tile["data-jobid"]] = Job(
                source="mab",
                source_id=tile["data-jobid"],
                title=link.get_text(strip=True),
                employer=location.split(",")[0].strip() or "Mitchells & Butlers",
                url=BASE + link["href"],
                location=location,
                pay=_text(tile, ".attrax-vacancy-tile__salary-value"),
                hours="part-time" if "part" in hours else "full-time" if "full" in hours else "",
            )
        time.sleep(1)
    return list(jobs.values())


def fetch_description(job: Job, session: requests.Session) -> str:
    widget = _soup(session, job.url).select_one(".description-widget")
    return widget.get_text("\n", strip=True) if widget else ""
