"""add attendance image path

Revision ID: 0002_add_attendance_image_path
Revises: 0001_initial_tables
Create Date: 2026-04-15
"""

from alembic import op
import sqlalchemy as sa

revision = "0002_add_attendance_image_path"
down_revision = "0001_initial_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "attendance",
        sa.Column("image_path", sa.String(length=255), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("attendance", "image_path")
