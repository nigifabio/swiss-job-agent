# Swiss Job Agent

Self-hosted job search assistant for the Swiss market. It scans job boards and company
career pages, ranks every posting against your skills, tracks your applications from
"new" to "offer", writes a tailored CV and cover letter for each job, and produces the
monthly **ORP / RAV proof-of-search report** ("Preuves des recherches personnelles").

- **Private by design:** runs on your own machine, your data stays in one SQLite file.
- **No AI service, no paid API:** CVs, letters and scores are rule-based and only use
  facts from your own profile. Nothing is invented.
- **Human in the loop:** it never logs into your accounts and never submits an application.
- **Multilingual:** postings in English, French, German and Italian; CVs and letters in the
  posting's language when you provide a reviewed translation of your profile.

## Quick start

Needs Docker (with the compose plugin), git and curl, on Linux or macOS.

```bash
git clone https://github.com/nigifabio/swiss-job-agent.git
cd swiss-job-agent
./install.sh
```

The installer asks a few questions, creates `.env`, builds the image, starts it and checks
it is healthy. Open http://127.0.0.1:8080: the **setup wizard** imports your CV (PDF/Word)
or LinkedIn export, suggests target roles and builds the search for you.

```bash
./install.sh upgrade   # latest version, with a backup first and automatic rollback
./install.sh backup    # database + your files into backups/
./install.sh status
```

Full guide: [docs/installation.md](docs/installation.md).

**No clone, prebuilt image** (amd64 + arm64, from `ghcr.io`):

```bash
mkdir swiss-job-agent && cd swiss-job-agent
curl -fsSLO https://raw.githubusercontent.com/nigifabio/swiss-job-agent/main/jobagent && chmod +x jobagent
./jobagent init && ./jobagent up
```

Day to day, in either setup: `./jobagent scan`, `logs`, `update`, `backup`, `discover`…
see [docs/docker.md](docs/docker.md).

## What it does

| | |
|---|---|
| **Find** | jobs.ch / jobup.ch, Job-Room (work.swiss), 12 career-site systems (Workday, SmartRecruiters, SAP SuccessFactors, Oracle, Prospective...) including the cantons of Vaud, Geneva and Fribourg, the Confederation, CHUV, HUG, EPFL, UNIGE, BCV, La Poste and Coop, remote boards, optional aggregators (Adzuna, Careerjet, Jooble) and your job-alert emails (LinkedIn, Indeed...). Duplicates across sources are merged. |
| **Rank** | 0-100 match score from your skills; mark skills you have or want to avoid straight from a posting. |
| **Track** | new · shortlisted · applied · interview · offer · rejected, with contacts, notes, follow-up reminders and a status history. |
| **Write** | tailored CV (PDF) and a Swiss-format cover letter per job, a CV for a type of role, or a CV from keywords. |
| **Report** | weekly/monthly ORP report as PDF, CSV or print, plus stats against your monthly target. |
| **Swiss specifics** | ORP monthly target and reminders, the official form 716.007 filled in, assignments with deadlines, spontaneous applications, travel time by public transport, work-rate filter, conditions a posting mentions (permit, language, licence). Interface in English, French and German. |

## Two ways to run it

1. **One person, one instance** (`./install.sh`): the normal case.
2. **Multi-tenant platform** (`./install.sh platform`): invite-only service where each person
   gets an isolated workspace (own containers, network and database) behind Cloudflare Access.
   See [docs/platform.md](docs/platform.md).

## Documentation

- [Installation, upgrade, backup, remote access](docs/installation.md)
- [Docker image and the `jobagent` wrapper](docs/docker.md)
- [User guide](docs/user-guide.md)
- [Job sources and the crawler](docs/sources.md)
- [Settings, profile, CVs and letters](docs/profiles-cv-letters.md)
- [Multi-tenant platform](docs/platform.md)
- [Releasing and the Docker image build](docs/releasing.md)
- [Security model](SECURITY.md)
- Every setting: [.env.example](.env.example)

## Development

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt pytest
.venv/bin/python -m pytest -q tests                       # app
(cd platform && ../.venv/bin/pip install -q -r requirements.txt && ../.venv/bin/python -m pytest -q tests)
```

The tests never touch the network (`tests/conftest.py` fails any real request): crawlers are
tested against recorded API shapes, the Cloudflare Access check with real signed tokens, and
every page, link, download and form of the app is crawled.

Stack: Python 3.13, FastAPI + Jinja (server-rendered), SQLite, reportlab, httpx, Docker Compose.

## A note on sources

LinkedIn, Indeed and Glassdoor are never scraped (terms of use, and the risk to your own
account); their alert emails cover them. The jobs.ch / jobup.ch source uses the sites'
unofficial search backend: check that its use is acceptable to you. Remotive and Remote OK
postings link back to them and name them as the source, as their terms require.

## License

[MIT](LICENSE)
