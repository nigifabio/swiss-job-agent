"""Provisioner: the only service holding the Docker socket.

Each tenant = volume jat-<slug>-data + bridge network jat-<slug> (its own subnet, no route to
other tenants) + two containers from the tenant image:
  jat-<slug>-web    the app (the gateway joins the tenant network to reach it)
  jat-<slug>-sched  the scan scheduler
both non-root, read-only root filesystem, no capabilities, no-new-privileges, memory / CPU /
process caps. Egress to the LAN is blocked on the host (platform/egress.sh).

HTTP API (bearer PROVISIONER_TOKEN), used by the gateway:
  GET    /tenants                       list with container state
  PUT    /tenants/{slug}   {email}      create or re-create (idempotent)
  POST   /tenants/{slug}/stop|start
  GET    /tenants/{slug}/export         tar.gz of the tenant's data
  DELETE /tenants/{slug}                archive the data, then remove everything
  POST   /sync                          re-attach the gateway to every tenant network
CLI (on the host: docker compose exec provisioner python -m jobplatform.provisioner ...):
  list | sync | upgrade [slug...]       upgrade = re-create on the current image, one at a
                                          time, health-checked, rolled back on failure
"""
import datetime
import gzip
import hmac
import io
import ipaddress
import json
import os
import re
import sys
import time

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

SLUG = re.compile(r"^[a-z0-9][a-z0-9-]{1,30}[a-z0-9]$")
EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
LABEL = "jobagent.tenant"
PREFIX = "jat-"


def env(name, default=""):
    return os.environ.get(name, default)


class Settings:
    def __init__(self):
        self.image = env("TENANT_IMAGE", "swiss-job-agent:latest")
        self.token = env("PROVISIONER_TOKEN")
        self.gateway = env("GATEWAY_CONTAINER", "jobplatform-gateway")
        self.subnet_pool = ipaddress.ip_network(env("TENANT_SUBNET_POOL", "172.31.0.0/16"))
        self.web_mem = env("TENANT_WEB_MEMORY", "512m")
        self.sched_mem = env("TENANT_SCHED_MEMORY", "512m")
        self.cpus = float(env("TENANT_CPUS", "0.5"))
        self.archives = env("ARCHIVE_DIR", "/archives")
        # Platform-wide settings passed to every tenant (keys, access check). Per-tenant ones
        # (ALLOWED_EMAILS) are added at creation.
        self.passthrough = {k: env(k) for k in (
            "CF_TEAM_DOMAIN", "CF_ACCESS_AUD", "ADZUNA_APP_ID", "ADZUNA_APP_KEY", "CAREERJET_API_KEY",
            "JOOBLE_API_KEY", "JOBCLOUD_SITES") if env(k)}


S = Settings()


def docker_client():
    import docker
    return docker.from_env(timeout=120)


def check_slug(slug):
    if not SLUG.match(slug or ""):
        raise HTTPException(400, "bad tenant id")
    return slug


def names(slug):
    return {"web": f"{PREFIX}{slug}-web", "sched": f"{PREFIX}{slug}-sched",
            "net": f"{PREFIX}{slug}", "vol": f"{PREFIX}{slug}-data"}


# ---- docker operations (d = docker client) ---------------------------------------------
def _get(coll, name):
    import docker.errors
    try:
        return coll.get(name)
    except docker.errors.NotFound:
        return None


def free_subnet(d):
    """The first /28 of the pool no tenant network uses (16 addresses: plenty for 3 containers)."""
    used = set()
    for n in d.networks.list(filters={"label": LABEL}):
        for cfg in (n.attrs.get("IPAM") or {}).get("Config") or []:
            if cfg.get("Subnet"):
                used.add(ipaddress.ip_network(cfg["Subnet"]))
    for sub in S.subnet_pool.subnets(new_prefix=28):
        if not any(sub.overlaps(u) for u in used):
            return sub
    raise HTTPException(507, "no free tenant subnet left")


def ensure_network(d, slug):
    import docker.types
    n = names(slug)
    net = _get(d.networks, n["net"])
    if net:
        return net
    sub = free_subnet(d)
    ipam = docker.types.IPAMConfig(pool_configs=[docker.types.IPAMPool(subnet=str(sub), gateway=str(sub[1]))])
    return d.networks.create(n["net"], driver="bridge", ipam=ipam, labels={LABEL: slug},
                             options={"com.docker.network.bridge.enable_icc": "true"})


def ensure_volume(d, slug, image):
    n = names(slug)
    vol = _get(d.volumes, n["vol"])
    if vol is None:
        vol = d.volumes.create(n["vol"], labels={LABEL: slug})
    # a new volume is root-owned: hand it to the app user (one-shot, network-less)
    d.containers.run(image, ["sh", "-c", "chown 1000:1000 /data && chmod 700 /data"], user="0",
                     volumes={n["vol"]: {"bind": "/data", "mode": "rw"}}, network_mode="none",
                     remove=True, cap_drop=["ALL"], cap_add=["CHOWN", "FOWNER", "DAC_OVERRIDE"])
    return vol


def spec(slug, email, role, image, extra=()):
    """The fixed, locked-down container spec. Nothing here comes from the tenant.
    extra: more sign-in addresses of the same person (the owner's Gmail next to their Hotmail...)."""
    import docker.types
    n = names(slug)
    extra = [e for e in extra if e and e != email]
    environment = dict(S.passthrough, DB_PATH="/data/jobs.db", ONBOARDING="1", PLATFORM_TENANT="1",
                       ALLOWED_EMAILS=",".join([email] + extra),
                       HOME="/tmp", PYTHONDONTWRITEBYTECODE="1", PROVIDERS="")
    common = dict(
        image=image, detach=True, environment=environment, user="1000:1000",
        volumes={n["vol"]: {"bind": "/data", "mode": "rw"}}, network=n["net"],
        read_only=True, tmpfs={"/tmp": "size=128m,mode=1777"}, cap_drop=["ALL"],
        security_opt=["no-new-privileges:true"], pids_limit=128, nano_cpus=int(S.cpus * 1e9),
        restart_policy={"Name": "unless-stopped"},
        labels={LABEL: slug, "jobagent.role": role, "jobagent.email": email, "jobagent.extra_emails": ",".join(extra)},
        log_config=docker.types.LogConfig(type="json-file", config={"max-size": "5m", "max-file": "2"}),
    )
    if role == "web":
        return dict(common, name=n["web"], mem_limit=S.web_mem, hostname=n["web"])
    return dict(common, name=n["sched"], mem_limit=S.sched_mem, command=["python", "-m", "app.scheduler"],
                healthcheck={"test": ["NONE"]})


def _remove(d, name):
    c = _get(d.containers, name)
    if c:
        c.remove(force=True)


def attach_gateway(d, slug):
    net = _get(d.networks, names(slug)["net"])
    gw = _get(d.containers, S.gateway)
    if not net or not gw:
        return False
    net.reload()
    if gw.id not in (net.attrs.get("Containers") or {}):
        try:
            net.connect(gw)
        except Exception as e:  # noqa: BLE001  (already connected)
            if "already exists" not in str(e):
                raise
    return True


def healthy(d, name, timeout=90):
    """Wait for the image healthcheck (web) to report healthy."""
    end = time.time() + timeout
    while time.time() < end:
        c = _get(d.containers, name)
        if c is None:
            return False
        c.reload()
        st = (c.attrs.get("State") or {})
        if st.get("Status") in ("exited", "dead"):
            return False
        if (st.get("Health") or {}).get("Status") == "healthy":
            return True
        time.sleep(2)
    return False


def create(d, slug, email, image=None, extra=None):
    """Create or re-create a tenant (data is kept: it lives in the volume).
    extra=None keeps the extra sign-in addresses the tenant already has (upgrades, rollbacks)."""
    image = image or S.image
    ensure_network(d, slug)
    ensure_volume(d, slug, image)
    n = names(slug)
    if extra is None:
        old = _get(d.containers, n["web"])
        extra = [e for e in ((old.labels.get("jobagent.extra_emails") if old else "") or "").split(",") if e]
    for role in ("web", "sched"):
        _remove(d, n[role])
        d.containers.run(**spec(slug, email, role, image, extra))
    attach_gateway(d, slug)
    return status(d, slug)


def image_id(c):
    """The image a container runs, from the container itself: Docker may no longer list that image
    (a rebuild moved the tag and the old one was collected), which must not break listing or upgrades."""
    return (c.attrs.get("Image") or "") if c is not None else ""


def image_name(c):
    try:
        return (c.image.tags or [c.image.short_id])[0]
    except Exception:  # noqa: BLE001  (image gone from the store; the container still runs)
        return image_id(c).split(":")[-1][:12] or "?"


def tenants(d):
    out = {}
    for c in d.containers.list(all=True, filters={"label": LABEL}):
        slug, role = c.labels.get(LABEL), c.labels.get("jobagent.role")
        t = out.setdefault(slug, {"slug": slug, "email": c.labels.get("jobagent.email", ""), "web": "missing",
                                  "sched": "missing"})
        state = c.attrs.get("State") or {}
        health = (state.get("Health") or {}).get("Status")
        t[role] = state.get("Status", c.status) + (f" ({health})" if health else "")
        if role == "web":
            t["image"] = image_name(c)
    for v in d.volumes.list(filters={"label": LABEL}):
        slug = v.attrs.get("Labels", {}).get(LABEL)
        out.setdefault(slug, {"slug": slug, "email": "", "web": "missing", "sched": "missing"})
    return sorted(out.values(), key=lambda t: t["slug"] or "")


def status(d, slug):
    return next((t for t in tenants(d) if t["slug"] == slug), None)


def set_running(d, slug, run):
    n = names(slug)
    for role in ("web", "sched"):
        c = _get(d.containers, n[role])
        if c is None:
            raise HTTPException(404, "no such tenant")
        c.start() if run else c.stop(timeout=20)
    return status(d, slug)


def export(d, slug):
    """tar.gz bytes of the tenant's /data, read through a throw-away network-less container."""
    n = names(slug)
    if _get(d.volumes, n["vol"]) is None:
        raise HTTPException(404, "no such tenant")
    c = d.containers.create(S.image, ["true"], user="1000:1000", network_mode="none",
                            volumes={n["vol"]: {"bind": "/data", "mode": "ro"}})
    try:
        stream, _ = c.get_archive("/data")
        raw = b"".join(stream)
    finally:
        c.remove(force=True)
    return gzip.compress(raw)


def delete(d, slug):
    """Archive the data to ARCHIVE_DIR, then remove containers, network and volume."""
    n = names(slug)
    archive = None
    if _get(d.volumes, n["vol"]) is not None:
        os.makedirs(S.archives, exist_ok=True)
        stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        archive = os.path.join(S.archives, f"{slug}-{stamp}.tar.gz")
        with open(archive, "wb") as f:
            f.write(export(d, slug))
        os.chmod(archive, 0o600)
    for role in ("web", "sched"):
        _remove(d, n[role])
    net = _get(d.networks, n["net"])
    if net:
        gw = _get(d.containers, S.gateway)
        if gw:
            try:
                net.disconnect(gw, force=True)
            except Exception:  # noqa: BLE001
                pass
        net.remove()
    vol = _get(d.volumes, n["vol"])
    if vol:
        vol.remove(force=True)
    return {"slug": slug, "archive": archive}


def prune_archives(days=None):
    """Delete-archives are kept ARCHIVE_DAYS (default 30), then removed."""
    days = int(env("ARCHIVE_DAYS", "30")) if days is None else days
    if not os.path.isdir(S.archives):
        return []
    cutoff, gone = time.time() - days * 86400, []
    for f in os.listdir(S.archives):
        p = os.path.join(S.archives, f)
        if f.endswith(".tar.gz") and os.path.getmtime(p) < cutoff:
            os.remove(p)
            gone.append(f)
    return gone


def sync(d):
    prune_archives()
    return {t["slug"]: attach_gateway(d, t["slug"]) for t in tenants(d) if t["slug"]}


def upgrade(d, slugs=None, log=print):
    """Re-create tenants on the current image, one at a time; roll back one that doesn't come up
    healthy and stop there. Returns True if all went well."""
    target = d.images.get(S.image)
    for t in tenants(d):
        if slugs and t["slug"] not in slugs:
            continue
        if t["web"] == "missing" or t["web"].startswith("exited"):
            log(f"{t['slug']}: not running, skipped")
            continue
        web = _get(d.containers, names(t["slug"])["web"])
        prev = image_id(web)
        if prev == target.id:
            log(f"{t['slug']}: already on {S.image}")
            continue
        create(d, t["slug"], t["email"], target.id)
        if healthy(d, names(t["slug"])["web"]):
            log(f"{t['slug']}: upgraded")
            continue
        log(f"{t['slug']}: UNHEALTHY on the new image, rolling back")
        try:
            create(d, t["slug"], t["email"], prev)
            log(f"{t['slug']}: " + ("rolled back" if healthy(d, names(t["slug"])["web"]) else "ROLLBACK UNHEALTHY"))
        except Exception as e:  # noqa: BLE001  (the previous image is gone: nothing to go back to)
            log(f"{t['slug']}: CAN'T ROLL BACK ({type(e).__name__}); data is intact in its volume")
        return False
    return True


# ---- HTTP API --------------------------------------------------------------------------------
app = FastAPI(title="jobplatform provisioner", docs_url=None, redoc_url=None, openapi_url=None)
_client = None


def client():
    global _client
    if _client is None:
        _client = docker_client()
    return _client


def auth(authorization: str = Header("")):
    if not S.token or not hmac.compare_digest(authorization.encode(), f"Bearer {S.token}".encode()):
        raise HTTPException(401, "unauthorized")


class NewTenant(BaseModel):
    email: str
    extra_emails: list[str] | None = None      # None: keep the ones the tenant has


@app.get("/healthz")
def healthz():
    return {"ok": True}


@app.get("/tenants", dependencies=[Depends(auth)])
def api_list():
    return tenants(client())


@app.put("/tenants/{slug}", dependencies=[Depends(auth)])
def api_create(slug: str, body: NewTenant):
    extra = None if body.extra_emails is None else [e.lower() for e in body.extra_emails]
    if not EMAIL.match(body.email) or len(extra or []) > 5 or not all(EMAIL.match(e) and "," not in e for e in extra or []):
        raise HTTPException(400, "bad email")
    return create(client(), check_slug(slug), body.email.lower(), extra=extra)


@app.post("/tenants/{slug}/{action}", dependencies=[Depends(auth)])
def api_action(slug: str, action: str):
    if action not in ("stop", "start"):
        raise HTTPException(404, "unknown action")
    return set_running(client(), check_slug(slug), action == "start")


@app.get("/tenants/{slug}/export", dependencies=[Depends(auth)])
def api_export(slug: str):
    data = export(client(), check_slug(slug))
    return StreamingResponse(io.BytesIO(data), media_type="application/gzip")


@app.delete("/tenants/{slug}", dependencies=[Depends(auth)])
def api_delete(slug: str):
    return delete(client(), check_slug(slug))


class Notice(BaseModel):
    msg: str


@app.post("/notify", dependencies=[Depends(auth)])
def api_notify(body: Notice):
    """Pass a short admin notice to the chat bridge (NOTIFY_WEBHOOK). The gateway can't reach the LAN itself."""
    url = env("NOTIFY_WEBHOOK")
    if not url:
        return {"sent": False}
    import httpx
    httpx.post(url, json={"msg": body.msg[:1500]}, timeout=10).raise_for_status()
    return {"sent": True}


@app.post("/sync", dependencies=[Depends(auth)])
def api_sync():
    return sync(client())


def main(argv):
    cmd, rest = (argv[0] if argv else "list"), argv[1:]
    d = client()
    if cmd == "list":
        print(json.dumps(tenants(d), indent=1))
    elif cmd == "sync":
        print(json.dumps(sync(d)))
    elif cmd == "upgrade":
        ok = upgrade(d, rest or None)
        sync(d)
        return 0 if ok else 1
    else:
        print(__doc__)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
