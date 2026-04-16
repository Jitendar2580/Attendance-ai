"""initial tables

Revision ID: 0001_initial_tables
Revises:
Create Date: 2026-04-14
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001_initial_tables"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "teams",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_teams_id", "teams", ["id"], unique=False)
    op.create_index("ix_teams_name", "teams", ["name"], unique=True)

    op.execute(
        """
        DO $$
        BEGIN
            CREATE TYPE user_role AS ENUM ('ADMIN', 'MANAGER', 'PLAYER');
        EXCEPTION
            WHEN duplicate_object THEN NULL;
        END $$;
        """
    )
    user_role = postgresql.ENUM("ADMIN", "MANAGER", "PLAYER", name="user_role", create_type=False)
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password", sa.String(length=255), nullable=False),
        sa.Column("role", user_role, nullable=False),
        sa.Column("team_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["team_id"], ["teams.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_index("ix_users_id", "users", ["id"], unique=False)
    op.create_index("ix_users_role", "users", ["role"], unique=False)
    op.create_index("ix_users_team_id", "users", ["team_id"], unique=False)

    op.execute(
        """
        DO $$
        BEGIN
            CREATE TYPE attendance_status AS ENUM ('TRAINING', 'GYM', 'HOSPITAL', 'LEAVE');
        EXCEPTION
            WHEN duplicate_object THEN NULL;
        END $$;
        """
    )
    attendance_status = postgresql.ENUM(
        "TRAINING", "GYM", "HOSPITAL", "LEAVE", name="attendance_status", create_type=False
    )
    op.create_table(
        "attendance",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("status", attendance_status, nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "date", name="uq_attendance_user_date"),
    )
    op.create_index("ix_attendance_id", "attendance", ["id"], unique=False)
    op.create_index("ix_attendance_user_id", "attendance", ["user_id"], unique=False)
    op.create_index("ix_attendance_date", "attendance", ["date"], unique=False)
    op.create_index("ix_attendance_status", "attendance", ["status"], unique=False)
    op.create_index("ix_attendance_date_status", "attendance", ["date", "status"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_attendance_date_status", table_name="attendance")
    op.drop_index("ix_attendance_status", table_name="attendance")
    op.drop_index("ix_attendance_date", table_name="attendance")
    op.drop_index("ix_attendance_user_id", table_name="attendance")
    op.drop_index("ix_attendance_id", table_name="attendance")
    op.drop_table("attendance")
    sa.Enum(name="attendance_status").drop(op.get_bind(), checkfirst=True)

    op.drop_index("ix_users_team_id", table_name="users")
    op.drop_index("ix_users_role", table_name="users")
    op.drop_index("ix_users_id", table_name="users")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
    sa.Enum(name="user_role").drop(op.get_bind(), checkfirst=True)

    op.drop_index("ix_teams_name", table_name="teams")
    op.drop_index("ix_teams_id", table_name="teams")
    op.drop_table("teams")
