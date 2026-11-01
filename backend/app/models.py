import uuid as uuidlib
from datetime import datetime
from sqlalchemy import Boolean, DateTime, ForeignKey, Index
from sqlalchemy import Integer, String, Text, UniqueConstraint
from sqlalchemy import func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .db import Base

TS = DateTime(timezone=True)


class AdminUser(Base):
    __tablename__ = "admin_users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))
    created_at: Mapped[datetime] = mapped_column(TS, server_default=func.now())
    last_login_at: Mapped[datetime | None] = mapped_column(TS)


class XrayUuid(Base):
    __tablename__ = "uuids"

    id: Mapped[int] = mapped_column(primary_key=True)
    value: Mapped[uuidlib.UUID] = mapped_column(UUID(as_uuid=True), unique=True)
    label: Mapped[str | None] = mapped_column(String(100))
    is_active: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))
    created_at: Mapped[datetime] = mapped_column(TS, server_default=func.now())

    licenses: Mapped[list["License"]] = relationship(back_populates="xray_uuid")


class License(Base):
    __tablename__ = "licenses"

    id: Mapped[int] = mapped_column(primary_key=True)
    code_hash: Mapped[str] = mapped_column(String(64), unique=True)
    uuid_id: Mapped[int] = mapped_column(ForeignKey("uuids.id", ondelete="RESTRICT"), index=True)
    status: Mapped[str] = mapped_column(String(16), server_default="active")
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(TS, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(TS, server_default=func.now(), onupdate=func.now())

    xray_uuid: Mapped["XrayUuid"] = relationship(back_populates="licenses")
    subscriptions: Mapped[list["Subscription"]] = relationship(back_populates="license")
    devices: Mapped[list["Device"]] = relationship(back_populates="license")


class Subscription(Base):
    __tablename__ = "subscriptions"

    id: Mapped[int] = mapped_column(primary_key=True)
    license_id: Mapped[int] = mapped_column(ForeignKey("licenses.id", ondelete="CASCADE"), index=True)
    starts_at: Mapped[datetime] = mapped_column(TS)
    ends_at: Mapped[datetime] = mapped_column(TS)
    status: Mapped[str] = mapped_column(String(16), server_default="active")
    created_at: Mapped[datetime] = mapped_column(TS, server_default=func.now())

    license: Mapped["License"] = relationship(back_populates="subscriptions")


class Device(Base):
    __tablename__ = "devices"
    __table_args__ = (
        Index(
            "uq_devices_one_active_per_license",
            "license_id",
            unique=True,
            postgresql_where=text("is_active"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    license_id: Mapped[int] = mapped_column(ForeignKey("licenses.id", ondelete="CASCADE"), index=True)
    public_key: Mapped[str] = mapped_column(Text)
    key_fingerprint: Mapped[str] = mapped_column(String(64), index=True)
    model: Mapped[str | None] = mapped_column(String(100))
    is_active: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))
    bound_at: Mapped[datetime] = mapped_column(TS, server_default=func.now())
    last_seen_at: Mapped[datetime | None] = mapped_column(TS)
    unbound_at: Mapped[datetime | None] = mapped_column(TS)
    selected_proxy_id: Mapped[int | None] = mapped_column(
        ForeignKey("proxies.id", ondelete="SET NULL")
    )

    license: Mapped["License"] = relationship(back_populates="devices")


class XrayConfig(Base):
    __tablename__ = "xray_configs"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    draft: Mapped[dict] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(TS, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(TS, server_default=func.now(), onupdate=func.now())


class ConfigVersion(Base):
    __tablename__ = "config_versions"
    __table_args__ = (
        UniqueConstraint("config_id", "version", name="uq_config_version"),
        Index(
            "uq_one_current_version_per_config",
            "config_id",
            unique=True,
            postgresql_where=text("is_current"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    config_id: Mapped[int] = mapped_column(ForeignKey("xray_configs.id", ondelete="CASCADE"))
    version: Mapped[int] = mapped_column(Integer)
    content: Mapped[dict] = mapped_column(JSONB)
    note: Mapped[str | None] = mapped_column(Text)
    is_current: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    created_by: Mapped[int | None] = mapped_column(ForeignKey("admin_users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(TS, server_default=func.now())


class Proxy(Base):
    __tablename__ = "proxies"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    address: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))
    sort_order: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    created_at: Mapped[datetime] = mapped_column(TS, server_default=func.now())


class LicenseProxyAccess(Base):
    __tablename__ = "license_proxy_access"

    license_id: Mapped[int] = mapped_column(ForeignKey("licenses.id", ondelete="CASCADE"), primary_key=True)
    proxy_id: Mapped[int] = mapped_column(ForeignKey("proxies.id", ondelete="CASCADE"), primary_key=True)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    admin_id: Mapped[int | None] = mapped_column(ForeignKey("admin_users.id", ondelete="SET NULL"))
    action: Mapped[str] = mapped_column(String(64), index=True)
    entity_type: Mapped[str | None] = mapped_column(String(64))
    entity_id: Mapped[str | None] = mapped_column(String(64))
    details: Mapped[dict | None] = mapped_column(JSONB)
    ip: Mapped[str | None] = mapped_column(String(45))
    created_at: Mapped[datetime] = mapped_column(TS, server_default=func.now(), index=True)


class XrayServer(Base):
    __tablename__ = "xray_servers"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    address: Mapped[str] = mapped_column(String(255))
    port: Mapped[int] = mapped_column(Integer, server_default=text("443"))
    agent_url: Mapped[str] = mapped_column(String(255))
    agent_token: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))
    status: Mapped[str] = mapped_column(String(16), server_default="unknown")
    xray_version: Mapped[str | None] = mapped_column(String(64))
    config: Mapped[dict | None] = mapped_column(JSONB)
    config_version: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    last_checked_at: Mapped[datetime | None] = mapped_column(TS)
    created_at: Mapped[datetime] = mapped_column(TS, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(TS, server_default=func.now(), onupdate=func.now())

    users: Mapped[list["XrayServerUser"]] = relationship(back_populates="server")


class XrayServerUser(Base):
    __tablename__ = "xray_server_users"
    __table_args__ = (
        UniqueConstraint("server_id", "uuid_id", name="uq_server_uuid"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    server_id: Mapped[int] = mapped_column(
        ForeignKey("xray_servers.id", ondelete="CASCADE"), index=True
    )
    uuid_id: Mapped[int] = mapped_column(
        ForeignKey("uuids.id", ondelete="CASCADE"), index=True
    )
    email: Mapped[str | None] = mapped_column(String(100))
    is_enabled: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))
    created_at: Mapped[datetime] = mapped_column(TS, server_default=func.now())

    server: Mapped["XrayServer"] = relationship(back_populates="users")
    xray_uuid: Mapped["XrayUuid"] = relationship()
