"""Shared domain helpers for MIFTAH."""
import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import LicenseProxyAccess, Proxy

PROXY_TAG = "proxyfb"


def allowed_proxy_ids(db: Session, license_id: int) -> list[int]:
    """Return proxy ids explicitly granted to a license.

    An empty grant list means "all active proxies are allowed" (default
    behaviour kept from the first implementation).
    """
    q = select(LicenseProxyAccess.proxy_id).where(
        LicenseProxyAccess.license_id == license_id
    )
    return list(db.scalars(q).all())


def proxy_is_allowed(db: Session, license_id: int, proxy: Proxy) -> bool:
    if not proxy.is_active:
        return False
    allowed = allowed_proxy_ids(db, license_id)
    return not allowed or proxy.id in allowed


def apply_proxy_address(config: dict, address: str) -> dict:
    """Return a copy of config with proxyfb outbound address replaced.

    Only ``outbounds[tag=proxyfb].settings.servers[0].address`` changes,
    exactly as required by the project document.
    """
    cfg = json.loads(json.dumps(config))
    for out in cfg.get("outbounds", []):
        if isinstance(out, dict) and out.get("tag") == PROXY_TAG:
            settings = out.setdefault("settings", {})
            servers = settings.get("servers")
            if not isinstance(servers, list) or not servers:
                servers = [{}]
                settings["servers"] = servers
            servers[0]["address"] = address
            break
    return cfg


def substitute_uuid(value: Any, uid: str) -> Any:
    """Recursively replace the {{UUID}} placeholder in a JSON structure."""
    if isinstance(value, str):
        return value.replace("{{UUID}}", uid)
    if isinstance(value, list):
        return [substitute_uuid(v, uid) for v in value]
    if isinstance(value, dict):
        return {k: substitute_uuid(v, uid) for k, v in value.items()}
    return value
