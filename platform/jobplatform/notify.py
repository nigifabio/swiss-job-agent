"""Tell the administrator that something needs them (an account request).

One optional channel: NOTIFY_WEBHOOK in platform/.env, a URL that takes POST {"msg": "..."} (a chat
bridge: Telegram, Matrix...). The gateway can't reach the LAN (it sits on the tenants' networks,
which are firewalled), so it hands the message to the provisioner, which posts it.
Sending happens in a background thread and never fails the request that triggered it.
"""
import os
import threading


def configured():
    return bool(os.environ.get("NOTIFY_WEBHOOK"))


def _run(prov, text):
    try:
        prov("POST", "/notify", json={"msg": text[:1500]})
    except Exception as e:  # noqa: BLE001
        print(f"[notify] failed: {type(e).__name__}: {str(e)[:160]}")


def admins(prov, subject, body):
    if configured():
        threading.Thread(target=_run, args=(prov, f"{subject}\n{body}"), daemon=True).start()
