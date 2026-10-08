import os
import re
import json
import threading

from urllib.parse import urlparse

from fastapi import FastAPI, Request, Form
from fastapi.responses import RedirectResponse, HTMLResponse, PlainTextResponse, FileResponse, Response
from fastapi.templating import Jinja2Templates

from . import auth, config, enrich, fetch, letter, onboard, places, prefs, report, roles, skills, store, tailor
from .importers import cvparse, extract, linkedin

store.init_db()

app = FastAPI(title="Swiss Job Agent", docs_url=None, redoc_url=None, openapi_url=None)
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "templates"))


SECURITY_HEADERS = {"X-Frame-Options": "DENY", "X-Content-Type-Options": "nosniff",
                    "Referrer-Policy": "same-origin", "Content-Security-Policy": "frame-ancestors 'none'; base-uri 'self'; object-src 'none'"}


def _cross_site(request):
    """A state-changing request sent by another site (CSRF), judged from Sec-Fetch-Site / Origin."""
    if request.method in ("GET", "HEAD", "OPTIONS"):
        return False
    if request.headers.get("sec-fetch-site", "same-origin") not in ("same-origin", "none"):
        return True
    origin = request.headers.get("origin")
    host = request.headers.get("x-forwarded-host") or request.headers.get("host")
    return bool(origin) and re.sub(r"^https?://", "", origin) != host


@app.middleware("http")
async def require_access(request: Request, call_next):
    if _cross_site(request):
        return PlainTextResponse("Cross-site request refused", status_code=403)
    resp = await _guarded(request, call_next)
    for k, v in SECURITY_HEADERS.items():
        resp.headers.setdefault(k, v)
    return resp


async def _guarded(request, call_next):
    if auth.ENABLED and request.url.path != "/healthz":
        token = (request.headers.get("cf-access-jwt-assertion")
                 or request.cookies.get("CF_Authorization"))
        email = auth.user_email(token)
        if not email:
            return PlainTextResponse("Forbidden", status_code=403)
        request.state.user = email
    if onboard.needed() and not request.url.path.startswith(("/onboarding", "/healthz", "/cv/role/")):
        return RedirectResponse("/onboarding", status_code=303)
    return await call_next(request)


def _safe_url(u):
    """Only keep http(s) links so a stored URL can't become a javascript: href."""
    u = (u or "").strip()
    return u if urlparse(u).scheme in ("http", "https") else ""


templates.env.filters["safe_url"] = _safe_url   # every rendered link goes through this


def render(request, name, ctx):
    ctx["user"] = getattr(request.state, "user", "")
    ctx["platform"] = config.PLATFORM_TENANT      # runs behind the platform gateway
    return templates.TemplateResponse(request, name, ctx)


@app.get("/", response_class=HTMLResponse)
def root():
    return RedirectResponse("/jobs?status=new")


@app.get("/jobs", response_class=HTMLResponse)
def jobs(request: Request, status: str = "new"):
    if status not in store.STATUSES:
        status = "new"
    meta = store.get_meta()
    return render(request, "dashboard.html", {
        "scanning": fetch.is_running(),
        "meta": meta,
        "scan_report": _json(meta.get("last_scan_report"), {}),
        "scan_warnings": _json(meta.get("last_scan_warnings"), []),
        "jobs": store.list_jobs(status),
        "status": status,
        "statuses": store.STATUSES,
        "counts": store.counts(),
        "reasons": store.DISCARD_REASONS,
        "followups": store.followups_due(14),
    })


@app.get("/job/{jid}", response_class=HTMLResponse)
def job_detail(request: Request, jid: int):
    job = store.get_job(jid)
    if not job:
        return RedirectResponse("/jobs?status=new")
    job["url"] = _safe_url(job.get("url"))
    if job["url"] and not job.get("enriched_at") and job.get("origin") != "manual":
        full = enrich.full_description(job["url"])
        if full and len(full) > len(job.get("description") or ""):
            job["description"] = full
        if enrich.looks_like_html(job.get("description")):
            job["description"] = enrich.html_to_text(job["description"])
        if full is not None:          # fetch failed -> leave unmarked, retry next view
            store.set_description(jid, job.get("description") or "")
    elif enrich.looks_like_html(job.get("description")):
        job["description"] = enrich.html_to_text(job["description"])
        store.set_description(jid, job["description"])
    desc_html, have, missing, avoided = skills.analyse(job.get("description") or "")
    return render(request, "detail.html", {
        "job": job, "statuses": store.STATUSES, "reasons": store.DISCARD_REASONS, "desc_html": desc_html, "have": have, "missing": missing,
        "avoided": avoided,
        "methods": store.APPLY_METHODS, "letter_engine": letter.config_note(), "cv_note": tailor.cv_note(),
        "can_tailor": tailor.load_profile() is not None,
        "has_cv": os.path.exists(tailor.cv_path(jid)),
    })


@app.post("/job/{jid}/cv")
def make_cv(jid: int):
    job, profile = store.get_job(jid), tailor.load_profile()
    if not job or not profile:
        return PlainTextResponse("No job or no candidate profile configured.", status_code=404)
    tailor.build(job, profile)
    return RedirectResponse(f"/job/{jid}", status_code=303)


@app.get("/job/{jid}/cv")
def get_cv(jid: int, dl: int = 0):
    job, profile, path = store.get_job(jid), tailor.load_profile(), tailor.cv_path(jid)
    if not job or not profile or not os.path.exists(path):
        return PlainTextResponse("No tailored CV for this role yet.", status_code=404)
    return FileResponse(path, media_type="application/pdf", filename=tailor.download_name(profile, job),
                        content_disposition_type="attachment" if dl else "inline")


def _json(raw, default):
    try:
        return json.loads(raw) if raw else default
    except ValueError:
        return default


def _local(path, default):
    """Only follow same-site relative redirects."""
    return path if path.startswith("/") and not path.startswith("//") else default


@app.post("/job/{jid}/status")
def set_status(jid: int, status: str = Form(...), next: str = Form("")):
    store.update_status(jid, status)
    return RedirectResponse(_local(next, f"/job/{jid}"), status_code=303)


def _quick(request, state, next, default):
    """Answer of a one-click list button: JSON when the page asked with fetch, else back to the list."""
    if request.headers.get("x-requested-with") == "fetch":
        return {"state": state, "counts": store.counts()}
    return RedirectResponse(_local(next, default), status_code=303)


@app.post("/job/{jid}/dismiss")
def dismiss(request: Request, jid: int, next: str = Form(""), reason: str = Form(""), now: str = Form("")):
    return _quick(request, store.dismiss(jid, reason, bool(now)), next, "/jobs?status=new")


@app.post("/job/{jid}/filled")
def filled(request: Request, jid: int, next: str = Form("")):
    """One click: the position is filled already (refusal if applied to, else out of the list)."""
    return _quick(request, "moved" if store.mark_filled(jid) else None, next, f"/job/{jid}")


@app.post("/job/{jid}/keep")
def keep(request: Request, jid: int, next: str = Form("")):
    store.keep(jid)
    return _quick(request, "kept", next, "/jobs?status=new")


def _start_background(fn):
    threading.Thread(target=fn, daemon=True).start()


@app.post("/skills")
def refine_skills(action: str = Form(...), term: str = Form(...), next: str = Form("/cv")):
    """A click on a skill chip: refine the CV skills / avoided words, then rescore open jobs
    so the queue re-orders now; the next scan uses the same lists."""
    if prefs.apply(action, term):
        store.rescore(fetch.score_job)
    return RedirectResponse(_local(next, "/cv"), status_code=303)


@app.post("/scan")
def scan_now():
    if not fetch.is_running():
        _start_background(fetch.run)
    return RedirectResponse("/jobs?status=new", status_code=303)


@app.post("/job/{jid}/fields")
def set_fields(
    jid: int,
    contact: str = Form(""),
    recruiter: str = Form(""),
    cv_version: str = Form(""),
    applied_date: str = Form(""),
    followup_date: str = Form(""),
    notes: str = Form(""),
    work_rate: str = Form(""),
    apply_method: str = Form("written"),
    orp_assigned: str = Form(""),
    outcome_note: str = Form(""),
):
    store.update_fields(jid, {
        "contact": contact, "recruiter": recruiter, "cv_version": cv_version,
        "applied_date": applied_date, "followup_date": followup_date, "notes": notes,
        "work_rate": work_rate, "outcome_note": outcome_note, "orp_assigned": 1 if orp_assigned else 0,
        "apply_method": apply_method if apply_method in store.APPLY_METHODS else "written",
    })
    return RedirectResponse(f"/job/{jid}", status_code=303)


# ---- cover letter ------------------------------------------------------------
@app.post("/job/{jid}/letter")
def make_letter(jid: int):
    job, profile = store.get_job(jid), tailor.load_profile()
    if not job or not profile:
        return PlainTextResponse("No job or no candidate profile configured.", status_code=404)
    text, _ = letter.write(profile, job)
    store.update_fields(jid, {"letter": text})
    return RedirectResponse(f"/job/{jid}#letter", status_code=303)


@app.post("/job/{jid}/letter/save")
def save_letter(jid: int, text: str = Form("")):
    store.update_fields(jid, {"letter": text})
    return RedirectResponse(f"/job/{jid}#letter", status_code=303)


@app.get("/job/{jid}/letter.pdf")
def letter_pdf(jid: int):
    job, profile = store.get_job(jid), tailor.load_profile()
    if not job or not profile or not job.get("letter"):
        return PlainTextResponse("No letter for this role yet.", status_code=404)
    out = letter.pdf(profile, job, job["letter"], os.path.join(tailor.CV_DIR, f"letter-{jid}.pdf"))
    name = tailor.download_name(profile, job).replace("_CV_", "_Letter_")
    return FileResponse(out, media_type="application/pdf", filename=name, content_disposition_type="attachment")


# ---- keyword CV ------------------------------------------------------------
def _cv_ctx(profile, **extra):
    targets = onboard.state().get("targets") or {}
    first = (targets.get("roles") or (roles.suggest(profile) if profile else []) or [""])[0]
    ctx = {"profile": profile, "keywords": store.get_meta().get("cv_keywords", ""),
           "built": os.path.exists(tailor.CUSTOM_CV), "prefs": prefs.summary(),
           "versions": tailor.profile_versions(),
           "roles": [{"id": r["id"], "label": roles.label(r)} for r in roles.ROLES], "role_default": first}
    ctx.update(extra)
    return ctx


@app.get("/cv", response_class=HTMLResponse)
def cv_page(request: Request):
    return render(request, "cv.html", _cv_ctx(tailor.load_profile()))


@app.post("/cv", response_class=HTMLResponse)
def cv_build(request: Request, keywords: str = Form("")):
    profile = tailor.load_profile()
    if not profile:
        return PlainTextResponse("No candidate profile configured.", status_code=404)
    store.set_meta(cv_keywords=keywords)
    words = [k for k in keywords.replace("\n", ",").split(",") if k.strip()]
    _, sup, unsup = tailor.build_custom(profile, words)
    return render(request, "cv.html", _cv_ctx(profile, keywords=keywords, built=True, supported=sup,
                                              unsupported=unsup))


@app.get("/cv/custom.pdf")
def cv_custom_pdf():
    profile = tailor.load_profile()
    if not profile or not os.path.exists(tailor.CUSTOM_CV):
        return PlainTextResponse("No CV generated yet.", status_code=404)
    name = tailor.download_name(profile, {"company": "keywords"})
    return FileResponse(tailor.CUSTOM_CV, media_type="application/pdf", filename=name,
                        content_disposition_type="inline")


# ---- stats + ORP report -------------------------------------------------------
@app.get("/stats", response_class=HTMLResponse)
def stats_page(request: Request):
    st = report.stats()
    return render(request, "stats.html", {"s": st, "discards": report.discard_stats(),
                                          "wmax": max([c for _, c in st["weeks"]] + [1]),
                                          "mmax": max([c for _, c in st["months"]] + [1])})


@app.get("/stats/discarded.csv")
def discarded_csv():
    """Every discarded posting with its reason: to keep, or to send to whoever tunes the search."""
    return Response(report.discarded_csv(), media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": 'attachment; filename="discarded-jobs.csv"'})


def _period(month, week):
    if week and not re.fullmatch(r"\d{4}-W\d{2}", week):
        week = None
    if month and not re.fullmatch(r"\d{4}-\d{2}", month):
        month = None
    return report.period(month, week)


@app.get("/report", response_class=HTMLResponse)
def report_page(request: Request, month: str = "", week: str = ""):
    kind, key, start, end, label = _period(month, week)
    profile = tailor.load_profile() or {}
    return render(request, "report.html", {
        "rows": report.rows(start, end), "cols": report.COLUMNS, "link_col": report.LINK, "label": label, "kind": kind, "key": key,
        "prev": report.shift(kind, key, -1), "next": report.shift(kind, key, 1),
        "target": report.TARGET, "name": profile.get("name", ""),
        "qs": f"{kind}={key}"})


@app.get("/report.csv")
def report_csv(month: str = "", week: str = ""):
    kind, key, start, end, _ = _period(month, week)
    return Response(report.to_csv(report.rows(start, end)), media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="recherches-{key}.csv"'})


@app.get("/report.pdf")
def report_pdf(month: str = "", week: str = ""):
    kind, key, start, end, label = _period(month, week)
    name = (tailor.load_profile() or {}).get("name", "")
    out = report.to_pdf(report.rows(start, end), label, name, os.path.join(tailor.CV_DIR, f"report-{key}.pdf"))
    return FileResponse(out, media_type="application/pdf", filename=f"recherches-emploi-{key}.pdf",
                        content_disposition_type="attachment")


@app.get("/add", response_class=HTMLResponse)
def add_form(request: Request):
    return render(request, "add.html", {"statuses": store.STATUSES})


@app.post("/add")
def add_submit(
    title: str = Form(...),
    company: str = Form(""),
    location: str = Form(""),
    url: str = Form(""),
    source: str = Form("manual"),
    status: str = Form("shortlisted"),
    description: str = Form(""),
):
    jid = store.add_manual({
        "title": title, "company": company, "location": location, "url": _safe_url(url),
        "source": source, "status": status, "description": description, "origin": "manual",
    })
    return RedirectResponse(f"/job/{jid}", status_code=303)


# ---- onboarding wizard --------------------------------------------------------------------
def _lines(text):
    return [x.strip() for x in (text or "").replace("\r", "").split("\n") if x.strip()]


def _csv_list(text):
    return [x.strip() for x in re.split(r"[,\n;]", text or "") if x.strip()]


async def _upload(form, name):
    f = form.get(name)
    if not f or not getattr(f, "filename", ""):
        return None
    data = await f.read(extract.MAX_UPLOAD + 1)
    return f.filename, data


@app.get("/onboarding", response_class=HTMLResponse)
def onboarding(request: Request):
    st = onboard.state()
    step = st["step"]
    if step == "done":
        return RedirectResponse("/jobs?status=new", status_code=303)
    ctx = {"step": step, "errors": st.pop("errors", []), "d": st["draft"] or onboard.empty_draft(),
           "sources": st.get("sources", [])}
    if st.get("errors") is not None or ctx["errors"]:
        onboard.save_state(st)
    if step == "target":
        t = st["targets"] or onboard.default_targets(st["draft"])
        fams = {}
        for r in roles.ROLES:
            fams.setdefault(FAMILY_LABELS.get(r["family"], r["family"]), []).append(
                {"id": r["id"], "label": roles.label(r)})
        ctx.update(t=t, families=list(fams.items()), towns=places.town_names(),
                   seniority=list(onboard.SENIORITY_LABELS.items()), suggested=roles.suggest(st["draft"]))
    if step == "confirm":
        ctx.update(s=st.get("settings", {}), role_cvs=st.get("role_cvs", []))
    return render(request, "onboarding.html", ctx)


FAMILY_LABELS = {"it": "IT & technology", "business": "Sales & marketing", "retail": "Retail", "services": "Office, customer & operations",
                 "finance": "Finance, legal & banking", "logistics": "Logistics & purchasing", "hospitality": "Hospitality",
                 "design": "Design", "education": "Education & training", "health": "Health care",
                 "engineering": "Engineering & technical"}


@app.post("/onboarding/import")
async def onboarding_import(request: Request):
    form = await request.form()
    st = onboard.state()
    drafts, sources, errors = [], [], []
    if not form.get("skip"):
        for field, label in (("cv", "CV"), ("linkedin_zip", "LinkedIn export"), ("linkedin_pdf", "LinkedIn PDF")):
            up = await _upload(form, field)
            if not up:
                continue
            name, data = up
            try:
                if field == "linkedin_zip":
                    drafts.append(linkedin.parse_zip(data))
                else:
                    drafts.append(cvparse.parse_any(extract.text_of(name, data)))
                sources.append(label)
            except extract.ImportError_ as e:
                errors.append(f"{label}: {e}")
            except Exception as e:  # noqa: BLE001
                errors.append(f"{label}: this file couldn't be read ({type(e).__name__}).")
        if not drafts and not errors:
            errors.append("Choose at least one file, or start from an empty profile.")
    if errors and not drafts:
        st["errors"] = errors
        onboard.save_state(st)
        return RedirectResponse("/onboarding", status_code=303)
    st.update(step="review", draft=onboard.merge(drafts) if drafts else onboard.empty_draft(),
              sources=sources, errors=errors, targets={})
    onboard.save_state(st)
    return RedirectResponse("/onboarding", status_code=303)


def _draft_from_form(form):
    langs = []
    for line in _lines(form.get("languages")):
        name, _, level = line.partition(",")
        found = cvparse._languages(name)
        code = found[0]["code"] if found else ""
        canon = found[0]["name"] if found else name.strip()
        langs.append({"name": canon, "code": code, "level": level.strip().lower()})
    exp = []
    for i in range(int(form.get("n_exp") or 0)):
        e = {k: (form.get(f"exp-{i}-{k}") or "").strip() for k in ("title", "org", "loc", "dates")}
        e["bullets"] = _lines(form.get(f"exp-{i}-bullets"))
        exp.append(e)
    return {
        "name": (form.get("name") or "").strip(), "headline": (form.get("headline") or "").strip(),
        "contact": {k: (form.get(k) or "").strip() for k in ("email", "phone", "linkedin", "location")},
        "summary": " ".join((form.get("summary") or "").split()),
        "expertise": _lines(form.get("expertise")), "experience": exp,
        "education": _lines(form.get("education")), "extras_title": (form.get("extras_title") or "").strip(),
        "extras": _lines(form.get("extras")), "skills": [x.lower() for x in _csv_list(form.get("skills"))],
        "languages": langs,
    }


@app.post("/onboarding/review")
async def onboarding_review(request: Request):
    form = await request.form()
    st = onboard.state()
    d = _draft_from_form(form)
    action = form.get("action") or "next"
    if action == "add":
        d["experience"].append({"title": "", "org": "", "loc": "", "dates": "", "bullets": []})
    elif action.startswith("del-") and action[4:].isdigit():
        i = int(action[4:])
        if i < len(d["experience"]):
            d["experience"].pop(i)
    st["draft"] = d
    if action == "back":
        st["step"] = "import"
    elif action == "next":
        if not d["name"]:
            st["errors"] = ["Your name is needed for the CV."]
        elif st.get("editing"):             # "Edit my profile": save it, keep the search as is
            onboard.save_profile(d)
            st.update(step="done", editing=False)
            onboard.save_state(st)
            return RedirectResponse("/cv", status_code=303)
        else:
            st["step"] = "target"
    onboard.save_state(st)
    return RedirectResponse("/onboarding" + ("#experience" if action in ("add",) else ""), status_code=303)


@app.post("/onboarding/target")
async def onboarding_target(request: Request):
    form = await request.form()
    st = onboard.state()
    t = {"roles": [r for r in form.getlist("roles") if roles.get(r)][:5],
         "extra_titles": _csv_list(form.get("extra_titles"))[:10],
         "seniority": form.get("seniority") if form.get("seniority") in onboard.SENIORITY else "mid",
         "home": (form.get("home") or "").strip()[:60],
         "radius": int(form.get("radius") or 30) if str(form.get("radius") or "30").isdigit() else 30,
         "whole_country": bool(form.get("whole_country")), "remote": bool(form.get("remote")),
         "langs": [x for x in form.getlist("langs") if x in onboard.POSTING_LANGS],
         "avoid": _csv_list(form.get("avoid"))[:20]}
    st["targets"] = t
    if form.get("action") == "back":
        st["step"] = "review"
    elif not t["roles"] and not t["extra_titles"]:
        st["errors"] = ["Pick at least one role, or type a job title."]
    elif not t["langs"]:
        st["errors"] = ["Pick at least one posting language."]
    else:
        st["settings"] = onboard.settings_for(st["draft"], t)
        profile = onboard.profile_from_draft(st["draft"])
        cvs = []
        for rid in t["roles"]:
            _, sup, miss = onboard.build_role_cv(profile, rid)
            cvs.append({"id": rid, "label": roles.label(roles.get(rid)), "missing": miss})
        st["role_cvs"] = cvs
        st["step"] = "confirm"
    onboard.save_state(st)
    return RedirectResponse("/onboarding", status_code=303)


@app.post("/onboarding/back")
def onboarding_back():
    st = onboard.state()
    st["step"] = "target"
    onboard.save_state(st)
    return RedirectResponse("/onboarding", status_code=303)


def _settings_from_form(form):
    out = {}
    for k, kind in config.EDITABLE.items():
        if kind == "bool":
            out[k] = bool(form.get(k))
        elif kind == "hours":
            try:
                out[k] = float(form.get(k) or 12)
            except ValueError:
                out[k] = 12
        elif form.get(k) is not None:
            out[k] = [x.strip() for line in _lines(form.get(k)) for x in line.split(",") if x.strip()]
    return out


@app.post("/onboarding/finish")
async def onboarding_finish(request: Request):
    form = await request.form()
    st = onboard.state()
    if st["step"] != "confirm":
        return RedirectResponse("/onboarding", status_code=303)
    onboard.finish(st["draft"], st["targets"], _settings_from_form(form))
    st["step"] = "done"
    onboard.save_state(st)
    if not fetch.is_running():
        _start_background(fetch.run)
    return RedirectResponse("/jobs?status=new", status_code=303)


@app.post("/onboarding/edit")
def onboarding_edit():
    profile = tailor.load_profile()
    st = onboard.state()
    if profile:
        st.update(step="review", draft=onboard.from_profile(profile), editing=True, sources=[])
    else:
        st.update(step="import")
    onboard.save_state(st)
    return RedirectResponse("/onboarding", status_code=303)


@app.post("/onboarding/restart")
def onboarding_restart():
    st = onboard.state()
    st.update(step="import", editing=False, sources=[])
    onboard.save_state(st)
    return RedirectResponse("/onboarding", status_code=303)


# ---- settings -------------------------------------------------------------------------------
def _current_settings():
    return {k: getattr(config, k) for k in config.EDITABLE}


@app.get("/settings", response_class=HTMLResponse)
def settings_page(request: Request, saved: int = 0):
    return render(request, "settings.html", {"s": _current_settings(), "saved": saved, "rescored": saved})


@app.post("/settings")
async def settings_save(request: Request):
    config.save_settings(_settings_from_form(await request.form()))
    prefs.invalidate()
    store.rescore(fetch.score_job)
    return RedirectResponse("/settings?saved=1", status_code=303)


# ---- CV for a target role -----------------------------------------------------------------
@app.post("/cv/role")
def cv_role(request: Request, role: str = Form(...)):
    profile = tailor.load_profile()
    if not profile or not roles.get(role):
        return RedirectResponse("/cv", status_code=303)
    _, sup, miss = onboard.build_role_cv(profile, role)
    return render(request, "cv.html", _cv_ctx(profile, role_built={"id": role, "label": roles.label(roles.get(role)),
                                                                   "supported": sup, "missing": miss}))


@app.get("/cv/role/{rid}.pdf")
def cv_role_pdf(rid: str):
    path = onboard.role_cv_path(rid)
    if not roles.get(rid) or not os.path.exists(path):
        return PlainTextResponse("No CV for this role yet.", status_code=404)
    profile = tailor.load_profile() or onboard.profile_from_draft(onboard.state()["draft"])
    name = tailor.download_name(profile, {"company": rid})
    return FileResponse(path, media_type="application/pdf", filename=name, content_disposition_type="inline")


@app.get("/healthz")
def healthz():
    return {"ok": True}
