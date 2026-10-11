"""Reed.co.uk jobseeker API. Free key from https://www.reed.co.uk/developers/jobseeker"""

import os
from datetime import datetime, timedelta

import requests
from bs4 import BeautifulSoup

from ..models import Job

API = "https://www.reed.co.uk/api/1.0"


def _key() -> str | None:
    return os.environ.get("REED_API_KEY")


def _pay(item: dict) -> str:
    lo, hi = item.get("minimumSalary"), item.get("maximumSalary")
    if not lo and not hi:
        return ""
    return f"£{lo:,.2f}" if lo == hi or not hi else f"£{lo or 0:,.2f} - £{hi:,.2f}"


def fetch(cfg: dict, session: requests.Session) -> list[Job]:
    key = _key()
    if not key:
        print("  reed: skipped (no REED_API_KEY)")
        return []
    search = cfg["search"]
    cutoff = datetime.now() - timedelta(days=search["max_age_days"])
    jobs: dict[str, Job] = {}
    for keywords in search["reed_keywords"]:
        r = session.get(
            f"{API}/search",
            params={
                "keywords": keywords,
                "locationName": search["postcode"],
                "distanceFromLocation": search["radius_miles"],
                "partTime": "true" if search["part_time_only"] else None,
                "resultsToTake": 100,
            },
            auth=(key, ""),
            timeout=30,
        )
        r.raise_for_status()
        for item in r.json().get("results", []):
            try:
                if datetime.strptime(item.get("date", ""), "%d/%m/%Y") < cutoff:
                    continue
            except ValueError:
                pass
            job_id = str(item["jobId"])
            jobs[job_id] = Job(
                source="reed",
                source_id=job_id,
                title=item.get("jobTitle", ""),
                employer=item.get("employerName", ""),
                url=item.get("jobUrl") or f"https://www.reed.co.uk/jobs/{job_id}",
                location=item.get("locationName", ""),
                pay=_pay(item),
                hours="part-time" if search["part_time_only"] else "",
                description=item.get("jobDescription", ""),
                posted=item.get("date", ""),
            )
    return list(jobs.values())


def fetch_description(job: Job, session: requests.Session) -> str:
    r = session.get(f"{API}/jobs/{job.source_id}", auth=(_key(), ""), timeout=30)
    r.raise_for_status()
    detail = r.json()
    if detail.get("externalUrl"):
        job.url = detail["externalUrl"]
    html = detail.get("jobDescription") or job.description
    return BeautifulSoup(html, "html.parser").get_text("\n", strip=True)
