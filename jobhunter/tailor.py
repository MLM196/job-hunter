"""Tailor the CV and cover letter to one job with Claude, or fall back to a template."""

import os

import anthropic
import yaml
from pydantic import BaseModel

from .models import Job

SYSTEM = """You help a young job seeker apply for part-time bar and restaurant jobs in Bristol, UK.
You get their profile (the only source of truth about them) and one job advert, and you
prepare their application for that job.

Rules you must never break:
- Use only facts from the profile. Never invent or upgrade employers, dates, duties,
  qualifications, certificates, skills or achievements. Rewording, reordering and choosing
  what to emphasise is fine; adding anything new is not.
- If the advert asks for something the profile doesn't show (a licence, a certain age,
  years of experience), don't claim it. Mention the gap in fit_summary instead.

Style: natural British English, warm and direct, the way a capable young person would write.
No clichés such as "I am writing to express my interest" or "I am a passionate individual".

What to return:
- fit_summary: one sentence for the candidate on how well this job matches and anything
  to double-check before applying (hours, age, location, missing requirements).
- profile_statement: a 2-3 sentence CV opening aimed at this job.
- key_skills: 5-7 short skills from the profile, most relevant to this job first.
- experience: every experience entry from the profile, most relevant to this job first,
  identified by its id, each with 1-3 bullets (under 25 words each) reworded from that
  entry's duties to suit the job.
- cover_letter: under 170 words. Start "Dear Hiring Manager," unless the advert names a
  person. Mention the employer and role, the most relevant experience, and the candidate's
  availability. End with "Best wishes," and the candidate's name on the next line.
- screening_answers: first-person answers (2-4 sentences each) to: "Why do you want to work
  here?", "Tell us about your relevant experience", "What is your availability?" and
  "Why would you be good at this role?"."""


class ExperienceBullets(BaseModel):
    id: str
    bullets: list[str]


class ScreeningAnswer(BaseModel):
    question: str
    answer: str


class TailoredApplication(BaseModel):
    fit_summary: str
    profile_statement: str
    key_skills: list[str]
    experience: list[ExperienceBullets]
    cover_letter: str
    screening_answers: list[ScreeningAnswer]


def _profile_for_prompt(profile: dict) -> str:
    return yaml.safe_dump(profile, sort_keys=False, allow_unicode=True)


def _job_for_prompt(job: Job) -> str:
    return (
        f"Title: {job.title}\nEmployer: {job.employer}\nLocation: {job.location}\n"
        f"Pay: {job.pay or 'not stated'}\nHours: {job.hours or 'not stated'}\n\n"
        f"Advert:\n{job.description[:8000] or '(no description available)'}"
    )


def template_application(profile: dict, job: Job) -> TailoredApplication:
    """Used when there's no ANTHROPIC_API_KEY or the API call fails."""
    hospitality = [e for e in profile["experience"] if e["id"] in ("pub", "restaurant")]
    roles = " and ".join(f"{e['role'].lower()} at {e['employer']}" for e in hospitality) or "hospitality work"
    letter = (
        "Dear Hiring Manager,\n\n"
        f"I'd love to join the team at {job.employer} as {job.title}. I have experience as a {roles}, "
        "so I'm used to busy shifts, looking after customers and working closely with the rest of the team.\n\n"
        "I'm honest, reliable and always on time, and I take pride in doing every job properly. "
        f"My availability is: {profile['availability']}.\n\n"
        "I'd be happy to come in for a trial shift or a chat whenever suits you.\n\n"
        f"Best wishes,\n{profile['name']}"
    )
    return TailoredApplication(
        fit_summary="Template application (no AI tailoring) - read it over before sending.",
        profile_statement=" ".join(profile["summary"].split()),
        key_skills=profile["skills"][:7],
        experience=[ExperienceBullets(id=e["id"], bullets=e["duties"]) for e in profile["experience"]],
        cover_letter=letter,
        screening_answers=[
            ScreeningAnswer(question="What is your availability?", answer=profile["availability"]),
            ScreeningAnswer(question=f"Why do you want to work at {job.employer}?",
                            answer=f"I enjoy hospitality work and think {job.employer} would be a great "
                                   "place to keep building my experience."),
        ],
    )


def _sanitise(app: TailoredApplication, profile: dict) -> TailoredApplication:
    """Keep only experience ids that exist and make sure none were dropped."""
    known = {e["id"]: e for e in profile["experience"]}
    ordered = [x for x in app.experience if x.id in known and x.bullets]
    seen = {x.id for x in ordered}
    ordered += [ExperienceBullets(id=i, bullets=e["duties"]) for i, e in known.items() if i not in seen]
    app.experience = ordered
    return app


def tailor(profile: dict, job: Job, cfg: dict) -> tuple[TailoredApplication, bool]:
    """Returns (application, was_tailored_by_claude)."""
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return template_application(profile, job), False
    client = anthropic.Anthropic()
    try:
        response = client.beta.messages.parse(
            model=cfg["tailoring"]["model"],
            max_tokens=16000,
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
            output_config={"effort": cfg["tailoring"]["effort"]},
            system=SYSTEM,
            messages=[{
                "role": "user",
                "content": f"<profile>\n{_profile_for_prompt(profile)}</profile>\n\n<job>\n{_job_for_prompt(job)}\n</job>",
            }],
            output_format=TailoredApplication,
        )
    except anthropic.AuthenticationError:
        print("  tailor: ANTHROPIC_API_KEY was rejected - using the template")
        return template_application(profile, job), False
    except (anthropic.APIStatusError, anthropic.APIConnectionError) as e:
        print(f"  tailor: Claude API error ({e.__class__.__name__}) - using the template")
        return template_application(profile, job), False

    if response.stop_reason in ("refusal", "max_tokens") or response.parsed_output is None:
        print(f"  tailor: no usable answer (stop_reason={response.stop_reason}) - using the template")
        return template_application(profile, job), False
    return _sanitise(response.parsed_output, profile), True
