from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..auth import TOKEN_MINUTES, create_admin_token, get_current_admin
from ..db import get_db
from ..models import AdminUser, AuditLog
from ..passwords import hash_password, verify_password

router = APIRouter(prefix="/api/v1/admin", tags=["admin-auth"])

IP_MAX_FAILS = 5
USER_MAX_FAILS = 20
WINDOW_MINUTES = 15
_DUMMY_HASH = hash_password("dummy-password-for-timing")


class LoginIn(BaseModel):
    username: str
    password: str


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def _recent_fails(db: Session, ip: str | None = None, username: str | None = None) -> int:
    since = datetime.now(timezone.utc) - timedelta(minutes=WINDOW_MINUTES)
    q = select(func.count()).select_from(AuditLog).where(
        AuditLog.action == "admin_login_failed",
        AuditLog.created_at >= since,
    )
    if ip is not None:
        q = q.where(AuditLog.ip == ip)
    if username is not None:
        q = q.where(AuditLog.entity_id == username[:64])
    return db.scalar(q) or 0


def _log(db: Session, action: str, ip: str, admin_id: int | None = None, username: str | None = None) -> None:
    entity = username[:64] if username else None
    db.add(AuditLog(admin_id=admin_id, action=action, entity_type="admin", entity_id=entity, ip=ip))
    db.commit()


@router.post("/login")
def login(body: LoginIn, request: Request, db: Session = Depends(get_db)):
    ip = _client_ip(request)
    if _recent_fails(db, ip=ip) >= IP_MAX_FAILS or _recent_fails(db, username=body.username) >= USER_MAX_FAILS:
        raise HTTPException(status_code=429, detail="too many attempts")
    admin = db.scalar(select(AdminUser).where(AdminUser.username == body.username))
    stored = admin.password_hash if admin else _DUMMY_HASH
    ok = verify_password(body.password, stored)
    if admin is None or not ok or not admin.is_active:
        _log(db, "admin_login_failed", ip, username=body.username)
        raise HTTPException(status_code=401, detail="invalid credentials")
    admin.last_login_at = datetime.now(timezone.utc)
    _log(db, "admin_login_ok", ip, admin_id=admin.id, username=admin.username)
    return {
        "access_token": create_admin_token(admin.id),
        "token_type": "bearer",
        "expires_in": TOKEN_MINUTES * 60,
    }


@router.get("/me")
def me(admin: AdminUser = Depends(get_current_admin)):
    return {"id": admin.id, "username": admin.username}


class PasswordIn(BaseModel):
    current: str
    new: str = Field(min_length=12, max_length=128)


@router.post("/password")
def change_password(
    body: PasswordIn,
    request: Request,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    ip = _client_ip(request)
    if _recent_fails(db, username=admin.username) >= USER_MAX_FAILS:
        raise HTTPException(status_code=429, detail="too many attempts")
    if not verify_password(body.current, admin.password_hash):
        _log(db, "admin_login_failed", ip, username=admin.username)
        raise HTTPException(status_code=403, detail="wrong password")
    admin.password_hash = hash_password(body.new)
    _log(db, "admin_password_changed", ip, admin_id=admin.id, username=admin.username)
    return {"changed": True}
