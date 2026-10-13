"""appointments table, enums, constraints and indexes

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-13
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UUID = postgresql.UUID(as_uuid=True)
NOT_DELETED = sa.text("deleted_at IS NULL")


def upgrade() -> None:
    bind = op.get_bind()

    op.execute(
        "CREATE TYPE appointment_type AS ENUM "
        "('consultation', 'follow_up', 'check_up', 'procedure', 'vaccination')"
    )
    op.execute(
        "CREATE TYPE appointment_status AS ENUM "
        "('scheduled', 'confirmed', 'completed', 'cancelled', 'no_show')"
    )

    op.create_table(
        "appointments",
        sa.Column("id", UUID, server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("patient_name", sa.String(100), nullable=False),
        sa.Column("doctor_id", UUID, nullable=False),
        sa.Column("hospital_id", UUID, nullable=False),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "appointment_type",
            postgresql.ENUM(
                "consultation",
                "follow_up",
                "check_up",
                "procedure",
                "vaccination",
                name="appointment_type",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column(
            "status",
            postgresql.ENUM(
                "scheduled",
                "confirmed",
                "completed",
                "cancelled",
                "no_show",
                name="appointment_status",
                create_type=False,
            ),
            server_default=sa.text("'scheduled'"),
            nullable=False,
        ),
        sa.Column("created_by", UUID, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_appointments"),
        sa.ForeignKeyConstraint(
            ["doctor_id"],
            ["doctors.id"],
            name="fk_appointments_doctor_id_doctors",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["hospital_id"],
            ["hospitals.id"],
            name="fk_appointments_hospital_id_hospitals",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["doctor_id", "hospital_id"],
            ["doctor_hospitals.doctor_id", "doctor_hospitals.hospital_id"],
            name="fk_appointments_doctor_hospital",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"], ["users.id"], name="fk_appointments_created_by_users"
        ),
        sa.CheckConstraint(
            "char_length(btrim(patient_name)) >= 2",
            name=op.f("ck_appointments_patient_name_length"),
        ),
        sa.CheckConstraint(
            "date_part('minute', start_time AT TIME ZONE 'UTC') IN (0, 30) "
            "AND date_part('second', start_time AT TIME ZONE 'UTC') = 0",
            name=op.f("ck_appointments_slot_aligned"),
        ),
    )

    # One active appointment per doctor and start time, whatever the hospital.
    op.create_index(
        "uq_appointments_doctor_slot",
        "appointments",
        ["doctor_id", "start_time"],
        unique=True,
        postgresql_where=sa.text("status <> 'cancelled' AND deleted_at IS NULL"),
    )
    op.create_index(
        "ix_appointments_start_time", "appointments", ["start_time"], postgresql_where=NOT_DELETED
    )
    op.create_index(
        "ix_appointments_doctor_start",
        "appointments",
        ["doctor_id", "start_time"],
        postgresql_where=NOT_DELETED,
    )
    op.create_index(
        "ix_appointments_status_start",
        "appointments",
        ["status", "start_time"],
        postgresql_where=NOT_DELETED,
    )
    op.create_index(
        "ix_appointments_hospital_start",
        "appointments",
        ["hospital_id", "start_time"],
        postgresql_where=NOT_DELETED,
    )

    # The trigram operator class lives in whichever schema holds pg_trgm.
    extension_schema = bind.execute(
        sa.text(
            "SELECT n.nspname FROM pg_extension e JOIN pg_namespace n ON n.oid = e.extnamespace "
            "WHERE e.extname = 'pg_trgm'"
        )
    ).scalar_one()
    op.create_index(
        "ix_appointments_patient_name_trgm",
        "appointments",
        ["patient_name"],
        postgresql_using="gin",
        postgresql_ops={"patient_name": f'"{extension_schema}".gin_trgm_ops'},
    )

    op.execute("ALTER TABLE appointments ENABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    op.drop_table("appointments")
    op.execute("DROP TYPE appointment_status")
    op.execute("DROP TYPE appointment_type")
