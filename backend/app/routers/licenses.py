import base64
import binascii
import hashlib
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..audit import write_audit
from ..auth import DEVICE_TOKEN_HOURS, create_device_token
from ..db import get_db
from ..models import AuditLog, Device, License, Subscription
from ..security import hash_code

router = APIRouter(prefix="/api/v1/licenses", tags=["licenses"])

MAX_FAILS = 10
WINDOW_MINUTES = 15


class ActivateIn(BaseModel):
    code: str = Field(min_length=8, max_length=64)
    public_key: str = Field(min_length=40, max_length=4096)
    model: str | None = Field(default=None, max_length=100)


def _ip(request: Request) -> str | None:
    return request.client.host if request.client else None


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _recent_fails(db: Session, ip: str | None) -> int:
    since = _now() - timedelta(minutes=WINDOW_MINUTES)
    q = select(func.count()).select_from(AuditLog).where(
        AuditLog.action == "activation_failed",
        AuditLog.ip == ip,
        AuditLog.created_at >= since,
    )
    return db.scalar(q) or 0


def _deny(db, ip, action, reason, lic_id, status, detail):
    write_audit(db, None, action, "license", lic_id, {"reason": reason}, ip)
    db.commit()
    raise HTTPException(status_code=status, detail=detail)


def _check_license(db: Session, ip: str | None, code: str) -> License:
    lic = db.scalar(select(License).where(License.code_hash == hash_code(code)))
    if lic is None:
        _deny(db, ip, "activation_failed", "unknown_code", None, 403, "invalid code")
    if lic.status != "active":
        _deny(db, ip, "activation_denied", lic.status, lic.id, 403, f"license {lic.status}")
    if not lic.xray_uuid.is_active:
        _deny(db, ip, "activation_denied", "uuid_disabled", lic.id, 403, "license unavailable")
    q = select(Subscription).where(Subscription.license_id == lic.id)
    sub = db.scalar(q.order_by(Subscription.ends_at.desc()).limit(1))
    now = _now()
    if sub is None or sub.status != "active":
        _deny(db, ip, "activation_denied", "no_subscription", lic.id, 403, "no active subscription")
    if now < _aware(sub.starts_at):
        _deny(db, ip, "activation_denied", "not_started", lic.id, 403, "subscription not started")
    if now >= _aware(sub.ends_at):
        _deny(db, ip, "activation_denied", "expired", lic.id, 403, "subscription expired")
    return lic


@router.post("/activate")
def activate(body: ActivateIn, request: Request, db: Session = Depends(get_db)):
    ip = _ip(request)
    if _recent_fails(db, ip) >= MAX_FAILS:
        raise HTTPException(status_code=429, detail="too many attempts")
    try:
        raw = base64.b64decode(body.public_key, validate=True)
    except (binascii.Error, ValueError):
        raise HTTPException(status_code=400, detail="invalid public_key")
    if not 32 <= len(raw) <= 2048:
        raise HTTPException(status_code=400, detail="invalid public_key")
    lic = _check_license(db, ip, body.code)
    fp = hashlib.sha256(raw).hexdigest()
    q = select(Device).where(Device.license_id == lic.id, Device.is_active.is_(True))
    dev = db.scalar(q)
    if dev is not None and dev.key_fingerprint != fp:
        _deny(db, ip, "activation_denied", "device_mismatch", lic.id, 409, "license bound to another device")
    if dev is None:
        dev = Device(license_id=lic.id, public_key=body.public_key, key_fingerprint=fp, model=body.model)
        db.add(dev)
        try:
            db.flush()
        except IntegrityError:
            db.rollback()
            _deny(db, ip, "activation_denied", "device_race", lic.id, 409, "license bound to another device")
    dev.last_seen_at = _now()
    write_audit(db, None, "activation_ok", "license", lic.id, {"device_id": dev.id}, ip)
    db.commit()
    sub = db.scalar(
        select(Subscription).where(Subscription.license_id == lic.id)
        .order_by(Subscription.ends_at.desc()).limit(1)
    )
    return {
        "device_token": create_device_token(dev.id, lic.id),
        "token_type": "bearer",
        "expires_in": DEVICE_TOKEN_HOURS * 3600,
        "license_status": lic.status,
        "subscription": {
            "starts_at": sub.starts_at.isoformat(),
            "ends_at": sub.ends_at.isoformat(),
        },
    }
