"""Adzuna job search API. Free keys from https://developer.adzuna.com"""

import os

import requests
from bs4 import BeautifulSoup

from ..models import Job

API = "https://api.adzuna.com/v1/api/jobs/gb/search"
MAX_PAGES = 3


def _clean(html: str) -> str:
    return BeautifulSoup(html or "", "html.parser").get_text(" ", strip=True)


def _pay(item: dict) -> str:
    lo, hi = item.get("salary_min"), item.get("salary_max")
    if not lo:
        return ""
    unit = "/hr" if lo < 100 else " a year"
    pay = f"£{lo:,.2f}{unit}" if lo == hi or not hi else f"£{lo:,.2f} - £{hi:,.2f}{unit}"
    return pay + (" (estimated)" if str(item.get("salary_is_predicted")) == "1" else "")


def fetch(cfg: dict, session: requests.Session) -> list[Job]:
    app_id, app_key = os.environ.get("ADZUNA_APP_ID"), os.environ.get("ADZUNA_APP_KEY")
    if not (app_id and app_key):
        print("  adzuna: skipped (no ADZUNA_APP_ID / ADZUNA_APP_KEY)")
        return []
    search = cfg["search"]
    params = {
        "app_id": app_id,
        "app_key": app_key,
        "what_or": search["adzuna_what_or"],
        "where": search["postcode"],
        "distance": round(search["radius_miles"] * 1.609),
        "max_days_old": search["max_age_days"],
        "results_per_page": 50,
        "sort_by": "date",
        "content-type": "application/json",
    }
    if search["part_time_only"]:
        params["part_time"] = 1
    jobs = []
    for page in range(1, MAX_PAGES + 1):
        r = session.get(f"{API}/{page}", params=params, timeout=30)
        r.raise_for_status()
        results = r.json().get("results", [])
        for item in results:
            contract = item.get("contract_time", "")
            jobs.append(
                Job(
                    source="adzuna",
                    source_id=str(item["id"]),
                    title=_clean(item.get("title", "")),
                    employer=(item.get("company") or {}).get("display_name", ""),
                    url=item.get("redirect_url", ""),
                    location=(item.get("location") or {}).get("display_name", ""),
                    lat=item.get("latitude"),
                    lon=item.get("longitude"),
                    pay=_pay(item),
                    hours={"part_time": "part-time", "full_time": "full-time"}.get(contract, ""),
                    description=_clean(item.get("description", "")),
                    posted=item.get("created", "")[:10],
                )
            )
        if len(results) < params["results_per_page"]:
            break
    return jobs


def fetch_description(job: Job, session: requests.Session) -> str:
    return job.description  # Adzuna only gives a snippet; the full advert is behind the redirect link
