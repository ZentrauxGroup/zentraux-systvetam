"""initial schema — crew_members, tasks, receipts

Revision ID: 0001
Revises: None
Create Date: 2026-03-24

SYSTVETAM — Central Dispatch Initial Schema
Zentraux Group LLC

Creates the three core tables. All five PostgreSQL ENUM types
(crew_status, execution_plane, task_status, task_type, receipt_type)
already exist in the production database — created by raw SQL in
the lifespan handler. This migration does NOT create or drop them.

Naming convention matches dispatch/database.py:
  pk: pk_%(table_name)s
  fk: fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s
  uq: uq_%(table_name)s_%(column_0_name)s
  ix: ix_%(column_0_label)s
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# ---------------------------------------------------------------------------
# ENUM references — these types already exist in PostgreSQL.
# create_type=False prevents Alembic from issuing CREATE TYPE.
# ---------------------------------------------------------------------------

crew_status_enum = postgresql.ENUM(
    "ACTIVE", "IDLE", "EXECUTING", "ERROR", "OFFLINE",
    name="crew_status",
    create_type=False,
)

execution_plane_enum = postgresql.ENUM(
    "cloud", "local",
    name="execution_plane",
    create_type=False,
)

task_status_enum = postgresql.ENUM(
    "NEW", "ASSIGNED", "EXECUTING", "QA_GATE", "LEVI_GATE",
    "DEPLOYING", "COMPLETE", "RECEIPTED", "FAILED",
    name="task_status",
    create_type=False,
)

task_type_enum = postgresql.ENUM(
    "STANDARD", "INTELLIGENCE_BRIEF", "BUILD_FROM_INTEL",
    "OPPORTUNITY", "GTM_CAMPAIGN", "VOICE_OUTREACH",
    "SECURITY_REVIEW", "QA_EVALUATION",
    name="task_type",
    create_type=False,
)

receipt_type_enum = postgresql.ENUM(
    "TASK_CREATED", "TASK_ASSIGNED", "TASK_COMPLETE", "TASK_RECEIPTED",
    "GATE_APPROVED", "GATE_RETURNED", "CREW_ACTIVATED", "CREW_DEACTIVATED",
    "QA_EVALUATION", "QA_PASSED", "QA_FAILED", "SYSTEM_EVENT",
    "ERROR_LOGGED", "CHANGE_REQUEST", "VENDOR_ONBOARD", "FINANCIAL_APPROVAL",
    name="receipt_type",
    create_type=False,
)


def upgrade() -> None:
    # -------------------------------------------------------------------
    # 1. crew_members — 16-member roster, status-tracked
    # -------------------------------------------------------------------
    op.create_table(
        "crew_members",
        sa.Column("id", sa.UUID(), nullable=False, default=sa.text("gen_random_uuid()")),
        sa.Column("callsign", sa.String(50), nullable=False),
        sa.Column("display_name", sa.String(100), nullable=False),
        sa.Column("role", sa.String(200), nullable=False),
        sa.Column("department", sa.String(50), nullable=False),
        sa.Column("sop_reference", sa.String(50), nullable=True),
        sa.Column("execution_plane", execution_plane_enum, nullable=False, server_default="cloud"),
        sa.Column("container_image", sa.String(200), nullable=True),
        sa.Column("container_port", sa.Integer(), nullable=True),
        sa.Column("status", crew_status_enum, nullable=False, server_default="IDLE"),
        sa.Column("container_id", sa.String(80), nullable=True),
        sa.Column("current_task_ref", sa.String(30), nullable=True),
        sa.Column("last_heartbeat", sa.DateTime(timezone=True), nullable=True),
        sa.Column("bio", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        # Constraints
        sa.PrimaryKeyConstraint("id", name="pk_crew_members"),
        sa.UniqueConstraint("callsign", name="uq_crew_members_callsign"),
    )

    # Indexes
    op.create_index("ix_crew_members_callsign", "crew_members", ["callsign"])
    op.create_index("ix_crew_members_status", "crew_members", ["status"])
    op.create_index("ix_crew_department_status", "crew_members", ["department", "status"])

    # -------------------------------------------------------------------
    # 2. tasks — state-machine-governed task lifecycle
    # -------------------------------------------------------------------
    op.create_table(
        "tasks",
        sa.Column("id", sa.UUID(), nullable=False, default=sa.text("gen_random_uuid()")),
        sa.Column("task_ref", sa.String(30), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("output", sa.Text(), nullable=True),
        sa.Column("task_type", task_type_enum, nullable=False, server_default="STANDARD"),
        sa.Column("source", sa.String(50), nullable=True),
        sa.Column("department", sa.String(50), nullable=True),
        sa.Column("assigned_to", sa.UUID(), nullable=True),
        sa.Column("requested_by", sa.String(50), nullable=False, server_default="AGT-001"),
        sa.Column("status", task_status_enum, nullable=False, server_default="NEW"),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("qa_result", sa.JSON(), nullable=True),
        sa.Column("levi_note", sa.Text(), nullable=True),
        sa.Column("intel_brief_id", sa.UUID(), nullable=True),
        sa.Column("container_id", sa.String(80), nullable=True),
        sa.Column("execution_plane", sa.String(20), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("assigned_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("executing_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("receipted_at", sa.DateTime(timezone=True), nullable=True),
        # Constraints
        sa.PrimaryKeyConstraint("id", name="pk_tasks"),
        sa.UniqueConstraint("task_ref", name="uq_tasks_task_ref"),
        sa.ForeignKeyConstraint(
            ["assigned_to"], ["crew_members.id"],
            name="fk_tasks_assigned_to_crew_members",
        ),
    )

    # Indexes
    op.create_index("ix_tasks_task_ref", "tasks", ["task_ref"])
    op.create_index("ix_tasks_status", "tasks", ["status"])
    op.create_index("ix_tasks_department", "tasks", ["department"])
    op.create_index("ix_tasks_assigned_to", "tasks", ["assigned_to"])

    # -------------------------------------------------------------------
    # 3. receipts — append-only audit trail (L0 doctrine)
    # -------------------------------------------------------------------
    op.create_table(
        "receipts",
        sa.Column("id", sa.UUID(), nullable=False, default=sa.text("gen_random_uuid()")),
        sa.Column("receipt_ref", sa.String(120), nullable=False),
        sa.Column("receipt_type", receipt_type_enum, nullable=False),
        sa.Column("task_id", sa.UUID(), nullable=True),
        sa.Column("crew_member_id", sa.UUID(), nullable=True),
        sa.Column("issued_by", sa.String(50), nullable=False, server_default="SYSTEM"),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.Column("sop_reference", sa.String(50), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        # Constraints
        sa.PrimaryKeyConstraint("id", name="pk_receipts"),
        sa.UniqueConstraint("receipt_ref", name="uq_receipts_receipt_ref"),
        sa.ForeignKeyConstraint(
            ["task_id"], ["tasks.id"],
            name="fk_receipts_task_id_tasks",
        ),
        sa.ForeignKeyConstraint(
            ["crew_member_id"], ["crew_members.id"],
            name="fk_receipts_crew_member_id_crew_members",
        ),
    )

    # Indexes
    op.create_index("ix_receipts_receipt_ref", "receipts", ["receipt_ref"])
    op.create_index("ix_receipts_receipt_type", "receipts", ["receipt_type"])
    op.create_index("ix_receipts_task_id", "receipts", ["task_id"])
    op.create_index("ix_receipts_created_at", "receipts", ["created_at"])


def downgrade() -> None:
    # Reverse order — receipts depends on tasks, tasks depends on crew_members
    op.drop_table("receipts")
    op.drop_table("tasks")
    op.drop_table("crew_members")
    # ENUMs are NOT dropped — they are managed by the lifespan handler
