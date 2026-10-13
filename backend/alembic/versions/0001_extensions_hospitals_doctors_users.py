"""pg_trgm, hospitals, doctors, doctor_hospitals, users

Revision ID: 0001
Revises:
Create Date: 2026-10-13
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UUID = postgresql.UUID(as_uuid=True)
NOW = sa.text("now()")
NEW_ID = sa.text("gen_random_uuid()")


def upgrade() -> None:
    bind = op.get_bind()

    # Supabase keeps extensions in the "extensions" schema; plain Postgres uses the default.
    has_extensions_schema = bind.execute(
        sa.text("SELECT 1 FROM pg_namespace WHERE nspname = 'extensions'")
    ).scalar()
    if has_extensions_schema:
        op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm WITH SCHEMA extensions")
    else:
        op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    op.execute("CREATE TYPE user_role AS ENUM ('admin', 'doctor')")

    op.create_table(
        "hospitals",
        sa.Column("id", UUID, server_default=NEW_ID, nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_hospitals"),
    )
    op.create_index("uq_hospitals_name_lower", "hospitals", [sa.text("lower(name)")], unique=True)

    op.create_table(
        "doctors",
        sa.Column("id", UUID, server_default=NEW_ID, nullable=False),
        sa.Column("full_name", sa.Text(), nullable=False),
        sa.Column("specialty", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_doctors"),
    )

    op.create_table(
        "doctor_hospitals",
        sa.Column("doctor_id", UUID, nullable=False),
        sa.Column("hospital_id", UUID, nullable=False),
        sa.PrimaryKeyConstraint("doctor_id", "hospital_id", name="pk_doctor_hospitals"),
        sa.ForeignKeyConstraint(
            ["doctor_id"],
            ["doctors.id"],
            name="fk_doctor_hospitals_doctor_id_doctors",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["hospital_id"],
            ["hospitals.id"],
            name="fk_doctor_hospitals_hospital_id_hospitals",
            ondelete="RESTRICT",
        ),
    )
    op.create_index(
        "ix_doctor_hospitals_hospital", "doctor_hospitals", ["hospital_id", "doctor_id"]
    )

    op.create_table(
        "users",
        sa.Column("id", UUID, server_default=NEW_ID, nullable=False),
        sa.Column("email", sa.Text(), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column(
            "role",
            postgresql.ENUM("admin", "doctor", name="user_role", create_type=False),
            nullable=False,
        ),
        sa.Column("doctor_id", UUID, nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_users"),
        sa.ForeignKeyConstraint(
            ["doctor_id"], ["doctors.id"], name="fk_users_doctor_id_doctors", ondelete="RESTRICT"
        ),
        sa.UniqueConstraint("doctor_id", name="uq_users_doctor_id"),
        sa.CheckConstraint(
            "role <> 'doctor' OR doctor_id IS NOT NULL",
            name=op.f("ck_users_doctor_role_has_doctor"),
        ),
    )
    op.create_index("uq_users_email_lower", "users", [sa.text("lower(email)")], unique=True)

    # Supabase exposes public tables through its REST API. Enabling row level security
    # with no policies closes that door; the app's own database role bypasses RLS.
    for table in ("alembic_version", "hospitals", "doctors", "doctor_hospitals", "users"):
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    # pg_trgm is shared by the whole database, so it is left in place.
    op.drop_table("users")
    op.drop_table("doctor_hospitals")
    op.drop_table("doctors")
    op.drop_table("hospitals")
    op.execute("DROP TYPE user_role")
