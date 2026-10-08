"""Skills the person's own job market asks for that their skill list doesn't have: counted over
the postings still in play. Each one is a question, never an addition: "I have it" (it then counts
for the score), "Avoid" (jobs asking for it go down), or "not relevant" (stop suggesting it)."""
import re
from collections import Counter

from . import prefs, skills, store

_cache = {}


def missing_skills(limit=12, min_jobs=2):
    """[(skill, number of postings that mention it)], most asked first."""
    jobs = store.open_jobs()
    key = (len(jobs), jobs[0]["id"] if jobs else 0, tuple(prefs.skills()), tuple(prefs.avoided()), tuple(prefs.ignored()))
    if _cache.get("key") != key:
        counts = Counter()
        # every known skill the person doesn't have, with its pattern; a plain substring test first keeps this fast
        wanted = [(t.rstrip("*").lower(), re.compile(skills._pattern(t), re.IGNORECASE), name)
                  for t, (name, cls) in skills.plan()[2].items() if cls == "miss"]
        for j in jobs:
            text = f"{j.get('title') or ''}\n{j.get('description') or ''}".lower()
            counts.update({name for t, rx, name in wanted if t in text and rx.search(text)})
        _cache.update(key=key, counts=counts, total=len(jobs))
    skip = set(prefs.ignored())
    return [(t, n) for t, n in _cache["counts"].most_common() if n >= min_jobs and t not in skip][:limit], _cache["total"]
