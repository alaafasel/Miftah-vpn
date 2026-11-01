import json
import os
import subprocess
import tempfile

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..audit import write_audit
from ..auth import get_current_admin
from ..config import settings
from ..db import get_db
from ..models import AdminUser, ConfigVersion, XrayConfig

router = APIRouter(prefix="/api/v1/admin/config", tags=["admin-config"])

CONFIG_NAME = "default"
MAX_BYTES = 512 * 1024


class ConfigIn(BaseModel):
    config: dict


class PublishIn(BaseModel):
    note: str | None = None


def _ip(request: Request) -> str | None:
    return request.client.host if request.client else None


def _get_cfg(db: Session) -> XrayConfig:
    cfg = db.scalar(select(XrayConfig).where(XrayConfig.name == CONFIG_NAME))
    if cfg is None:
        cfg = XrayConfig(name=CONFIG_NAME, draft={})
        db.add(cfg)
        db.flush()
    return cfg


def _proxyfb_check(outs: list) -> tuple[list[str], list[str]]:
    px = [o for o in outs if isinstance(o, dict) and o.get("tag") == "proxyfb"]
    if not px:
        return [], ["no outbound tagged proxyfb: proxy selection will have no effect"]
    try:
        addr = px[0]["settings"]["servers"][0]["address"]
    except (KeyError, IndexError, TypeError):
        addr = None
    if not isinstance(addr, str) or not addr:
        return ["proxyfb needs settings.servers[0].address"], []
    return [], []


def validate_config(cfg: dict) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    raw = json.dumps(cfg)
    if len(raw.encode()) > MAX_BYTES:
        errors.append("config too large")
    outs = cfg.get("outbounds")
    if not isinstance(outs, list) or not outs:
        errors.append("outbounds must be a non-empty list")
        return errors, warnings
    tags = []
    for i, o in enumerate(outs):
        if not isinstance(o, dict) or not o.get("protocol"):
            errors.append(f"outbounds[{i}] needs a protocol")
        elif o.get("tag"):
            tags.append(o["tag"])
    dups = sorted({t for t in tags if tags.count(t) > 1})
    if dups:
        errors.append("duplicate outbound tags: " + ", ".join(dups))
    e, w = _proxyfb_check(outs)
    errors += e
    warnings += w
    if "inbounds" in cfg and not isinstance(cfg["inbounds"], list):
        errors.append("inbounds must be a list")
    if "{{UUID}}" not in raw:
        warnings.append("no {{UUID}} placeholder: every subscriber gets the UUID written in the config")
    if not errors and settings.xray_bin:
        err = _xray_test(cfg)
        if err:
            errors.append(err)
    return errors, warnings


def _xray_test(cfg: dict) -> str | None:
    """Validate the config with the real Xray binary when available."""
    fd, path = tempfile.mkstemp(suffix=".json")
    try:
        with os.fdopen(fd, "w") as fh:
            json.dump(cfg, fh)
        proc = subprocess.run(
            [settings.xray_bin, "run", "-test", "-c", path],
            capture_output=True, text=True, timeout=20,
        )
        if proc.returncode != 0:
            msg = (proc.stderr or proc.stdout or "xray test failed").strip()
            return "xray rejected config: " + msg[-500:]
        return None
    except (OSError, subprocess.SubprocessError) as exc:
        return f"could not run xray test: {exc}"
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass


@router.get("")
def get_config(
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    cfg = _get_cfg(db)
    q = select(ConfigVersion).where(
        ConfigVersion.config_id == cfg.id, ConfigVersion.is_current.is_(True)
    )
    cur = db.scalar(q)
    db.commit()
    return {
        "draft": cfg.draft,
        "draft_updated_at": cfg.updated_at.isoformat(),
        "current_version": cur.version if cur else None,
    }


@router.put("")
def save_draft(
    body: ConfigIn,
    request: Request,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    cfg = _get_cfg(db)
    cfg.draft = body.config
    errors, warnings = validate_config(body.config)
    details = {"errors": len(errors)}
    write_audit(db, admin.id, "config_draft_saved", "config", cfg.id, details, _ip(request))
    db.commit()
    return {"saved": True, "errors": errors, "warnings": warnings}


@router.post("/publish")
def publish(
    body: PublishIn,
    request: Request,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    cfg = _get_cfg(db)
    errors, warnings = validate_config(cfg.draft)
    if errors:
        raise HTTPException(status_code=422, detail={"errors": errors})
    last = db.scalar(select(func.max(ConfigVersion.version)).where(ConfigVersion.config_id == cfg.id)) or 0
    db.execute(
        update(ConfigVersion)
        .where(ConfigVersion.config_id == cfg.id, ConfigVersion.is_current.is_(True))
        .values(is_current=False)
    )
    ver = ConfigVersion(
        config_id=cfg.id, version=last + 1, content=cfg.draft,
        note=body.note, is_current=True, created_by=admin.id,
    )
    db.add(ver)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="concurrent publish, retry")
    details = {"version": ver.version}
    write_audit(db, admin.id, "config_published", "config", cfg.id, details, _ip(request))
    db.commit()
    return {"version": ver.version, "warnings": warnings}


@router.get("/versions")
def list_versions(
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    cfg = _get_cfg(db)
    q = select(ConfigVersion).where(ConfigVersion.config_id == cfg.id)
    rows = db.scalars(q.order_by(ConfigVersion.version.desc())).all()
    db.commit()
    return [
        {
            "version": v.version,
            "note": v.note,
            "is_current": v.is_current,
            "created_by": v.created_by,
            "created_at": v.created_at.isoformat(),
        }
        for v in rows
    ]


def _get_version(db: Session, cfg: XrayConfig, version: int) -> ConfigVersion:
    q = select(ConfigVersion).where(
        ConfigVersion.config_id == cfg.id, ConfigVersion.version == version
    )
    v = db.scalar(q)
    if v is None:
        raise HTTPException(status_code=404, detail="version not found")
    return v


@router.get("/versions/{version}")
def get_version(
    version: int,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    v = _get_version(db, _get_cfg(db), version)
    return {"version": v.version, "note": v.note, "is_current": v.is_current, "content": v.content}


@router.post("/versions/{version}/restore")
def restore_version(
    version: int,
    request: Request,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    cfg = _get_cfg(db)
    v = _get_version(db, cfg, version)
    cfg.draft = v.content
    write_audit(db, admin.id, "config_restored", "config", cfg.id, {"version": version}, _ip(request))
    db.commit()
    return {"restored_to_draft": version}
