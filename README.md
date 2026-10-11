# Job Hunter

Three times a day, GitHub looks for **part-time bar, waiting and front-of-house
jobs** within a **20-minute Dott ride of Montpelier station** and **emails you**
each new one, from the same Gmail account House Hunter uses (sender name
"Job Hunter"). Each job comes with a **CV and cover letter written for that job**
attached, plus ready-made answers for the usual application-form questions.
It runs on GitHub's computers, so your laptop can be off.

**Keep this repository private.** It contains your CV details.

## Where jobs come from

| Source | Needs |
|---|---|
| Mitchells & Butlers careers site (Browns, Miller & Carter, All Bar One, Castle pubs and more) | nothing |
| Reed.co.uk | free key: `REED_API_KEY` from reed.co.uk/developers/jobseeker |
| Adzuna (pulls in adverts from lots of job sites) | free keys: `ADZUNA_APP_ID` and `ADZUNA_APP_KEY` from developer.adzuna.com |

Indeed isn't included: it blocks automated tools and has no job-seeker API, so
set up Indeed's own email alerts if you want those too.

## Setting it up

Add these in the GitHub repo → **Settings → Secrets and variables → Actions → New repository secret**:

| Secret | What to put |
|---|---|
| `SMTP_USER` | the same Gmail address as House Hunter |
| `SMTP_PASSWORD` | the same Gmail app password as House Hunter |
| `EMAIL_TO` | where the job emails go |
| `ANTHROPIC_API_KEY` | optional. With it, Claude tailors every CV and cover letter to the advert (a few pence per job). Without it you get a decent standard version. |
| `REED_API_KEY`, `ADZUNA_APP_ID`, `ADZUNA_APP_KEY` | optional, for more jobs (see above) |

Then **Actions → Job hunter → Run workflow** to test it.

## Changing things

- **Your details:** `profile.yaml`. The CVs are built only from what's in here. They're
  reworded for each job but never made up. Anything still marked `TODO` stops CVs
  being made until you fill it in.
- **Ride time, job types, how many jobs per email:** `config.yaml`.
- **Pause it:** Actions → Job hunter → "..." → Disable workflow.

## Applying

Every email has an **Open the advert & apply** button for each job. The CV and cover
letter are attached, and the "answers for application forms" can be copied straight
into the form. Mitchells & Butlers jobs don't need a CV: you sign up once on their
site, then each application takes about 2 minutes.

If an advert says "email your CV to ...", Job Hunter can send the application for you.
Turn on `auto_apply.email` in `config.yaml` to allow it. The email goes from the alerts
Gmail under your name, and replies come to the email in `profile.yaml`.

## Good to know

- You're only emailed about each job once. If nothing new turns up, you get no email.
- If an email fails to send, the jobs are kept and sent with the next one.
- Ride times use real street routes (OpenStreetMap) at an average of 16 km/h, plus 3
  minutes to find and unlock a Dott. Adverts that only say "Bristol" are still sent,
  marked "location unclear".
- `data/seen.json` is its memory. Delete an entry to be sent that job again.
- `applications/` keeps every CV and cover letter it has made.
- These sites' terms discourage heavy automated use, so keep this for personal use.

## Running on your own computer instead

Copy `.env.example` to `.env` and fill it in. Don't run both at once.

| Command | What it does |
|---|---|
| `pip install -r requirements.txt` | Install what it needs (once) |
| `python -m jobhunter run --dry-run` | Search and show what matches, without saving anything |
| `python -m jobhunter run` | Find new jobs and write their CVs and cover letters |
| `python -m jobhunter notify --dry-run` | Show the email it would send |
| `python -m jobhunter notify` | Send the email |
