from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..audit import write_audit
from ..auth import get_current_admin
from ..db import get_db
from ..models import AdminUser, License, Subscription, XrayUuid

router = APIRouter(prefix="/api/v1/admin/subscriptions", tags=["admin-subscriptions"])


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _ip(request: Request) -> str | None:
    return request.client.host if request.client else None


def _out(s: Subscription, lic: License | None = None, uid: XrayUuid | None = None) -> dict:
    return {
        "id": s.id,
        "license_id": s.license_id,
        "status": s.status,
        "starts_at": s.starts_at.isoformat(),
        "ends_at": s.ends_at.isoformat(),
        "created_at": s.created_at.isoformat(),
        "license_status": lic.status if lic else None,
        "license_note": lic.note if lic else None,
        "uuid": str(uid.value) if uid else None,
    }


def _get(db: Session, sub_id: int) -> Subscription:
    s = db.get(Subscription, sub_id)
    if s is None:
        raise HTTPException(status_code=404, detail="subscription not found")
    return s


@router.get("")
def list_subscriptions(
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    rows = db.scalars(select(Subscription).order_by(Subscription.id.desc()).limit(1000)).all()
    out = []
    for s in rows:
        lic = db.get(License, s.license_id)
        uid = db.get(XrayUuid, lic.uuid_id) if lic else None
        out.append(_out(s, lic, uid))
    return out


class SubCreate(BaseModel):
    license_id: int
    days: int | None = Field(default=None, ge=1, le=3650)
    starts_at: datetime | None = None
    ends_at: datetime | None = None


@router.post("", status_code=201)
def create_subscription(
    body: SubCreate,
    request: Request,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    lic = db.get(License, body.license_id)
    if lic is None:
        raise HTTPException(status_code=404, detail="license not found")
    start = _aware(body.starts_at) if body.starts_at else _now()
    if body.ends_at:
        end = _aware(body.ends_at)
    elif body.days:
        end = start + timedelta(days=body.days)
    else:
        raise HTTPException(status_code=400, detail="give days or ends_at")
    if end <= start:
        raise HTTPException(status_code=400, detail="ends_at must be after starts_at")
    s = Subscription(license_id=lic.id, starts_at=start, ends_at=end)
    db.add(s)
    db.flush()
    write_audit(db, admin.id, "subscription_created", "subscription", s.id,
                {"license_id": lic.id, "ends_at": end.isoformat()}, _ip(request))
    db.commit()
    db.refresh(s)
    return _out(s, lic)


class ExtendIn(BaseModel):
    days: int = Field(ge=1, le=3650)


@router.post("/{sub_id}/extend")
def extend(
    sub_id: int,
    body: ExtendIn,
    request: Request,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    s = _get(db, sub_id)
    base = max(_aware(s.ends_at), _now())
    s.ends_at = base + timedelta(days=body.days)
    s.status = "active"
    write_audit(db, admin.id, "subscription_extended", "subscription", s.id,
                {"days": body.days, "ends_at": s.ends_at.isoformat()}, _ip(request))
    db.commit()
    db.refresh(s)
    return _out(s)


class StatusIn(BaseModel):
    status: str = Field(pattern="^(active|stopped|banned)$")


@router.post("/{sub_id}/status")
def set_status(
    sub_id: int,
    body: StatusIn,
    request: Request,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    s = _get(db, sub_id)
    old = s.status
    s.status = body.status
    write_audit(db, admin.id, "subscription_status", "subscription", s.id,
                {"from": old, "to": body.status}, _ip(request))
    db.commit()
    db.refresh(s)
    return _out(s)


@router.delete("/{sub_id}", status_code=204)
def delete_subscription(
    sub_id: int,
    request: Request,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    s = _get(db, sub_id)
    write_audit(db, admin.id, "subscription_deleted", "subscription", s.id, None, _ip(request))
    db.delete(s)
    db.commit()
