"""MIFTAH Xray Manager agent.

Runs on the Xray server (separate from the control plane). Exposes a small
token-protected API used by the MIFTAH backend to validate/apply configs and
synchronise users. It never accepts arbitrary shell commands.
"""
import hmac
import json
import os
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone

from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel

AGENT_TOKEN = os.environ.get("AGENT_TOKEN", "")
XRAY_BIN = os.environ.get("XRAY_BIN", "/usr/local/bin/xray")
XRAY_CONFIG = os.environ.get("XRAY_CONFIG", "/usr/local/etc/xray/config.json")
XRAY_SERVICE = os.environ.get("XRAY_SERVICE", "xray")
BACKUP_DIR = os.environ.get("BACKUP_DIR", "/usr/local/etc/xray/backups")

app = FastAPI(title="MIFTAH Xray Agent", version="1.0.0")


def auth(x_agent_token: str | None = Header(default=None)) -> None:
    if not AGENT_TOKEN:
        raise HTTPException(status_code=500, detail="AGENT_TOKEN not configured")
    if not x_agent_token or not hmac.compare_digest(x_agent_token, AGENT_TOKEN):
        raise HTTPException(status_code=401, detail="unauthorized")


def _run(cmd: list[str], timeout: int = 20) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


def _xray_version() -> str | None:
    try:
        p = _run([XRAY_BIN, "version"])
        if p.returncode == 0:
            return p.stdout.splitlines()[0].strip()
    except (OSError, subprocess.SubprocessError):
        return None
    return None


def _service_state() -> str:
    try:
        p = _run(["systemctl", "is-active", XRAY_SERVICE])
        return p.stdout.strip() or "unknown"
    except (OSError, subprocess.SubprocessError):
        return "unknown"


def _validate(config: dict) -> tuple[bool, str | None]:
    fd, path = tempfile.mkstemp(suffix=".json")
    try:
        with os.fdopen(fd, "w") as fh:
            json.dump(config, fh)
        p = _run([XRAY_BIN, "run", "-test", "-c", path])
        if p.returncode != 0:
            return False, (p.stderr or p.stdout or "xray test failed").strip()[-1000:]
        return True, None
    except (OSError, subprocess.SubprocessError) as exc:
        return False, str(exc)
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass


def _write_config(config: dict) -> None:
    os.makedirs(os.path.dirname(XRAY_CONFIG), exist_ok=True)
    os.makedirs(BACKUP_DIR, exist_ok=True)
    if os.path.exists(XRAY_CONFIG):
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        shutil.copy2(XRAY_CONFIG, os.path.join(BACKUP_DIR, f"config-{stamp}.json"))
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(XRAY_CONFIG), suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as fh:
            json.dump(config, fh, indent=2)
        os.chmod(tmp, 0o600)
        os.replace(tmp, XRAY_CONFIG)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def _restart() -> str:
    try:
        p = _run(["systemctl", "restart", XRAY_SERVICE], timeout=30)
        if p.returncode != 0:
            raise HTTPException(
                status_code=500,
                detail=(p.stderr or p.stdout or "restart failed").strip()[:500],
            )
    except (OSError, subprocess.SubprocessError) as exc:
        raise HTTPException(status_code=500, detail=f"restart failed: {exc}")
    return _service_state()


class ConfigIn(BaseModel):
    config: dict


class User(BaseModel):
    id: str
    email: str | None = None
    enabled: bool = True


class UsersIn(BaseModel):
    users: list[User]


@app.get("/health", dependencies=[Depends(auth)])
def health():
    return {
        "status": "ok",
        "xray_version": _xray_version(),
        "service": _service_state(),
        "time": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/status", dependencies=[Depends(auth)])
def status():
    cfg_ok = None
    if os.path.exists(XRAY_CONFIG):
        try:
            with open(XRAY_CONFIG) as fh:
                cfg_ok, err = _validate(json.load(fh))
        except (OSError, json.JSONDecodeError):
            cfg_ok = False
    return {
        "service": _service_state(),
        "xray_version": _xray_version(),
        "config_path": XRAY_CONFIG,
        "config_exists": os.path.exists(XRAY_CONFIG),
        "config_valid": cfg_ok,
    }


@app.post("/config/validate", dependencies=[Depends(auth)])
def validate(body: ConfigIn):
    ok, err = _validate(body.config)
    return {"valid": ok, "error": err}


@app.post("/config/apply", dependencies=[Depends(auth)])
def apply_config(body: ConfigIn):
    ok, err = _validate(body.config)
    if not ok:
        raise HTTPException(status_code=422, detail=err)
    _write_config(body.config)
    state = _restart()
    return {"applied": True, "service": state, "time": datetime.now(timezone.utc).isoformat()}


@app.post("/users/sync", dependencies=[Depends(auth)])
def sync_users(body: UsersIn):
    if not os.path.exists(XRAY_CONFIG):
        raise HTTPException(status_code=400, detail="no config on server")
    try:
        with open(XRAY_CONFIG) as fh:
            cfg = json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=500, detail=f"cannot read config: {exc}")

    clients = []
    for u in body.users:
        if not u.enabled:
            continue
        clients.append({"id": u.id, "email": u.email or u.id, "flow": ""})

    updated = 0
    for inbound in cfg.get("inbounds", []):
        proto = inbound.get("protocol")
        if proto in ("vless", "vmess", "trojan"):
            settings = inbound.setdefault("settings", {})
            if proto == "trojan":
                settings["clients"] = [
                    {"password": c["id"], "email": c["email"]} for c in clients
                ]
            else:
                settings["clients"] = clients
            updated += 1
    if not updated:
        raise HTTPException(status_code=422, detail="no vless/vmess/trojan inbound found")

    ok, err = _validate(cfg)
    if not ok:
        raise HTTPException(status_code=422, detail=err)
    _write_config(cfg)
    state = _restart()
    return {"synced": len(clients), "inbounds": updated, "service": state}


@app.post("/service/restart", dependencies=[Depends(auth)])
def restart():
    return {"service": _restart()}
