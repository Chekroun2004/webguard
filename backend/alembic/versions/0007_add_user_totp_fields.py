"""add user totp fields

Revision ID: 0007
Revises: 0006
Create Date: 2026-05-27
"""
from alembic import op
import sqlalchemy as sa

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("totp_secret_encrypted", sa.Text(), nullable=True))
    op.add_column(
        "users",
        sa.Column(
            "totp_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.add_column(
        "users",
        sa.Column("totp_confirmed_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "totp_confirmed_at")
    op.drop_column("users", "totp_enabled")
    op.drop_column("users", "totp_secret_encrypted")
