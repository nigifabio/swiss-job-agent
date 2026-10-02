"""Lightweight language gate. Keeps only postings in the allowed languages.
Falls back to keeping the posting if detection isn't possible (short text,
library missing) so we never silently drop good roles."""

try:
    from langdetect import detect, DetectorFactory
    DetectorFactory.seed = 0
    _OK = True
except Exception:  # langdetect not installed
    _OK = False


def keep_language(text, allowed):
    if not _OK:
        return True
    t = (text or "").strip()
    if len(t) < 25:           # too short to classify reliably -> keep
        return True
    try:
        return detect(t) in allowed
    except Exception:
        return True


def detect_language(text):
    """Best-guess language code for text, or 'en' when undetectable."""
    if not _OK or len((text or "").strip()) < 25:
        return "en"
    try:
        return detect(text)
    except Exception:
        return "en"
