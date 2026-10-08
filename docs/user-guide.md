# User guide

## Finding jobs

- All configured sources are scanned every 12 hours (`FETCH_INTERVAL_HOURS`). **↻ Scan now** on the
  homepage starts a scan at once; the page shows "Scanning…" and refreshes itself, then the time of
  the last scan, how many new jobs it found and a count per source.
- If a source failed or suddenly returned nothing (the site changed or blocked the scan), a
  **⚠ Last scan had problems** banner explains it.
- New jobs are sorted by a **match score** (0-100): how many of your skills the posting mentions
  (words in the title count triple).
- **★ Best new** (first tab): the ten best-ranked jobs that arrived since your last visit. In the full list
  those jobs carry a **new** badge.
- **The same job from several agencies is one card.** When the employer and one or more agencies advertise
  the same position, the list shows it once with "Same job also posted by". What you do to the card
  (discard, shortlist, applied) is done to its copies; applying to one discards the others as duplicates.
- **Several jobs at once:** tick jobs (or **Select all**), choose a reason, then **Discard the selected**
  or **Shortlist the selected**. Or type a score and discard every job of the list under it (jobs the
  ORP assigned to you are never swept away).
- **📋 My week:** what came in during the last 7 days, the best of it, applications against the monthly
  target, interviews coming up, and what waits for a follow-up.

## Tracking applications

- Tabs: new · shortlisted · applied · interview · offer · rejected · discarded.
- On every job in a list: **✓ Applied**, **☆ Shortlist**, and **✕ Not for me**: the first click greys the job out (it
  stays where it is, **↩ Keep** brings it back), a second click (**✕ Remove**) moves it to *discarded*. From the
  *discarded* tab, **↩ Back to new** restores it.
- **Why?** When a job is greyed out, the **Why?** menu removes it with a reason (not my kind of job, too senior, too
  far, wrong language, work rate, company, duplicate...). The **Stats** page then shows *Why jobs were discarded*:
  how many per reason, which sites they came from, the words those titles share and what to change in Settings.
  The list can be downloaded as CSV, for example to send to the person who tunes the search.
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
languages, skills, sources, scan interval. Saving re-ranks the jobs already found, and when what is
searched has changed (terms, titles, towns, languages, sources, work rate) a new scan starts by itself:
the results are on the Jobs page a few minutes later. Changing your skills only re-ranks; it needs no scan.
With the wizard enabled you can also **edit your profile** or **re-run the setup wizard** there.

**Calendar:** the Settings page gives an address to add to your phone's or computer's calendar
(Apple, Google, Outlook: "subscribe" / "add by URL"). It shows your interviews (enter the date and time
on the job page), ORP deadlines, follow-up dates, the hand-in of your proofs of job search on the 5th and
a summary of the week every Monday. The address contains a long random key: anyone who has it can read
those dates (job titles and companies, nothing else); **New address** makes the old one stop working.

## Stats and the ORP report

- **Stats**: applications this month vs your ORP target (`ORP_MONTHLY_TARGET`, default 10), this week,
  total, answer rate, interview rate, average days to a first answer, weekly and monthly charts (click
  a bar for that period's report), funnel, sources, how you applied.
- **ORP report**: "Preuves des recherches personnelles en vue de trouver un emploi" for a week or a
  month, with **PDF**, **CSV (Excel)** and **Print**. Each application carries the link to the posting it was for (a link in the page, the address
  under the job title in the PDF, a column in the CSV). Copy the rows into Job-Room (work.swiss) or attach
  the PDF, as your ORP/RAV office asks, by the 5th of the following month. The AVS number is left blank
  to fill in by hand.

## For people registered with an ORP / RAV

- **Monthly target:** the home page shows where you stand ("ORP target 10.2026: 4 / 10 applications · 9 days left") and
  turns into a reminder in the last ten days of the month. Until the 5th it also reminds you to hand in last month's
  proofs. Set your own target under **Settings**.
- **Official form:** on the **ORP report** of a month, *Official ORP form (PDF)* gives the unemployment-insurance form
  716.007 itself, filled in with your applications (several copies when there are more than 14). Add your AVS number,
  the date and your signature.
- **Assignments:** tick *Assigned by the ORP* on a job and give the deadline: it is listed at the top of the home page
  with the days left.
- **Spontaneous applications:** *+ spontaneous application* records a company you wrote to without a posting. It counts
  in the report and the target.

## Where you search

- **Home town and radius** (Settings): change the town or the number of kilometres and the towns and cantons to search
  are recalculated. Leave the radius at 0 to keep a list of towns you typed yourself.
- **Travel time:** each job shows the time by public transport from your home town (🚆 23 min). With a *longest travel*
  in Settings, jobs further away are greyed out.
- **Work rate:** give the range you want (for example 60 to 80 %); jobs whose title states another rate are skipped.
- **Companies you don't want:** *Never show this company* on a job page, or the list in Settings.
- **One-click fixes:** the *Why jobs were discarded* table on the Stats page offers buttons such as *skip titles with
  "industriel"*, *stop searching in Fribourg* or *never show Adecco*: one click changes the setting and clears the list.

## On a job page

- **This posting mentions:** a language that isn't in your skills, a work-permit or nationality condition, a driving
  licence, a criminal-record extract.
- **Salary:** links to the official calculators (Salarium, national wage calculator), since postings rarely state pay.
- **Posting offline:** postings are re-checked every week; one that is gone is marked *position filled* (or noted, if you
  had applied).
- **Follow-up message:** ten days after an application without an answer, the home page suggests following up and the job
  page has a short message to copy, in the posting's language.
- **Interview preparation sheet:** for a job you applied to, a one-page PDF with what the posting asks for against your
  skills, your experience to mention, usual questions and questions to ask.

## A stronger profile

- **Often asked in your jobs** (CV page): skills that the jobs found for you mention most and that are not in
  your list, with how many jobs ask for each. **+ I have it** counts it from now on, **⛔ Avoid** pushes
  those jobs down, **not relevant** stops the suggestion. Nothing is put on your CV unless your profile mentions it.
- **Profile check** (CV page): what a Swiss recruiter looks for and what is missing, with the reason: contact
  details, a job title, a summary of 3 to 5 lines, skills, dates, what you did in your last jobs, results with
  numbers, education, languages with their level, and a version of your profile in each language you search in.
- **Your profile in another language:** from the CV page, a form with your own text on the left and a box for
  the translation on the right. Nothing is machine-translated. A box left empty keeps the original; once saved,
  CVs and letters for postings in that language are written in it.
- **Documents to send** (job page): a checklist per application (CV, letter, work certificates, diplomas,
  references, permit copy, criminal-record and debt-register extracts, salary expectations, photo). The ones the
  posting names are marked; tick what is ready.

## Language of the site

English, French, German and Italian. The site follows your browser; **Settings → Language of this site** fixes it.
