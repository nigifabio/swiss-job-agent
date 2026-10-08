"""Interface languages: English (the templates), French, German and Italian.

Templates are written in English. For another language, each template's source is rewritten when it is
loaded: every fragment listed for that template in locales.TEMPLATES (English as it stands in the file,
Jinja expressions included) is replaced by its translation. Texts that come from Python (statuses,
discard reasons, hints...) go through the `tr` filter and locales.STRINGS.
A test checks that every listed fragment still occurs in its template, so a changed English text can't
silently lose its translation.

Which language: the person's setting (UI_LANG), else the browser's Accept-Language, else English.
"""
import contextvars
import re

from jinja2 import BaseLoader, Environment, FileSystemLoader, select_autoescape

LANGS = ("en", "fr", "de", "it")
_current = contextvars.ContextVar("ui_lang", default="en")


def pick(setting="", accept_language=""):
    if setting in LANGS:
        return setting
    for part in (accept_language or "").split(","):
        code = part.split(";")[0].strip().lower()[:2]
        if code in LANGS:
            return code
    return "en"


def use(lang):
    _current.set(lang if lang in LANGS else "en")


def current():
    return _current.get()


def _pattern(fragment):
    """The fragment as a regex: any run of whitespace in it matches any run of whitespace."""
    return re.compile(r"\s+".join(re.escape(p) for p in fragment.split()))


def translate_source(source, entries, lang):
    """Template source in `lang`. entries: [(english, french, german, italian)], longest English first."""
    if lang == "en":
        return source
    idx = LANGS.index(lang)
    for entry in sorted(entries, key=lambda e: -len(e[0])):
        target = entry[idx] if len(entry) > idx else ""
        if target:                                  # no translation: the English stays
            source = _pattern(entry[0]).sub(lambda m, t=target: t, source)
    return source


def missing(source, entries):
    """English fragments that don't occur in the source (for the test)."""
    return [e[0] for e in entries if not _pattern(e[0]).search(source)]


class Loader(BaseLoader):
    def __init__(self, directory, catalog, lang):
        self.fs, self.catalog, self.lang = FileSystemLoader(directory), catalog, lang

    def get_source(self, environment, template):
        source, filename, uptodate = self.fs.get_source(environment, template)
        return translate_source(source, self.catalog.get(template, []), self.lang), filename, uptodate


def tr(text, strings=None, lang=None):
    """A Python-side text in the current language (unchanged when it has no translation)."""
    lang = lang or current()
    if lang == "en" or not isinstance(text, str):
        return text
    if strings is None:
        from .locales import STRINGS as strings
    hit = strings.get(text)
    i = LANGS.index(lang) - 1
    return (hit[i] if hit and len(hit) > i else "") or text


def environments(directory, catalog, strings=None):
    """{lang: jinja Environment} over one template folder."""
    envs = {}
    for lang in LANGS:
        env = Environment(loader=Loader(directory, catalog, lang), autoescape=select_autoescape(["html"]))
        env.filters["tr"] = lambda s, _strings=strings: tr(s, _strings)
        env.globals["ui_lang"] = lang
        envs[lang] = env
    return envs
