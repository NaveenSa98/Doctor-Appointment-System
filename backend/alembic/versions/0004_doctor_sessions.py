"""weekly doctor sessions and single-day exclusions

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-15
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UUID = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    op.create_table(
        "doctor_sessions",
        sa.Column("id", UUID, server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("doctor_id", UUID, nullable=False),
        sa.Column("hospital_id", UUID, nullable=False),
        sa.Column("weekday", sa.Integer(), nullable=False),
        sa.Column("start_time", sa.Time(), nullable=False),
        sa.Column("end_time", sa.Time(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_doctor_sessions")),
        sa.ForeignKeyConstraint(
            ["doctor_id"],
            ["doctors.id"],
            name=op.f("fk_doctor_sessions_doctor_id_doctors"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["hospital_id"],
            ["hospitals.id"],
            name=op.f("fk_doctor_sessions_hospital_id_hospitals"),
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            "weekday BETWEEN 0 AND 6", name=op.f("ck_doctor_sessions_weekday_range")
        ),
        sa.CheckConstraint(
            "end_time > start_time", name=op.f("ck_doctor_sessions_ends_after_start")
        ),
        sa.CheckConstraint(
            "date_part('minute', start_time) IN (0, 30)"
            " AND date_part('minute', end_time) IN (0, 30)"
            " AND date_part('second', start_time) = 0 AND date_part('second', end_time) = 0",
            name=op.f("ck_doctor_sessions_half_hour_aligned"),
        ),
    )
    op.create_index(
        "ix_doctor_sessions_doctor_weekday", "doctor_sessions", ["doctor_id", "weekday"]
    )

    op.create_table(
        "session_exclusions",
        sa.Column("id", UUID, server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("session_id", UUID, nullable=False),
        sa.Column("on_date", sa.Date(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_session_exclusions")),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["doctor_sessions.id"],
            name=op.f("fk_session_exclusions_session_id_doctor_sessions"),
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint("session_id", "on_date", name="uq_session_exclusions_day"),
    )

    # Same as the other tables: close Supabase's public REST door; the app's role bypasses RLS.
    for table in ("doctor_sessions", "session_exclusions"):
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    op.drop_table("session_exclusions")
    op.drop_index("ix_doctor_sessions_doctor_weekday", table_name="doctor_sessions")
    op.drop_table("doctor_sessions")
