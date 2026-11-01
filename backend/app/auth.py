from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session
from sqlalchemy import select

from .config import settings
from .db import get_db
from .models import AdminUser, Device, Subscription

bearer = HTTPBearer(auto_error=False)
ALGO = "HS256"
TOKEN_MINUTES = 30


def create_admin_token(admin_id: int) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(admin_id),
        "typ": "admin",
        "iat": now,
        "exp": now + timedelta(minutes=TOKEN_MINUTES),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=ALGO)


def _unauthorized() -> HTTPException:
    return HTTPException(status_code=401, detail="unauthorized")


def get_current_admin(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> AdminUser:
    if creds is None:
        raise _unauthorized()
    try:
        data = jwt.decode(creds.credentials, settings.jwt_secret, algorithms=[ALGO])
    except jwt.PyJWTError:
        raise _unauthorized()
    if data.get("typ") != "admin":
        raise _unauthorized()
    admin = db.get(AdminUser, int(data["sub"]))
    if admin is None or not admin.is_active:
        raise _unauthorized()
    return admin


DEVICE_TOKEN_HOURS = 24


def create_device_token(device_id: int, license_id: int) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(device_id),
        "lic": license_id,
        "typ": "device",
        "iat": now,
        "exp": now + timedelta(hours=DEVICE_TOKEN_HOURS),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=ALGO)


def get_current_device(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> Device:
    if creds is None:
        raise _unauthorized()
    try:
        data = jwt.decode(creds.credentials, settings.jwt_secret, algorithms=[ALGO])
    except jwt.PyJWTError:
        raise _unauthorized()
    if data.get("typ") != "device":
        raise _unauthorized()
    dev = db.get(Device, int(data["sub"]))
    if dev is None or not dev.is_active or dev.license_id != data.get("lic"):
        raise _unauthorized()
    lic = dev.license
    if lic.status != "active" or not lic.xray_uuid.is_active:
        raise HTTPException(status_code=403, detail="license unavailable")
    q = select(Subscription).where(Subscription.license_id == lic.id)
    sub = db.scalar(q.order_by(Subscription.ends_at.desc()).limit(1))
    now = datetime.now(timezone.utc)
    if sub is None or sub.status != "active" or not (sub.starts_at <= now < sub.ends_at):
        raise HTTPException(status_code=403, detail="subscription not valid")
    return dev
