# Settings, profile, CVs and letters

Everything here is rule-based: no language model, no external service. Documents only ever contain
facts from your own profile.

## Search settings

Start values come from `.env` (every option is documented in [`.env.example`](../.env.example)).
The **Settings** page writes `data/settings.json`, which overrides the `.env` values it contains;
both containers reload it.

| Setting | Purpose |
|---|---|
| `PROVIDERS` | sources, see [sources](sources.md) |
| `SEARCH_TERMS`, `WHERE` | queries and regions (`;`-separated) for the search-based sources |
| `TITLE_KEYWORDS`, `TITLE_EXCLUDE` | titles to keep / drop (`word*` = prefix) |
| `LOCATION_KEYWORDS`, `ALLOW_REMOTE`, `REMOTE_REGIONS` | where |
| `LANGUAGES` | languages of the ads to keep (`en,fr,de,it`) |
| `SCORE_KEYWORDS` | your skills: the basis of the 0-100 match score |
| `ORP_MONTHLY_TARGET` | applications per month your ORP/RAV office asked for (default 10) |
| `CF_TEAM_DOMAIN`, `CF_ACCESS_AUD`, `ALLOWED_EMAILS` | Cloudflare Access check, see [installation](installation.md) |

After changing `SCORE_KEYWORDS` in `.env`:
`docker compose run --rm scheduler python -m app.fetch --rescore`.

## Skill preferences

Set from job pages (**+ I have it**, **⛔ Avoid**, **✕**) and stored in the database: effective skills =
`SCORE_KEYWORDS` − removed + added; each avoided word costs 25 points. A skill matches in every posting
language: catalog skills have French, German and Italian spellings (`sales` = vente / Verkauf /
vendita), see `SKILL_I18N` in `app/roles.py`. Letters use the posting's own word.

## Setup wizard

With `ONBOARDING=1` (the installer's default) the app opens on a wizard until `data/profile.json` exists:

1. **Import** a CV (PDF / Word / text), a **LinkedIn profile PDF** (More → Save to PDF) and/or the
   **LinkedIn data export ZIP** (Settings → Data privacy → Get a copy of your data). Files are parsed
   locally, in a time- and memory-limited subprocess (8 MB, 12 pages at most).
2. **Review** the draft profile: contact, summary, skills, languages with levels, jobs with bullets,
   education.
3. **Target**: roles from a catalog of 37 (titles in EN/FR/DE/IT, best matches pre-ticked), extra
   titles, level, home town and commute radius, remote, posting languages, words to avoid.
4. **Confirm** the generated search (search terms, title words, exclusions by level, towns and cantons
   within the radius, skills, sources) and get a CV for each target role.

Later: **Edit my profile** and **Re-run the setup wizard** on the Settings page.

## Your CV facts: `data/profile.json`

```json
{
  "name": "...", "headline": "...", "summary": "...",
  "contact": {"email": "...", "phone": "...", "linkedin": "...", "location": "..."},
  "expertise": ["..."],
  "experience": [{"title": "...", "org": "...", "loc": "...", "dates": "...", "bullets": ["..."]}],
  "education": ["..."], "extras_title": "Languages", "extras": ["..."]
}
```

Full example: [`examples/profile.example.json`](../examples/profile.example.json). An employer named
`"Confidential"` is left out of letters. This file stays on your machine (`data/` is never in git).

## Translations: `data/profile.<lang>.json`

Reviewed translations of the same facts (`fr`, `it`, `de`). One is used only if it has exactly the
same jobs and number of bullets as `profile.json`, otherwise it is ignored and the CV page says so.
Name and contact always come from `profile.json`. Nothing is translated automatically: write or
review the translation yourself.

## How the documents are built (`app/compose.py`)

- **Language:** the posting's language (detected) if you have a profile in it, else your profile's own
  language. CV and letter always use the same language.
- **Tailored CV:** summary = your opening sentence + your most relevant other sentence + "Directly
  relevant to this role: …" (skills the posting asks for, spelled as the posting spells them); bullets
  in each job ordered by relevance; expertise re-ordered; section headings localised.
- **Cover letter:** sender, recipient, place and date, subject → "I am applying for the {role} position
  at {company}" → your current role and the skills the posting asks for → your 3 most relevant
  achievements → closing; in English, French, Italian or German.
- **Keyword CV:** keywords your profile supports get a Key skills line and move matching bullets up;
  unsupported ones are reported, never added.
- Relevance = content words shared with the posting (stop words removed, title words ×2) + 3 per CV
  skill mentioned.
