"""Job-alert emails (LinkedIn, Indeed, jobs.ch/jobup.ch, Job-Room, Glassdoor) read from a
dedicated mailbox over IMAP. Covers LinkedIn and Indeed without scraping them: the person
subscribes to job alerts sent to that mailbox, and each scan picks up the job links.

Settings (set with deploy/set-env.sh; silent until IMAP_HOST is set):
  IMAP_HOST, IMAP_USER, IMAP_PASSWORD (an app password), IMAP_FOLDER (INBOX), IMAP_DAYS (14)

The mailbox is opened READ-ONLY: messages are never marked read, moved or deleted.
Extraction is generic (job-link patterns + the link's text as title, the next text lines as
company and location), because alert layouts change; tune PATTERNS on real alerts.
"""
import os
import re
import email
import imaplib
import datetime
from email.header import decode_header, make_header
from html.parser import HTMLParser

from .. import filters, scanlog
from ..normalize import content_hash

PATTERNS = [   # (source, regex on the href, canonical URL built from the match)
    ("linkedin", re.compile(r"linkedin\.com/(?:comm/)?jobs/view/(?:[\w-]*?-)?(\d{6,})"),
     "https://www.linkedin.com/jobs/view/{}/"),
    ("indeed", re.compile(r"indeed\.\w+(?:\.\w+)?/(?:rc/clk|viewjob|pagead/clk|m/viewjob)[^\"'\s>]*?[?&]jk=([0-9a-f]{8,})"),
     "https://ch.indeed.com/viewjob?jk={}"),
    ("jobs.ch", re.compile(r"(https?://www\.(?:jobs|jobup)\.ch/[a-z]{2}/[\w-]+/detail/[\w-]+/?)"), "{}"),
    ("job-room", re.compile(r"(https?://www\.job-room\.ch/job-search/[\w-]+)"), "{}"),
    ("glassdoor", re.compile(r"(https?://www\.glassdoor\.\w+(?:\.\w+)?/job-listing/[^\"'\s>?]+)"), "{}"),
]
GENERIC = {"view job", "apply", "apply now", "see job", "voir l'offre", "postuler", "view", "more jobs",
           "see all jobs", "voir toutes les offres", "jetzt bewerben", "stelle ansehen", "candidati"}


class _Links(HTMLParser):
    """Sequence of ('a', href, text) and ('t', text) in reading order."""
    def __init__(self):
        super().__init__()
        self.items, self._href, self._buf = [], None, []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self._flush()
            self._href = dict(attrs).get("href") or ""

    def handle_endtag(self, tag):
        if tag == "a" and self._href is not None:
            self.items.append(("a", self._href, " ".join("".join(self._buf).split())))
            self._href, self._buf = None, []
        elif tag in ("p", "div", "td", "tr", "br", "li", "table"):
            self._flush()

    def handle_data(self, data):
        self._buf.append(data)

    def _flush(self):
        if self._href is None:
            text = " ".join("".join(self._buf).split())
            if text:
                self.items.append(("t", text))
            self._buf = []


def jobs_from_html(html):
    """[(source, url, title, company, location)] found in one alert email's HTML."""
    p = _Links()
    p.feed(html or "")
    p._flush()
    items, out, seen = p.items, [], set()
    for i, it in enumerate(items):
        if it[0] != "a":
            continue
        _, href, text = it
        for source, rx, canon in PATTERNS:
            m = rx.search(href)
            if not m:
                continue
            url = canon.format(m.group(1))
            if url in seen or len(text) < 4 or text.lower() in GENERIC:
                break
            seen.add(url)
            after = [x[1] for x in items[i + 1:i + 4] if x[0] == "t" and x[1].lower() not in GENERIC]
            out.append((source, url, text, after[0] if after else "", after[1] if len(after) > 1 else ""))
            break
    return out


def _html_parts(msg):
    for part in msg.walk():
        if part.get_content_type() == "text/html":
            payload = part.get_payload(decode=True) or b""
            yield payload.decode(part.get_content_charset() or "utf-8", errors="replace")


def fetch():
    host = os.environ.get("IMAP_HOST", "")
    if not host:
        return []
    days = int(os.environ.get("IMAP_DAYS", "14"))
    since = (datetime.date.today() - datetime.timedelta(days=days)).strftime("%d-%b-%Y")
    out, seen = [], set()
    try:
        imap = imaplib.IMAP4_SSL(host, timeout=30)
        imap.login(os.environ.get("IMAP_USER", ""), os.environ.get("IMAP_PASSWORD", ""))
        imap.select(os.environ.get("IMAP_FOLDER", "INBOX"), readonly=True)
        _, ids = imap.search(None, "SINCE", since)
        for num in (ids[0].split() if ids and ids[0] else []):
            _, data = imap.fetch(num, "(BODY.PEEK[])")          # PEEK: never sets \\Seen
            msg = email.message_from_bytes(data[0][1])
            for html in _html_parts(msg):
                for source, url, title, company, loc in jobs_from_html(html):
                    title = filters.strip_html(title)
                    h = content_hash(title, company, loc)
                    if h in seen or not filters.title_ok(title) or not filters.language_ok(title, ""):
                        continue
                    seen.add(h)
                    out.append({"source": f"email:{source}", "title": title, "company": company,
                                "location": loc, "description": "", "url": url, "salary": "",
                                "posted_at": str(make_header(decode_header(msg.get("Date", "")))),
                                "content_hash": h})
        imap.logout()
    except (imaplib.IMAP4.error, OSError) as e:
        scanlog.error("email alerts", f"{type(e).__name__}: {str(e)[:120]}")   # never the password
    scanlog.count("email alerts", len(out))
    return out
