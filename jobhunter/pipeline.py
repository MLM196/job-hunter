"""One run: find jobs, keep the ones that fit, prepare applications, queue notifications."""

from datetime import date

import requests

from . import documents, email_apply, mailer, notify
from .commute import Commute
from .filters import JobFilter
from .models import Job
from .settings import APPLICATIONS, DATA, ROOT, USER_AGENT, find_todos, load_json, load_yaml, save_json
from .sources import SOURCES
from .tailor import tailor

SEEN_PATH = DATA / "seen.json"


def _collect(cfg: dict, session: requests.Session) -> list[Job]:
    jobs, keys = [], set()
    for name, module in SOURCES.items():
        if not cfg["sources"].get(name):
            continue
        try:
            found = module.fetch(cfg, session)
        except (requests.RequestException, ValueError, KeyError) as e:
            print(f"  {name}: failed ({e.__class__.__name__}: {e})")
            continue
        print(f"  {name}: {len(found)} listings")
        for job in found:
            if job.dedupe_key not in keys:  # same job advertised on two sites
                keys.add(job.dedupe_key)
                jobs.append(job)
    return jobs


def run(dry_run: bool = False, limit: int | None = None) -> None:
    cfg, profile = load_yaml("config.yaml"), load_yaml("profile.yaml")
    todos = find_todos(profile)
    if todos:
        print(f"profile.yaml still has TODOs ({', '.join(todos)}) - sending alerts without CVs.")

    session = requests.Session()
    session.headers["User-Agent"] = USER_AGENT
    commute = Commute(cfg, session)
    job_filter = JobFilter(cfg)
    seen = load_json(SEEN_PATH, {})

    print("Searching...")
    candidates = []
    for job in _collect(cfg, session):
        if job.id in seen or job_filter.role_reason(job):
            continue
        commute.locate(job)
        if job_filter.commute_reason(job):
            continue
        candidates.append(job)
    commute.save()
    candidates.sort(key=lambda j: (j.ride_minutes is None, j.ride_minutes or 0))
    candidates = candidates[: limit or cfg["limits"]["max_new_jobs_per_run"]]
    print(f"{len(candidates)} new job(s) match.")

    notifications, emails_sent = [], 0
    for job in candidates:
        print(f"- {job.title} @ {job.employer} ({job.ride_minutes or '?'} min)")
        try:
            job.description = SOURCES[job.source].fetch_description(job, session) or job.description
        except requests.RequestException as e:
            print(f"  couldn't fetch the full advert ({e.__class__.__name__})")

        item = {
            "title": job.title, "employer": job.employer, "location": job.location, "pay": job.pay,
            "hours": job.hours, "url": job.url, "source": job.source,
            "ride": f"~{job.ride_minutes} min" if job.ride_minutes is not None else "location unclear",
        }
        if not todos and not dry_run:
            app, tailored = tailor(profile, job, cfg)
            folder = documents.write_pack(profile, job, app, APPLICATIONS)
            item.update(
                folder=folder.relative_to(ROOT).as_posix(),
                files=sorted(p.name for p in folder.iterdir()),
                fit_summary=app.fit_summary,
                cover_letter=app.cover_letter,
                answers=[a.model_dump() for a in app.screening_answers],
            )
            to = email_apply.find_application_email(job.description)
            if (to and cfg["auto_apply"]["email"] and mailer.configured()
                    and emails_sent < cfg["auto_apply"]["max_emails_per_run"]):
                try:
                    email_apply.send_application(profile, job, app, folder, to)
                    emails_sent += 1
                    item["status"] = f"Applied automatically by email to {to}"
                except OSError as e:  # smtplib errors are OSErrors
                    print(f"  email to {to} failed: {e}")
            elif to:
                item["status"] = f"This advert asks for CVs by email: {to}"
            print(f"  pack written to {item['folder']}{' (tailored by Claude)' if tailored else ' (template)'}")
        notifications.append(item)
        seen[job.id] = {"title": job.title, "employer": job.employer, "found": date.today().isoformat(),
                        "status": item.get("status", "found")}

    if dry_run:
        print("Dry run - nothing saved.")
        for item in notifications:
            print(f"  would notify: {item['title']} - {item['employer']} | {item['ride']} | {item['url']}")
        return
    save_json(SEEN_PATH, seen)
    notify.queue(notifications)
