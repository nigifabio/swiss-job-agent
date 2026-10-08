# Job sources and the crawler

Choose sources with `PROVIDERS` in `.env` or on the Settings page (`;`-separated).

| Provider | What | Needs |
|---|---|---|
| `ats` | company career sites listed in `data/watchlist.json`: Greenhouse, Lever, Ashby, SmartRecruiters, Workday, Personio, Recruitee, Teamtailor, Workable, SAP SuccessFactors, Prospective, Oracle Recruiting, Hireserve; plus the public boards everybody gets (below) | nothing for the public boards; a watchlist for more |
| `jobup` | jobs.ch + jobup.ch (the sites' unofficial search backend) | – |
| `jobroom` | Job-Room / work.swiss (SECO) public ads, by canton (`JOBROOM_CANTONS`, else from `WHERE`) | – |
| `remote` | Remotive, Remote OK, Himalayas, Jobicy; only roles open to Switzerland / Europe / worldwide | – |
| `adzuna` | aggregator | `ADZUNA_APP_ID` + `ADZUNA_APP_KEY` ([developer.adzuna.com](https://developer.adzuna.com/)) |
| `careerjet` | aggregator | `CAREERJET_API_KEY` |
| `jooble` | aggregator | `JOOBLE_API_KEY` ([jooble.org/api/about](https://jooble.org/api/about)) |
| `email` | job-alert emails (LinkedIn, Indeed, jobs.ch/jobup.ch, Job-Room, Glassdoor) from a mailbox, opened **read-only** | `IMAP_HOST`, `IMAP_USER`, `IMAP_PASSWORD` |

Keyed sources and email stay silent until configured. The Careerjet and Jooble result formats were
built from their documentation; report an issue if they change.

**Job-alert emails:** use a dedicated mailbox (for Gmail, a separate account with an app password),
subscribe it to the alerts of LinkedIn, Indeed, jobs.ch and so on, and set the `IMAP_*` values. The
mailbox is only read, never changed.

**Never scraped:** LinkedIn, Indeed and Glassdoor (terms of use, bot blocking, risk to your own
account). Their alert emails cover them.

## Filters applied to every source

A title must contain a `TITLE_KEYWORDS` word (a trailing `*` matches a prefix, e.g. `coordinat*`) and
none of `TITLE_EXCLUDE`; the location must match `LOCATION_KEYWORDS`, or be remote and open to
CH / Europe / EMEA / worldwide (`ALLOW_REMOTE`, `REMOTE_REGIONS`); the ad must be in one of `LANGUAGES`.

## Duplicates

1. **Exact fingerprint:** title + company + location (lowercased, spaces tidied).
2. **Loose fingerprint:** ignores gender markers (H/F, m/w/d), work rates (80-100%), accents,
   punctuation, company suffixes (AG, SA, Sàrl, Schweiz…) and everything after the first word of the
   location.

A posting matching either fingerprint of a stored one is skipped and the first source found is kept.
Jobs you add by hand are never merged. Job-Room ads republished from jobs.ch/jobup.ch are skipped:
the `jobup` source has them with the real employer.

## Public boards (everybody gets them)

`app/watchlists/public.json` lists large Swiss employers and administrations that are crawled for every person,
on top of their own watchlist (the title, place and language filters still decide what is kept). Today:

| Employer | System | What |
|---|---|---|
| État de Vaud | Oracle Recruiting | the canton's administration, courts, schools, social services |
| CHUV | Hireserve | the university hospital in Lausanne: care, administration, technical, research |
| EPFL | SAP SuccessFactors | research, technical and administrative jobs in Lausanne |
| BCV | SAP SuccessFactors | Banque Cantonale Vaudoise |
| SICPA | SAP SuccessFactors | Prilly head office (and sites abroad, filtered out by your towns) |
| État de Genève | the canton's own list page | administration, police, schools, social services |
| HUG | SmartRecruiters | Geneva university hospitals |
| imad | SmartRecruiters | home care in Geneva |
| Hospice général | SmartRecruiters | social services in Geneva |
| Université de Genève | Hireserve | academic, technical and administrative jobs |
| SIG Genève | SAP SuccessFactors | Services Industriels de Genève |
| État de Fribourg | SAP SuccessFactors | the canton's administration |
| Groupe E | SAP SuccessFactors | energy company (Fribourg, Vaud) |
| Confédération suisse | Prospective | the federal administration (jobs.admin.ch) |
| La Poste | SAP SuccessFactors | Swiss Post (jobs in your regions and for your search terms) |
| Suva | SAP SuccessFactors | accident insurance, agencies across Switzerland |
| Coop | SAP SuccessFactors | shops, logistics, restaurants (jobs in your regions and for your search terms) |

`PUBLIC_BOARDS=0` in `.env` turns them off. To add an employer that uses one of these systems to your own
watchlist, give its address in a seed file (`Company = https://...`):

- **SAP SuccessFactors**: the feed address `https://<career site>/services/rss/job/` (the site gives its 20 newest
  jobs plus 20 per search: one search per region and search term of yours);
- **Prospective**: an address containing `/careercenter/<number>` (in the page source of the career page);
- **Oracle Recruiting**: the career address `https://<host>.oraclecloud.com/hcmUI/CandidateExperience/fr/sites/<site>`.
- **Hireserve**: add the entry by hand to `data/watchlist.json`: `{"company": "...", "ats": "hireserve", "slug": "<host>/<web_site_id>/<default town>"}`
  (the number is the `p_web_site_id` in the portal's addresses).

## Company career sites (watchlist)

```bash
docker compose run --rm scheduler python -m app.discover app/companies.romandie.txt
```

probes each company in the seed file for nine career-site systems and merges the hits into
`data/watchlist.json`. Seed files in the repo: `app/companies.seed.txt` (Swiss tech),
`app/companies.romandie.txt` (Geneva/Vaud employers with tech teams),
`app/companies.vaud-services.txt` (hotels, retail, logistics, watchmaking, services). Write your own:
one company per line, or `Company = https://careers-url` to add a board directly (Workday often needs
this).

A board is kept only if its declared company name matches the company searched for, so a company
with the same short name isn't picked up by mistake. Re-check an existing watchlist with
`python -m app.discover --verify`. The setup wizard seeds a watchlist from `app/watchlists/`.

## Crawler behaviour

- Timeouts, connection errors, 429 and 5xx are retried with backoff (honouring Retry-After, at most
  60 s); other 4xx fail at once; requests to the same host are paced.
- One failing board or source never stops the others. Details are fetched only for new postings that
  pass the filters.
- **Scan health:** per-source counts and errors are stored after each scan and shown on the dashboard,
  with a warning when a source errors or drops to zero. API keys, the IMAP password and URLs holding
  keys are never written into errors or logs.
- The scheduler does not rescan when a container restarts, and a lock keeps "Scan now" and the
  scheduler from overlapping.
