from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..audit import write_audit
from ..auth import DEVICE_TOKEN_HOURS, create_device_token, get_current_device
from ..db import get_db
from ..models import ConfigVersion, Device, Proxy, Subscription, XrayConfig
from ..services import apply_proxy_address, proxy_is_allowed, substitute_uuid

router = APIRouter(prefix="/api/v1", tags=["device"])

CONFIG_NAME = "default"


def _current_version(db: Session) -> ConfigVersion:
    q = (
        select(ConfigVersion)
        .join(XrayConfig, XrayConfig.id == ConfigVersion.config_id)
        .where(XrayConfig.name == CONFIG_NAME, ConfigVersion.is_current.is_(True))
    )
    v = db.scalar(q)
    if v is None:
        raise HTTPException(status_code=404, detail="no published config")
    return v


def _status(db: Session, dev: Device) -> dict:
    q = select(Subscription).where(Subscription.license_id == dev.license_id)
    sub = db.scalar(q.order_by(Subscription.ends_at.desc()).limit(1))
    now = datetime.now(timezone.utc)
    if sub is None:
        raise HTTPException(status_code=403, detail="subscription not valid")
    left = int((sub.ends_at - now).total_seconds())
    return {
        "valid": sub.status == "active" and left > 0,
        "license_status": dev.license.status,
        "starts_at": sub.starts_at.isoformat(),
        "ends_at": sub.ends_at.isoformat(),
        "remaining_seconds": max(0, left),
        "uuid_id": dev.license.uuid_id,
        "selected_proxy_id": dev.selected_proxy_id,
    }


@router.get("/config/version")
def config_version(
    dev: Device = Depends(get_current_device),
    db: Session = Depends(get_db),
):
    return {"version": _current_version(db).version}


@router.get("/config/current")
def config_current(
    dev: Device = Depends(get_current_device),
    db: Session = Depends(get_db),
):
    v = _current_version(db)
    uid = str(dev.license.xray_uuid.value)
    cfg = substitute_uuid(v.content, uid)
    if dev.selected_proxy_id:
        proxy = db.get(Proxy, dev.selected_proxy_id)
        if proxy is not None and proxy_is_allowed(db, dev.license_id, proxy):
            cfg = apply_proxy_address(cfg, proxy.address)
    return {
        "version": v.version,
        "config": cfg,
        "selected_proxy_id": dev.selected_proxy_id,
    }


@router.get("/subscriptions/me")
def subscription_me(
    dev: Device = Depends(get_current_device),
    db: Session = Depends(get_db),
):
    return _status(db, dev)


@router.post("/licenses/verify")
def verify(
    dev: Device = Depends(get_current_device),
    db: Session = Depends(get_db),
):
    dev.last_seen_at = datetime.now(timezone.utc)
    db.commit()
    return _status(db, dev)


@router.post("/licenses/refresh")
def refresh(dev: Device = Depends(get_current_device)):
    return {
        "device_token": create_device_token(dev.id, dev.license_id),
        "token_type": "bearer",
        "expires_in": DEVICE_TOKEN_HOURS * 3600,
    }


@router.get("/devices/me")
def device_me(
    dev: Device = Depends(get_current_device),
    db: Session = Depends(get_db),
):
    return {
        "id": dev.id,
        "model": dev.model,
        "fingerprint": dev.key_fingerprint[:12],
        "bound_at": dev.bound_at.isoformat(),
        "last_seen_at": dev.last_seen_at.isoformat() if dev.last_seen_at else None,
        "selected_proxy_id": dev.selected_proxy_id,
    }


@router.post("/devices/unbind")
def unbind(
    request: Request,
    dev: Device = Depends(get_current_device),
    db: Session = Depends(get_db),
):
    """Release the device slot for this license (user initiated)."""
    dev.is_active = False
    dev.unbound_at = datetime.now(timezone.utc)
    ip = request.client.host if request.client else None
    write_audit(db, None, "device_self_unbound", "license", dev.license_id,
                {"device_id": dev.id}, ip)
    db.commit()
    return {"unbound": True}
