from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth import get_current_device
from ..db import get_db
from ..models import Device, Proxy
from ..services import allowed_proxy_ids, proxy_is_allowed

router = APIRouter(prefix="/api/v1/proxies", tags=["proxies"])


@router.get("")
def list_for_device(
    dev: Device = Depends(get_current_device),
    db: Session = Depends(get_db),
):
    allowed = allowed_proxy_ids(db, dev.license_id)
    q = select(Proxy).where(Proxy.is_active.is_(True))
    if allowed:
        q = q.where(Proxy.id.in_(allowed))
    rows = db.scalars(q.order_by(Proxy.sort_order, Proxy.id)).all()
    return [
        {
            "id": p.id,
            "name": p.name,
            "address": p.address,
            "selected": p.id == dev.selected_proxy_id,
        }
        for p in rows
    ]


class SelectIn(BaseModel):
    proxy_id: int


@router.post("/select")
def select_proxy(
    body: SelectIn,
    dev: Device = Depends(get_current_device),
    db: Session = Depends(get_db),
):
    proxy = db.get(Proxy, body.proxy_id)
    if proxy is None:
        raise HTTPException(status_code=404, detail="proxy not found")
    if not proxy_is_allowed(db, dev.license_id, proxy):
        raise HTTPException(status_code=403, detail="proxy not allowed")
    dev.selected_proxy_id = proxy.id
    db.commit()
    return {"selected_proxy_id": proxy.id, "name": proxy.name, "address": proxy.address}
