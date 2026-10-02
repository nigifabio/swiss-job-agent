"""Text from an uploaded file, parsed in a separate, resource-limited process: a malformed or
hostile PDF can't take the web app down (CPU, memory and time are capped; output is bounded).

    text = extract.text_of(filename, data)      # raises ImportError_ with a user-facing message
"""
import io
import os
import re
import sys
import subprocess
import tempfile
import zipfile

MAX_UPLOAD = 8 * 1024 * 1024          # bytes accepted from the browser
MAX_PAGES = 12
MAX_TEXT = 200_000                    # characters kept
TIMEOUT = 25                          # seconds for one extraction


class ImportError_(Exception):
    """A problem to show the user (bad type, too big, unreadable...)."""


def kind(filename, data):
    name = (filename or "").lower()
    if data[:5] == b"%PDF-":
        return "pdf"
    if data[:2] == b"PK":
        return "docx" if name.endswith(".docx") else "zip"
    if name.endswith((".txt", ".md")):
        return "txt"
    raise ImportError_("Unsupported file: upload a PDF, a Word .docx, a .txt, or the LinkedIn export .zip.")


def _docx_text(data):
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        info = z.getinfo("word/document.xml")
        if info.file_size > 20 * 1024 * 1024:
            raise ImportError_("This Word file is too large.")
        xml = z.read(info).decode("utf-8", "ignore")
    out = []
    for para in re.findall(r"<w:p[ >].*?</w:p>", xml, flags=re.S):
        para = re.sub(r"<w:tab/>", "\t", para)
        para = re.sub(r"<w:br/>", "\n", para)
        text = "".join(re.findall(r"<w:t(?: [^>]*)?>([^<]*)</w:t>", para))
        bullet = "• " if "<w:numPr>" in para else ""
        out.append(bullet + _unescape(text))
    return "\n".join(out)


def _unescape(s):
    import html
    return html.unescape(s)


def _pdf_text(path):
    import pypdf
    r = pypdf.PdfReader(path)
    if r.is_encrypted:
        try:
            r.decrypt("")
        except Exception:  # noqa: BLE001
            raise ImportError_("This PDF is password-protected.")
    pages = r.pages[:MAX_PAGES]
    return "\n".join((p.extract_text() or "") for p in pages)


def _limits():
    import resource
    resource.setrlimit(resource.RLIMIT_CPU, (TIMEOUT, TIMEOUT))
    mem = 768 * 1024 * 1024
    try:
        resource.setrlimit(resource.RLIMIT_AS, (mem, mem))
    except (ValueError, OSError):
        pass


def text_of(filename, data):
    if len(data) > MAX_UPLOAD:
        raise ImportError_(f"File too large (max {MAX_UPLOAD // (1024 * 1024)} MB).")
    k = kind(filename, data)
    if k == "txt":
        return data.decode("utf-8", "replace")[:MAX_TEXT]
    if k == "zip":
        raise ImportError_("This looks like a ZIP: use the LinkedIn export field for it.")
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "in." + k)
        with open(path, "wb") as f:
            f.write(data)
        try:
            p = subprocess.run([sys.executable, "-m", "app.importers.extract", k, path],
                               capture_output=True, timeout=TIMEOUT + 5,
                               preexec_fn=_limits if os.name == "posix" else None,
                               cwd=os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        except subprocess.TimeoutExpired:
            raise ImportError_("Reading this file took too long; try exporting it again as PDF.")
    if p.returncode == 3:
        raise ImportError_(p.stderr.decode("utf-8", "replace").strip()[:200])
    if p.returncode != 0:
        raise ImportError_("This file couldn't be read. Try another export (PDF or .docx).")
    text = p.stdout.decode("utf-8", "replace")[:MAX_TEXT]
    if len(text.strip()) < 40:
        raise ImportError_("No text found in this file (a scanned image?). Upload a text PDF or a .docx.")
    return text


def _main(argv):
    k, path = argv
    try:
        if k == "pdf":
            out = _pdf_text(path)
        else:
            with open(path, "rb") as f:
                out = _docx_text(f.read())
    except ImportError_ as e:
        sys.stderr.write(str(e))
        return 3
    sys.stdout.write(out[:MAX_TEXT])
    return 0


if __name__ == "__main__":
    sys.exit(_main(sys.argv[1:]))
