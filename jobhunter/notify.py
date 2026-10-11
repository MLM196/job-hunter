"""Email new jobs to EMAIL_TO, House Hunter style. Unsent jobs stay in
data/pending.json and go out with the next successful email."""

import html
import os

from . import mailer
from .settings import DATA, ROOT, load_json, save_json

PENDING = DATA / "pending.json"
BUTTON = "display:inline-block;margin-top:10px;padding:8px 14px;background:#1f4e5f;color:#fff;border-radius:6px;text-decoration:none"
BOX = "background:#f4f6f7;border-radius:6px;padding:10px 12px;margin-top:10px;font-size:14px;white-space:pre-wrap"


def queue(items: list[dict]) -> None:
    save_json(PENDING, load_json(PENDING, []) + items)


def _facts(item: dict) -> str:
    return " · ".join([item["ride"], item["pay"] or "pay not stated", item["hours"] or "hours not stated"])


def _text(items: list[dict]) -> str:
    parts = []
    for it in items:
        lines = [f"{it['title']} - {it['employer']}", it["location"], _facts(it)]
        lines += [x for x in (it.get("status"), it.get("fit_summary")) if x]
        lines.append(it["url"])
        if it.get("cover_letter"):
            lines += ["", "Cover letter:", it["cover_letter"]]
        parts.append("\n".join(lines))
    return "\n\n-----\n\n".join(parts)


def _html(items: list[dict], intro: str) -> str:
    cards = []
    for it in items:
        e = {k: html.escape(str(v)) for k, v in it.items() if isinstance(v, str)}
        answers = "".join(
            f"<p style='margin:8px 0 2px'><b>{html.escape(a['question'])}</b></p>{html.escape(a['answer'])}"
            for a in it.get("answers", [])
        )
        cards.append(f"""
<div style="border:1px solid #ddd;border-radius:8px;padding:12px 14px;margin:0 0 14px">
  <div style="font-size:17px;font-weight:600">{e['title']}</div>
  <div style="margin:3px 0;color:#333">{e['employer']} · {e['location']}</div>
  <div style="color:#666;font-size:13px">{html.escape(_facts(it))} · via {e['source']}</div>
  {f"<div style='margin-top:6px;color:#0a7d32'><b>{e['status']}</b></div>" if it.get('status') else ''}
  {f"<div style='margin-top:6px;font-style:italic;color:#444'>{e['fit_summary']}</div>" if it.get('fit_summary') else ''}
  <a href="{e['url']}" style="{BUTTON}">Open the advert &amp; apply</a>
  {f"<div style='{BOX}'><b>Cover letter</b> (also attached)<br><br>{e['cover_letter']}</div>" if it.get('cover_letter') else ''}
  {f"<div style='{BOX};white-space:normal'><b>Answers for application forms</b>{answers}</div>" if answers else ''}
</div>""")
    return f"""<div style="font-family:system-ui,Arial,sans-serif;max-width:600px">
<p>{html.escape(intro)}</p>{''.join(cards)}
<p style="color:#888;font-size:12px">Job Hunter · edit config.yaml in the repo to change what you're sent.</p></div>"""


def _attachments(items: list[dict]) -> list:
    files = []
    for it in items:
        folder = ROOT / it["folder"] if it.get("folder") else None
        if folder and folder.exists():
            for doc in sorted(folder.glob("*.docx")):
                label = doc.stem if len(items) == 1 else f"{doc.stem} ({it['employer']})"
                files.append((doc, f"{label}.docx"))
    return files


def notify(dry_run: bool = False) -> None:
    items = load_json(PENDING, [])
    if not items:
        print("No new jobs to send.")
        return
    n = len(items)
    subject = (f"New job: {items[0]['title']} - {items[0]['employer']} ({items[0]['ride']})" if n == 1
               else f"{n} new jobs near Montpelier")
    intro = (f"{n} new part-time job{'s' if n > 1 else ''} within your Dott range. "
             "Each one has a tailored CV and cover letter attached." if any(i.get("folder") for i in items)
             else f"{n} new part-time job{'s' if n > 1 else ''} within your Dott range. "
                  "Fill in the TODOs in profile.yaml to get a tailored CV with each one.")
    to = os.environ.get("EMAIL_TO")
    if dry_run or not (mailer.configured() and to):
        if not dry_run:
            print("Email not set up (SMTP_USER, SMTP_PASSWORD, EMAIL_TO) - printing instead and keeping the jobs queued.")
        print(f"\n--- would email: {subject} ---\n{_text(items)}\n--- attachments: {[a[1] for a in _attachments(items)]}")
        return
    try:
        mailer.send(subject, to, _text(items), _html(items, intro), attachments=_attachments(items))
    except OSError as e:  # smtplib errors are OSErrors
        print(f"Email failed ({e!r}) - the jobs stay queued for next time.")
        raise SystemExit(1)
    print(f"Emailed {n} job(s) to {to}.")
    save_json(PENDING, [])
