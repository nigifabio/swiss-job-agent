# User guide

## Finding jobs

- All configured sources are scanned every 12 hours (`FETCH_INTERVAL_HOURS`). **↻ Scan now** on the
  homepage starts a scan at once; the page shows "Scanning…" and refreshes itself, then the time of
  the last scan, how many new jobs it found and a count per source.
- If a source failed or suddenly returned nothing (the site changed or blocked the scan), a
  **⚠ Last scan had problems** banner explains it.
- New jobs are sorted by a **match score** (0-100): how many of your skills the posting mentions
  (words in the title count triple).

## Tracking applications

- Tabs: new · shortlisted · applied · interview · offer · rejected · discarded.
- On every job in a list: **✓ Applied**, **☆ Shortlist**, and **✕ Not for me**: the first click greys the job out (it
  stays where it is, **↩ Keep** brings it back), a second click (**✕ Remove**) moves it to *discarded*. From the
  *discarded* tab, **↩ Back to new** restores it.
- **⊘ Position filled** (list and job page): the posting is no longer open. If you had applied, the job becomes a
  refusal with the reason "Poste déjà pourvu" and stays in your ORP report; if not, it leaves the list.
- Entering an **applied date** on the job page moves the job to *Applied* (the report and the stats count by that
  date); moving a job back to *new* or *shortlisted* removes the date.
- **Open & apply ↗** opens the posting in a new tab, then asks **"Did you apply?"**: *Yes* moves the
  job to Applied and records the date.
- The job page keeps the contact, recruiter, CV version sent, applied and follow-up dates, notes, and
  the fields the ORP report needs (employment rate, how you applied, assigned by the ORP, reason for a
  refusal). Follow-ups due in the next 14 days show on the homepage.
- **+ Add application** records jobs found elsewhere (LinkedIn, a recruiter, a referral).

## Reading a posting

- The job page shows the **full posting** (fetched the first time you open it).
- Skills are highlighted: **green** = in your skills, **red** = asked for but not in your skills,
  grey = a word you avoid.
- Each skill has buttons: **+ I have it** (count it from now on), **⛔ Avoid** (postings asking for it
  lose 25 points), **✕** (stop counting it). Open jobs are re-ranked at once and later scans use the
  same lists. The **CV** page lists them all (Skills & preferences) to add, undo or restore.

## CV and cover letter

- **Generate tailored CV** (job page): a PDF, in the posting's language when you have a translated
  profile in it; summary and bullet order are chosen for that job, from your own facts only.
- **Write cover letter** (job page): a Swiss-format letter in the same language as the CV, naming the
  role, the company, the skills the posting asks for and your 3 most relevant achievements. It is a
  **draft**: edit it, **Save edits**, then **Download PDF**.
- **CV page → CV for a role**: pick a type of job; the CV leads with your skills that matter for it.
  Skills the role often needs that your profile lacks are listed so you can add them if true.
- **CV page → CV from keywords**: paste a posting's requirements; keywords your profile supports get a
  Key skills line and move matching bullets up; unsupported ones are listed, never added.

## Settings

**Settings** (top menu) holds the search itself: search terms, titles to keep or skip, towns,
languages, skills, sources, scan interval. Saving re-ranks the jobs already found. With the wizard
enabled you can also **edit your profile** or **re-run the setup wizard** there.

## Stats and the ORP report

- **Stats**: applications this month vs your ORP target (`ORP_MONTHLY_TARGET`, default 10), this week,
  total, answer rate, interview rate, average days to a first answer, weekly and monthly charts (click
  a bar for that period's report), funnel, sources, how you applied.
- **ORP report**: "Preuves des recherches personnelles en vue de trouver un emploi" for a week or a
  month, with **PDF**, **CSV (Excel)** and **Print**. Each application carries the link to the posting it was for (a link in the page, the address
  under the job title in the PDF, a column in the CSV). Copy the rows into Job-Room (work.swiss) or attach
  the PDF, as your ORP/RAV office asks, by the 5th of the following month. The AVS number is left blank
  to fill in by hand.
