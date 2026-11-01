from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from ..audit import write_audit
from ..auth import get_current_admin
from ..db import get_db
from ..models import AdminUser, AuditLog, Device, License, Subscription, XrayUuid
from ..security import generate_code, hash_code

router = APIRouter(prefix="/api/v1/admin/licenses", tags=["admin-licenses"])


class LicenseCreate(BaseModel):
    uuid_id: int
    days: int | None = Field(default=None, ge=1, le=3650)
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    note: str | None = None


def _ip(request: Request) -> str | None:
    return request.client.host if request.client else None


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _out(db: Session, lic: License) -> dict:
    q = select(Subscription).where(Subscription.license_id == lic.id)
    sub = db.scalar(q.order_by(Subscription.ends_at.desc()).limit(1))
    q = select(Device).where(Device.license_id == lic.id, Device.is_active.is_(True))
    dev = db.scalar(q)
    return {
        "id": lic.id,
        "status": lic.status,
        "uuid_id": lic.uuid_id,
        "note": lic.note,
        "created_at": lic.created_at.isoformat(),
        "subscription": sub and {
            "starts_at": sub.starts_at.isoformat(),
            "ends_at": sub.ends_at.isoformat(),
            "status": sub.status,
        },
        "device": dev and {
            "id": dev.id,
            "model": dev.model,
            "bound_at": dev.bound_at.isoformat(),
        },
    }


@router.post("", status_code=201)
def create_license(
    body: LicenseCreate,
    request: Request,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    u = db.get(XrayUuid, body.uuid_id)
    if u is None:
        raise HTTPException(status_code=404, detail="uuid not found")
    start = _aware(body.starts_at) if body.starts_at else _now()
    if body.ends_at:
        end = _aware(body.ends_at)
    elif body.days:
        end = start + timedelta(days=body.days)
    else:
        raise HTTPException(status_code=400, detail="give days or ends_at")
    if end <= start:
        raise HTTPException(status_code=400, detail="ends_at must be after starts_at")
    code = generate_code()
    lic = License(code_hash=hash_code(code), uuid_id=u.id, note=body.note)
    db.add(lic)
    db.flush()
    db.add(Subscription(license_id=lic.id, starts_at=start, ends_at=end))
    details = {"uuid_id": u.id, "ends_at": end.isoformat()}
    write_audit(db, admin.id, "license_created", "license", lic.id, details, _ip(request))
    db.commit()
    db.refresh(lic)
    out = _out(db, lic)
    out["code"] = code
    return out


@router.get("")
def list_licenses(
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    rows = db.scalars(select(License).order_by(License.id.desc())).all()
    return [_out(db, x) for x in rows]


class StatusIn(BaseModel):
    status: str = Field(pattern="^(active|disabled|banned)$")


def _get(db: Session, lic_id: int) -> License:
    lic = db.get(License, lic_id)
    if lic is None:
        raise HTTPException(status_code=404, detail="license not found")
    return lic


def _set_status(db, lic, status, admin, request):
    old = lic.status
    lic.status = status
    details = {"from": old, "to": status}
    write_audit(db, admin.id, "license_status", "license", lic.id, details, _ip(request))
    db.commit()
    db.refresh(lic)
    return _out(db, lic)


@router.post("/{lic_id}/status")
def set_status(
    lic_id: int,
    body: StatusIn,
    request: Request,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    return _set_status(db, _get(db, lic_id), body.status, admin, request)


@router.post("/{lic_id}/revoke")
def revoke(
    lic_id: int,
    request: Request,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    return _set_status(db, _get(db, lic_id), "banned", admin, request)


class RenewIn(BaseModel):
    days: int = Field(ge=1, le=3650)


@router.post("/{lic_id}/renew")
def renew(
    lic_id: int,
    body: RenewIn,
    request: Request,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    lic = _get(db, lic_id)
    q = select(Subscription).where(Subscription.license_id == lic.id)
    sub = db.scalar(q.order_by(Subscription.ends_at.desc()).limit(1))
    now = _now()
    if sub is None:
        sub = Subscription(license_id=lic.id, starts_at=now, ends_at=now)
        db.add(sub)
    base = max(_aware(sub.ends_at), now)
    sub.ends_at = base + timedelta(days=body.days)
    sub.status = "active"
    details = {"days": body.days, "ends_at": sub.ends_at.isoformat()}
    write_audit(db, admin.id, "license_renewed", "license", lic.id, details, _ip(request))
    db.commit()
    db.refresh(lic)
    return _out(db, lic)


@router.post("/{lic_id}/reset-device")
def reset_device(
    lic_id: int,
    request: Request,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    lic = _get(db, lic_id)
    q = select(Device).where(Device.license_id == lic.id, Device.is_active.is_(True))
    devs = db.scalars(q).all()
    for d in devs:
        d.is_active = False
        d.unbound_at = _now()
    write_audit(db, admin.id, "device_reset", "license", lic.id, {"devices": len(devs)}, _ip(request))
    db.commit()
    return {"reset": len(devs)}


@router.delete("/{lic_id}", status_code=204)
def delete_license(
    lic_id: int,
    request: Request,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    lic = _get(db, lic_id)
    write_audit(db, admin.id, "license_deleted", "license", lic.id, None, _ip(request))
    db.execute(delete(License).where(License.id == lic.id))
    db.commit()


@router.get("/{lic_id}/log")
def license_log(
    lic_id: int,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    _get(db, lic_id)
    q = select(AuditLog).where(
        AuditLog.entity_type == "license", AuditLog.entity_id == str(lic_id)
    )
    rows = db.scalars(q.order_by(AuditLog.id.desc()).limit(100)).all()
    return [
        {"action": x.action, "details": x.details, "ip": x.ip, "at": x.created_at.isoformat()}
        for x in rows
    ]


class ProxyAccessIn(BaseModel):
    proxy_ids: list[int]


@router.get("/{lic_id}/proxies")
def get_license_proxies(
    lic_id: int,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    from ..models import LicenseProxyAccess, Proxy

    lic = _get(db, lic_id)
    q = select(LicenseProxyAccess.proxy_id).where(
        LicenseProxyAccess.license_id == lic.id
    )
    ids = list(db.scalars(q).all())
    rows = db.scalars(select(Proxy).order_by(Proxy.sort_order, Proxy.id)).all()
    return {
        "license_id": lic.id,
        "proxy_ids": ids,
        "proxies": [
            {"id": p.id, "name": p.name, "address": p.address, "is_active": p.is_active}
            for p in rows
        ],
    }


@router.put("/{lic_id}/proxies")
def set_license_proxies(
    lic_id: int,
    body: ProxyAccessIn,
    request: Request,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    from ..models import LicenseProxyAccess, Proxy

    lic = _get(db, lic_id)
    wanted = set(body.proxy_ids)
    if wanted:
        found = set(db.scalars(select(Proxy.id).where(Proxy.id.in_(wanted))).all())
        missing = sorted(wanted - found)
        if missing:
            raise HTTPException(status_code=404, detail=f"proxies not found: {missing}")
    db.query(LicenseProxyAccess).filter(
        LicenseProxyAccess.license_id == lic.id
    ).delete(synchronize_session=False)
    for pid in wanted:
        db.add(LicenseProxyAccess(license_id=lic.id, proxy_id=pid))
    write_audit(db, admin.id, "license_proxy_access_updated", "license", lic.id,
                {"proxy_ids": sorted(wanted)}, _ip(request))
    db.commit()
    return {"license_id": lic.id, "proxy_ids": sorted(wanted)}
