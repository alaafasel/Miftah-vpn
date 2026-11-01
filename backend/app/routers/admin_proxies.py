from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..audit import write_audit
from ..auth import get_current_admin
from ..db import get_db
from ..models import AdminUser, Proxy

router = APIRouter(prefix="/api/v1/admin/proxies", tags=["admin-proxies"])

ADDR = r"^[A-Za-z0-9.:\-]{1,255}$"


class ProxyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    address: str = Field(pattern=ADDR)
    sort_order: int = 0


class ProxyUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    address: str | None = Field(default=None, pattern=ADDR)
    is_active: bool | None = None
    sort_order: int | None = None


def _ip(request: Request) -> str | None:
    return request.client.host if request.client else None


def _out(p: Proxy) -> dict:
    return {
        "id": p.id,
        "name": p.name,
        "address": p.address,
        "is_active": p.is_active,
        "sort_order": p.sort_order,
    }


def _get(db: Session, proxy_id: int) -> Proxy:
    p = db.get(Proxy, proxy_id)
    if p is None:
        raise HTTPException(status_code=404, detail="proxy not found")
    return p


@router.post("", status_code=201)
def create_proxy(
    body: ProxyCreate,
    request: Request,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    p = Proxy(name=body.name, address=body.address, sort_order=body.sort_order)
    db.add(p)
    db.flush()
    details = {"name": p.name, "address": p.address}
    write_audit(db, admin.id, "proxy_created", "proxy", p.id, details, _ip(request))
    db.commit()
    db.refresh(p)
    return _out(p)


@router.get("")
def list_proxies(
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    rows = db.scalars(select(Proxy).order_by(Proxy.sort_order, Proxy.id)).all()
    return [_out(p) for p in rows]


@router.patch("/{proxy_id}")
def update_proxy(
    proxy_id: int,
    body: ProxyUpdate,
    request: Request,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    p = _get(db, proxy_id)
    data = body.model_dump(exclude_none=True)
    if not data:
        raise HTTPException(status_code=400, detail="nothing to update")
    for k, v in data.items():
        setattr(p, k, v)
    write_audit(db, admin.id, "proxy_updated", "proxy", p.id, data, _ip(request))
    db.commit()
    db.refresh(p)
    return _out(p)


@router.delete("/{proxy_id}", status_code=204)
def delete_proxy(
    proxy_id: int,
    request: Request,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    p = _get(db, proxy_id)
    write_audit(db, admin.id, "proxy_deleted", "proxy", p.id, {"name": p.name}, _ip(request))
    db.delete(p)
    db.commit()


class AccessIn(BaseModel):
    license_ids: list[int]


@router.get("/{proxy_id}/access")
def get_access(
    proxy_id: int,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    from ..models import License, LicenseProxyAccess

    p = _get(db, proxy_id)
    q = select(LicenseProxyAccess.license_id).where(
        LicenseProxyAccess.proxy_id == p.id
    )
    ids = list(db.scalars(q).all())
    lic = db.scalars(select(License).order_by(License.id)).all()
    return {
        "proxy_id": p.id,
        "license_ids": ids,
        "licenses": [
            {"id": x.id, "status": x.status, "note": x.note} for x in lic
        ],
    }


@router.put("/{proxy_id}/access")
def set_access(
    proxy_id: int,
    body: AccessIn,
    request: Request,
    admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    from ..models import License, LicenseProxyAccess

    p = _get(db, proxy_id)
    wanted = set(body.license_ids)
    if wanted:
        found = set(db.scalars(select(License.id).where(License.id.in_(wanted))).all())
        missing = sorted(wanted - found)
        if missing:
            raise HTTPException(status_code=404, detail=f"licenses not found: {missing}")
    db.query(LicenseProxyAccess).filter(
        LicenseProxyAccess.proxy_id == p.id
    ).delete(synchronize_session=False)
    for lid in wanted:
        db.add(LicenseProxyAccess(license_id=lid, proxy_id=p.id))
    write_audit(db, admin.id, "proxy_access_updated", "proxy", p.id,
                {"license_ids": sorted(wanted)}, _ip(request))
    db.commit()
    return {"proxy_id": p.id, "license_ids": sorted(wanted)}
