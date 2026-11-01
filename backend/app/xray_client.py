"""HTTP client for the MIFTAH Xray Manager agent.

The agent runs on the Xray server and exposes a small authenticated API.
The control plane never needs shell access to the Xray host.
"""
import httpx

from .models import XrayServer

TIMEOUT = 20.0


class AgentError(Exception):
    pass


def _base(server: XrayServer) -> str:
    return server.agent_url.rstrip("/")


def _headers(server: XrayServer) -> dict:
    return {"X-Agent-Token": server.agent_token}


def _request(server: XrayServer, method: str, path: str, **kwargs) -> dict:
    try:
        with httpx.Client(timeout=TIMEOUT, verify=True) as client:
            r = client.request(
                method, _base(server) + path, headers=_headers(server), **kwargs
            )
    except httpx.HTTPError as exc:
        raise AgentError(f"agent unreachable: {exc}") from exc
    if r.status_code >= 400:
        try:
            detail = r.json().get("detail")
        except Exception:
            detail = r.text[:300]
        raise AgentError(f"agent error {r.status_code}: {detail}")
    try:
        return r.json()
    except Exception as exc:
        raise AgentError("agent returned invalid JSON") from exc


def health(server: XrayServer) -> dict:
    return _request(server, "GET", "/health")


def status(server: XrayServer) -> dict:
    return _request(server, "GET", "/status")


def validate(server: XrayServer, config: dict) -> dict:
    return _request(server, "POST", "/config/validate", json={"config": config})


def apply_config(server: XrayServer, config: dict) -> dict:
    return _request(server, "POST", "/config/apply", json={"config": config})


def sync_users(server: XrayServer, users: list[dict]) -> dict:
    return _request(server, "POST", "/users/sync", json={"users": users})


def restart(server: XrayServer) -> dict:
    return _request(server, "POST", "/service/restart")
