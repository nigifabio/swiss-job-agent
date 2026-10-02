"""Full posting text on demand. Search results only carry a snippet; job pages on
jobs.ch/jobup.ch (and most boards) embed the whole ad as schema.org JobPosting JSON-LD."""
import re
import json
import html

import httpx

_LD = re.compile(r'<script[^>]*application/ld\+json[^>]*>(.*?)</script>', re.S | re.I)
_BLOCK = re.compile(r"</?(p|br|li|ul|ol|h[1-6]|div|tr)[^>]*>", re.I)
_TAG = re.compile(r"<[^>]+>")
HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                         "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"}


def html_to_text(h):
    """HTML (even entity-escaped HTML, as Greenhouse sends it) -> plain text with paragraph breaks."""
    t = html.unescape(h or "") if "&lt;" in (h or "") else (h or "")
    t = _BLOCK.sub("\n", t)
    t = html.unescape(_TAG.sub("", t))
    t = re.sub(r"[ \t\xa0]+", " ", t)
    return re.sub(r"\n\s*\n+", "\n\n", t).strip()


def _postings(data):
    for x in data if isinstance(data, list) else [data]:
        if isinstance(x, dict):
            if x.get("@type") == "JobPosting":
                yield x
            yield from _postings(x.get("@graph", []))


def full_description(url):
    """The posting's full text from its page; "" if the page has none (don't retry);
    None if the page couldn't be fetched (retry on a later view)."""
    try:
        r = httpx.get(url, headers=HEADERS, timeout=10, follow_redirects=True)
        r.raise_for_status()
    except Exception:  # noqa: BLE001
        return None
    for m in _LD.finditer(r.text):
        try:
            data = json.loads(m.group(1))
        except ValueError:
            continue
        for p in _postings(data):
            text = html_to_text(p.get("description", ""))
            if text:
                return text
    return ""


def looks_like_html(text):
    return bool(text) and bool(_TAG.search(text) or "&lt;" in text)
