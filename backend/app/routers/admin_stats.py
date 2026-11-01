from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..auth import get_current_admin
from ..db import get_db
from ..models import AdminUser, AuditLog, Device, License, Subscription, XrayUuid

router = APIRouter(prefix="/api/v1/admin", tags=["admin-stats"])


def _n(db: Session, q) -> int:
    return db.scalar(q) or 0


def _cnt(model):
    return select(func.count()).select_from(model)


@router.get("/stats")
def stats(
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    now = datetime.now(timezone.utc)
    last = select(
        Subscription.license_id.label("lid"),
        func.max(Subscription.ends_at).label("e"),
    ).group_by(Subscription.license_id).subquery()
    base = _cnt(License).join(last, last.c.lid == License.id)
    active = _n(db, base.where(License.status == "active", last.c.e > now))
    expired = _n(db, base.where(License.status == "active", last.c.e <= now))
    q = select(AuditLog).where(AuditLog.action == "activation_ok")
    rows = db.scalars(q.order_by(AuditLog.id.desc()).limit(10)).all()
    return {
        "licenses_total": _n(db, _cnt(License)),
        "licenses_active": active,
        "licenses_expired": expired,
        "licenses_banned": _n(db, _cnt(License).where(License.status == "banned")),
        "licenses_disabled": _n(db, _cnt(License).where(License.status == "disabled")),
        "devices_active": _n(db, _cnt(Device).where(Device.is_active.is_(True))),
        "uuids_total": _n(db, _cnt(XrayUuid)),
        "subscriptions_total": _n(db, _cnt(Subscription)),
        "recent_activations": [
            {"license_id": x.entity_id, "ip": x.ip, "at": x.created_at.isoformat()}
            for x in rows
        ],
    }


@router.get("/audit-logs")
def audit_logs(
    limit: int = 100,
    action: str | None = None,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    q = select(AuditLog)
    if action:
        q = q.where(AuditLog.action == action)
    n = max(1, min(limit, 500))
    rows = db.scalars(q.order_by(AuditLog.id.desc()).limit(n)).all()
    return [
        {
            "id": x.id,
            "action": x.action,
            "entity_type": x.entity_type,
            "entity_id": x.entity_id,
            "admin_id": x.admin_id,
            "ip": x.ip,
            "details": x.details,
            "at": x.created_at.isoformat(),
        }
        for x in rows
    ]


@router.get("/devices")
def devices(
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    rows = db.scalars(select(Device).order_by(Device.id.desc()).limit(500)).all()
    return [
        {
            "id": d.id,
            "license_id": d.license_id,
            "model": d.model,
            "is_active": d.is_active,
            "fingerprint": d.key_fingerprint[:12],
            "bound_at": d.bound_at.isoformat(),
            "last_seen_at": d.last_seen_at.isoformat() if d.last_seen_at else None,
            "unbound_at": d.unbound_at.isoformat() if d.unbound_at else None,
        }
        for d in rows
    ]
