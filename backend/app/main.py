from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.orm import Session

from .db import get_db
from .routers import (
    admin_auth, admin_uuids, admin_licenses, licenses, admin_config,
    admin_proxies, proxies, device_api, admin_stats, admin_subscriptions, admin_xray,
)

app = FastAPI(title="MIFTAH API", version="0.1.0")
app.include_router(admin_auth.router)
app.include_router(admin_stats.router)
app.include_router(device_api.router)
app.include_router(proxies.router)
app.include_router(admin_proxies.router)
app.include_router(licenses.router)
app.include_router(admin_config.router)
app.include_router(admin_licenses.router)
app.include_router(admin_uuids.router)
app.include_router(admin_subscriptions.router)
app.include_router(admin_xray.router)


@app.get("/health")
def health():
    return {"status": "ok", "service": "miftah-api"}


@app.get("/health/db")
def health_db(db: Session = Depends(get_db)):
    db.execute(text("select 1"))
    return {"status": "ok", "database": "connected"}
