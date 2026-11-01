import uuid as uuidlib

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..audit import write_audit
from ..auth import get_current_admin
from ..db import get_db
from ..models import AdminUser, License, XrayUuid

router = APIRouter(prefix="/api/v1/admin/uuids", tags=["admin-uuids"])


class UuidCreate(BaseModel):
    value: uuidlib.UUID | None = None
    label: str | None = None


def _ip(request: Request) -> str | None:
    return request.client.host if request.client else None


def _out(u: XrayUuid, count: int = 0) -> dict:
    return {
        "id": u.id,
        "value": str(u.value),
        "label": u.label,
        "is_active": u.is_active,
        "licenses": count,
        "created_at": u.created_at.isoformat(),
    }


@router.post("", status_code=201)
def create_uuid(
    body: UuidCreate,
    request: Request,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    value = body.value or uuidlib.uuid4()
    u = XrayUuid(value=value, label=body.label)
    db.add(u)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="uuid already exists")
    write_audit(db, admin.id, "uuid_created", "uuid", u.id, {"value": str(value)}, _ip(request))
    db.commit()
    db.refresh(u)
    return _out(u)


@router.get("")
def list_uuids(
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    q = select(License.uuid_id, func.count()).group_by(License.uuid_id)
    counts = dict(db.execute(q).all())
    rows = db.scalars(select(XrayUuid).order_by(XrayUuid.id)).all()
    return [_out(u, counts.get(u.id, 0)) for u in rows]


class UuidUpdate(BaseModel):
    value: uuidlib.UUID | None = None
    label: str | None = None
    is_active: bool | None = None


def _get(db: Session, uuid_id: int) -> XrayUuid:
    u = db.get(XrayUuid, uuid_id)
    if u is None:
        raise HTTPException(status_code=404, detail="uuid not found")
    return u


@router.patch("/{uuid_id}")
def update_uuid(
    uuid_id: int,
    body: UuidUpdate,
    request: Request,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    u = _get(db, uuid_id)
    data = body.model_dump(exclude_unset=True)
    changes = {k: v for k, v in data.items() if v is not None or k == "label"}
    if not changes:
        raise HTTPException(status_code=400, detail="nothing to update")
    for k, v in changes.items():
        setattr(u, k, v)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="uuid already exists")
    details = {k: str(v) for k, v in changes.items()}
    write_audit(db, admin.id, "uuid_updated", "uuid", u.id, details, _ip(request))
    db.commit()
    db.refresh(u)
    q = select(func.count()).select_from(License).where(License.uuid_id == u.id)
    return _out(u, db.scalar(q) or 0)


@router.delete("/{uuid_id}", status_code=204)
def delete_uuid(
    uuid_id: int,
    request: Request,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    u = _get(db, uuid_id)
    q = select(func.count()).select_from(License).where(License.uuid_id == u.id)
    n = db.scalar(q) or 0
    if n:
        raise HTTPException(status_code=409, detail=f"uuid is linked to {n} licenses")
    write_audit(db, admin.id, "uuid_deleted", "uuid", u.id, {"value": str(u.value)}, _ip(request))
    db.delete(u)
    db.commit()


@router.get("/{uuid_id}/licenses")
def uuid_licenses(
    uuid_id: int,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    u = _get(db, uuid_id)
    q = select(License).where(License.uuid_id == u.id).order_by(License.id)
    return [
        {"id": x.id, "status": x.status, "note": x.note, "created_at": x.created_at.isoformat()}
        for x in db.scalars(q).all()
    ]
