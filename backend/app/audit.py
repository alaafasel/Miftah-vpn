from sqlalchemy.orm import Session

from .models import AuditLog


def write_audit(
    db: Session,
    admin_id: int | None,
    action: str,
    entity_type: str | None = None,
    entity_id=None,
    details: dict | None = None,
    ip: str | None = None,
) -> None:
    eid = str(entity_id) if entity_id is not None else None
    db.add(
        AuditLog(
            admin_id=admin_id,
            action=action,
            entity_type=entity_type,
            entity_id=eid,
            details=details,
            ip=ip,
        )
    )
