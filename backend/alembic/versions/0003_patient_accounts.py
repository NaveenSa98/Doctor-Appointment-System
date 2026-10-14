"""patient accounts: a patient role, a display name, and bookings that outlive their account

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-14
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

FK = "fk_appointments_created_by_users"


def upgrade() -> None:
    # The new value is not used in this transaction, so adding it here is safe.
    op.execute("ALTER TYPE user_role ADD VALUE IF NOT EXISTS 'patient'")
    op.add_column("users", sa.Column("full_name", sa.Text(), nullable=True))

    # Deleting an account must keep the bookings (the doctor's history), so the link is cleared.
    op.drop_constraint(FK, "appointments", type_="foreignkey")
    op.create_foreign_key(FK, "appointments", "users", ["created_by"], ["id"], ondelete="SET NULL")


def downgrade() -> None:
    # Postgres cannot drop one value from an enum, so 'patient' stays in the type
    # (downgrading to base drops the whole type). Patient users are removed instead.
    op.execute(
        "UPDATE appointments SET created_by = NULL "
        "WHERE created_by IN (SELECT id FROM users WHERE role = 'patient')"
    )
    op.execute("DELETE FROM users WHERE role = 'patient'")

    op.drop_constraint(FK, "appointments", type_="foreignkey")
    op.create_foreign_key(FK, "appointments", "users", ["created_by"], ["id"])
    op.drop_column("users", "full_name")
