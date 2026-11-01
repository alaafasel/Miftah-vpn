"""xray manager + device proxy selection

Revision ID: 0002_xray_manager
Revises: 73a404055473
Create Date: 2026-11-02
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0002_xray_manager"
down_revision = "73a404055473"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "xray_servers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("address", sa.String(length=255), nullable=False),
        sa.Column("port", sa.Integer(), server_default=sa.text("443"), nullable=False),
        sa.Column("agent_url", sa.String(length=255), nullable=False),
        sa.Column("agent_token", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("status", sa.String(length=16), server_default="unknown", nullable=False),
        sa.Column("xray_version", sa.String(length=64), nullable=True),
        sa.Column("config", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("config_version", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_table(
        "xray_server_users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("server_id", sa.Integer(), nullable=False),
        sa.Column("uuid_id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(length=100), nullable=True),
        sa.Column("is_enabled", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["server_id"], ["xray_servers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["uuid_id"], ["uuids.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("server_id", "uuid_id", name="uq_server_uuid"),
    )
    op.create_index(op.f("ix_xray_server_users_server_id"), "xray_server_users", ["server_id"])
    op.create_index(op.f("ix_xray_server_users_uuid_id"), "xray_server_users", ["uuid_id"])
    op.add_column("devices", sa.Column("selected_proxy_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_devices_selected_proxy", "devices", "proxies",
        ["selected_proxy_id"], ["id"], ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_devices_selected_proxy", "devices", type_="foreignkey")
    op.drop_column("devices", "selected_proxy_id")
    op.drop_index(op.f("ix_xray_server_users_uuid_id"), table_name="xray_server_users")
    op.drop_index(op.f("ix_xray_server_users_server_id"), table_name="xray_server_users")
    op.drop_table("xray_server_users")
    op.drop_table("xray_servers")
