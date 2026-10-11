"""Optional: apply automatically when an advert says to email a CV somewhere.

Off by default (config.yaml -> auto_apply.email). Sends from the alerts Gmail
account under your name, with replies going to the email in profile.yaml.
"""

import re
from pathlib import Path

from . import mailer
from .models import Job
from .tailor import TailoredApplication

EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
# The address has to appear close to wording like "send your CV to"...
CUE_RE = re.compile(r"(send|email|e-mail|forward|submit)\b.{0,40}\b(cv|resume|application)", re.I)
# ...and must not look like a privacy or no-reply mailbox.
SKIP_RE = re.compile(r"noreply|no-reply|privacy|gdpr|dpo|unsubscribe|dataprotection", re.I)


def find_application_email(description: str) -> str | None:
    for m in EMAIL_RE.finditer(description):
        address = m.group(0).rstrip(".")
        nearby = description[max(0, m.start() - 120): m.start()]
        if CUE_RE.search(nearby) and not SKIP_RE.search(address):
            return address
    return None


def send_application(profile: dict, job: Job, app: TailoredApplication, folder: Path, to: str) -> None:
    mailer.send(
        subject=f"Application: {job.title} - {profile['name']}",
        to=to,
        text=app.cover_letter,
        sender_name=profile["name"],
        reply_to=profile["email"],
        attachments=[(p, p.name) for p in sorted(folder.glob("*.docx"))],
    )
