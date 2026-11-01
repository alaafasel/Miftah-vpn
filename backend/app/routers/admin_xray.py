from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import xray_client
from ..audit import write_audit
from ..auth import get_current_admin
from ..db import get_db
from ..models import AdminUser, XrayServer, XrayServerUser, XrayUuid

router = APIRouter(prefix="/api/v1/admin/xray", tags=["admin-xray"])

URL = r"^https?://[A-Za-z0-9._:\-\[\]]+(/[A-Za-z0-9._\-/]*)?$"


def _ip(request: Request) -> str | None:
    return request.client.host if request.client else None


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _out(s: XrayServer) -> dict:
    return {
        "id": s.id,
        "name": s.name,
        "address": s.address,
        "port": s.port,
        "agent_url": s.agent_url,
        "is_active": s.is_active,
        "status": s.status,
        "xray_version": s.xray_version,
        "config_version": s.config_version,
        "has_config": bool(s.config),
        "last_checked_at": s.last_checked_at.isoformat() if s.last_checked_at else None,
    }


def _get(db: Session, server_id: int) -> XrayServer:
    s = db.get(XrayServer, server_id)
    if s is None:
        raise HTTPException(status_code=404, detail="server not found")
    return s


class ServerCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    address: str = Field(min_length=1, max_length=255)
    port: int = Field(default=443, ge=1, le=65535)
    agent_url: str = Field(pattern=URL)
    agent_token: str = Field(min_length=16, max_length=255)


class ServerUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    address: str | None = Field(default=None, min_length=1, max_length=255)
    port: int | None = Field(default=None, ge=1, le=65535)
    agent_url: str | None = Field(default=None, pattern=URL)
    agent_token: str | None = Field(default=None, min_length=16, max_length=255)
    is_active: bool | None = None


@router.get("/servers")
def list_servers(
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    rows = db.scalars(select(XrayServer).order_by(XrayServer.id)).all()
    return [_out(s) for s in rows]


@router.post("/servers", status_code=201)
def create_server(
    body: ServerCreate,
    request: Request,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    if db.scalar(select(XrayServer).where(XrayServer.name == body.name)):
        raise HTTPException(status_code=409, detail="server name already exists")
    s = XrayServer(**body.model_dump())
    db.add(s)
    db.flush()
    write_audit(db, admin.id, "xray_server_created", "xray_server", s.id,
                {"name": s.name, "address": s.address}, _ip(request))
    db.commit()
    db.refresh(s)
    return _out(s)


@router.patch("/servers/{server_id}")
def update_server(
    server_id: int,
    body: ServerUpdate,
    request: Request,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    s = _get(db, server_id)
    data = body.model_dump(exclude_none=True)
    if not data:
        raise HTTPException(status_code=400, detail="nothing to update")
    for k, v in data.items():
        setattr(s, k, v)
    write_audit(db, admin.id, "xray_server_updated", "xray_server", s.id,
                {k: str(v) for k, v in data.items()}, _ip(request))
    db.commit()
    db.refresh(s)
    return _out(s)


@router.delete("/servers/{server_id}", status_code=204)
def delete_server(
    server_id: int,
    request: Request,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    s = _get(db, server_id)
    write_audit(db, admin.id, "xray_server_deleted", "xray_server", s.id,
                {"name": s.name}, _ip(request))
    db.delete(s)
    db.commit()


@router.post("/servers/{server_id}/check")
def check_server(
    server_id: int,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    s = _get(db, server_id)
    try:
        h = xray_client.health(s)
    except xray_client.AgentError as exc:
        s.status = "offline"
        s.last_checked_at = _now()
        db.commit()
        raise HTTPException(status_code=502, detail=str(exc))
    s.status = "online"
    s.xray_version = h.get("xray_version")
    s.last_checked_at = _now()
    db.commit()
    return {"status": "online", **h}


@router.get("/servers/{server_id}/status")
def server_status(
    server_id: int,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    s = _get(db, server_id)
    try:
        st = xray_client.status(s)
    except xray_client.AgentError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    return st


class ConfigIn(BaseModel):
    config: dict


@router.get("/servers/{server_id}/config")
def get_server_config(
    server_id: int,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    s = _get(db, server_id)
    return {"config": s.config, "config_version": s.config_version}


@router.put("/servers/{server_id}/config")
def save_server_config(
    server_id: int,
    body: ConfigIn,
    request: Request,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    s = _get(db, server_id)
    try:
        result = xray_client.validate(s, body.config)
    except xray_client.AgentError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    if not result.get("valid", False):
        raise HTTPException(status_code=422, detail=result.get("error", "invalid config"))
    s.config = body.config
    write_audit(db, admin.id, "xray_config_saved", "xray_server", s.id, None, _ip(request))
    db.commit()
    return {"saved": True, "valid": True}


@router.post("/servers/{server_id}/apply")
def apply_server_config(
    server_id: int,
    request: Request,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    s = _get(db, server_id)
    if not s.config:
        raise HTTPException(status_code=400, detail="no server config saved")
    try:
        result = xray_client.apply_config(s, s.config)
    except xray_client.AgentError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    s.config_version += 1
    s.status = "online"
    s.last_checked_at = _now()
    write_audit(db, admin.id, "xray_config_applied", "xray_server", s.id,
                {"version": s.config_version}, _ip(request))
    db.commit()
    return {"applied": True, "version": s.config_version, "agent": result}


@router.get("/servers/{server_id}/users")
def list_server_users(
    server_id: int,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    s = _get(db, server_id)
    rows = db.scalars(
        select(XrayServerUser).where(XrayServerUser.server_id == s.id).order_by(XrayServerUser.id)
    ).all()
    return [
        {
            "id": u.id,
            "uuid_id": u.uuid_id,
            "uuid": str(u.xray_uuid.value),
            "email": u.email,
            "is_enabled": u.is_enabled,
        }
        for u in rows
    ]


class UserIn(BaseModel):
    uuid_id: int
    email: str | None = Field(default=None, max_length=100)


@router.post("/servers/{server_id}/users", status_code=201)
def add_server_user(
    server_id: int,
    body: UserIn,
    request: Request,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    s = _get(db, server_id)
    if db.get(XrayUuid, body.uuid_id) is None:
        raise HTTPException(status_code=404, detail="uuid not found")
    exists = db.scalar(
        select(XrayServerUser).where(
            XrayServerUser.server_id == s.id, XrayServerUser.uuid_id == body.uuid_id
        )
    )
    if exists:
        raise HTTPException(status_code=409, detail="user already linked")
    u = XrayServerUser(server_id=s.id, uuid_id=body.uuid_id, email=body.email)
    db.add(u)
    db.flush()
    write_audit(db, admin.id, "xray_user_added", "xray_server", s.id,
                {"uuid_id": body.uuid_id}, _ip(request))
    db.commit()
    db.refresh(u)
    return {"id": u.id, "uuid_id": u.uuid_id, "email": u.email, "is_enabled": u.is_enabled}


class UserUpdate(BaseModel):
    email: str | None = Field(default=None, max_length=100)
    is_enabled: bool | None = None


@router.patch("/servers/{server_id}/users/{user_id}")
def update_server_user(
    server_id: int,
    user_id: int,
    body: UserUpdate,
    request: Request,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    s = _get(db, server_id)
    u = db.get(XrayServerUser, user_id)
    if u is None or u.server_id != s.id:
        raise HTTPException(status_code=404, detail="user not found")
    data = body.model_dump(exclude_none=True)
    for k, v in data.items():
        setattr(u, k, v)
    write_audit(db, admin.id, "xray_user_updated", "xray_server", s.id,
                {"user_id": u.id, **{k: str(v) for k, v in data.items()}}, _ip(request))
    db.commit()
    return {"id": u.id, "email": u.email, "is_enabled": u.is_enabled}


@router.delete("/servers/{server_id}/users/{user_id}", status_code=204)
def delete_server_user(
    server_id: int,
    user_id: int,
    request: Request,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    s = _get(db, server_id)
    u = db.get(XrayServerUser, user_id)
    if u is None or u.server_id != s.id:
        raise HTTPException(status_code=404, detail="user not found")
    write_audit(db, admin.id, "xray_user_deleted", "xray_server", s.id,
                {"user_id": u.id}, _ip(request))
    db.delete(u)
    db.commit()


@router.post("/servers/{server_id}/sync-users")
def sync_users(
    server_id: int,
    request: Request,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    s = _get(db, server_id)
    rows = db.scalars(
        select(XrayServerUser).where(XrayServerUser.server_id == s.id)
    ).all()
    if rows:
        users = [
            {"id": str(u.xray_uuid.value), "email": u.email or f"u{u.uuid_id}",
             "enabled": u.is_enabled}
            for u in rows
        ]
    else:
        uuids = db.scalars(select(XrayUuid).where(XrayUuid.is_active.is_(True))).all()
        users = [
            {"id": str(u.value), "email": u.label or f"uuid{u.id}", "enabled": True}
            for u in uuids
        ]
    try:
        result = xray_client.sync_users(s, users)
    except xray_client.AgentError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    write_audit(db, admin.id, "xray_users_synced", "xray_server", s.id,
                {"count": len(users)}, _ip(request))
    db.commit()
    return {"synced": len(users), "agent": result}
