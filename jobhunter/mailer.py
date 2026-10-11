"""Send email through the same Gmail account House Hunter uses.

Needs SMTP_USER (the Gmail address) and SMTP_PASSWORD (a Gmail app password).
SMTP_HOST / SMTP_PORT default to Gmail.
"""

import os
import smtplib
from email.message import EmailMessage
from pathlib import Path

DOCX_SUBTYPE = "vnd.openxmlformats-officedocument.wordprocessingml.document"


def configured() -> bool:
    return bool(os.environ.get("SMTP_USER") and os.environ.get("SMTP_PASSWORD"))


def send(subject: str, to: str, text: str, html: str | None = None, sender_name: str = "Job Hunter",
         reply_to: str | None = None, attachments: list[tuple[Path, str]] = ()) -> None:
    """attachments: (file on disk, filename shown in the email). Raises on failure."""
    user = os.environ["SMTP_USER"]
    msg = EmailMessage()
    msg["Subject"], msg["From"], msg["To"] = subject, f"{sender_name} <{user}>", to
    if reply_to:
        msg["Reply-To"] = reply_to
    msg.set_content(text)
    if html:
        msg.add_alternative(html, subtype="html")
    for path, filename in attachments:
        msg.add_attachment(path.read_bytes(), maintype="application", subtype=DOCX_SUBTYPE, filename=filename)
    host = os.environ.get("SMTP_HOST") or "smtp.gmail.com"
    with smtplib.SMTP(host, int(os.environ.get("SMTP_PORT") or "587"), timeout=30) as smtp:
        smtp.starttls()
        smtp.login(user, os.environ["SMTP_PASSWORD"])
        smtp.send_message(msg)
