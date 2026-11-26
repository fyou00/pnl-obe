"""Add profil_lulusan and pl_cpl tables

Revision ID: 20261126_0002
Revises: 20261117_0001
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20261126_0002"
down_revision: str | None = "20261117_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "profil_lulusan",
        sa.Column("kurikulum_id", sa.Uuid(), nullable=False),
        sa.Column("kode_pl", sa.String(length=10), nullable=False),
        sa.Column("nama_pl", sa.String(length=150), nullable=False),
        sa.Column("bidang_kerja", sa.Text(), nullable=True),
        sa.Column("deskripsi", sa.Text(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["kurikulum_id"],
            ["kurikulum.id"],
            name=op.f("fk_profil_lulusan_kurikulum_id_kurikulum"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_profil_lulusan")),
        sa.UniqueConstraint("kurikulum_id", "kode_pl", name=op.f("uq_profil_lulusan_kurikulum_id")),
    )
    op.create_index(
        op.f("ix_profil_lulusan_kurikulum_id"),
        "profil_lulusan",
        ["kurikulum_id"],
        unique=False,
    )
    op.create_table(
        "pl_cpl",
        sa.Column("profil_lulusan_id", sa.Uuid(), nullable=False),
        sa.Column("cpl_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["cpl_id"],
            ["master_cpl.id"],
            name=op.f("fk_pl_cpl_cpl_id_master_cpl"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["profil_lulusan_id"],
            ["profil_lulusan.id"],
            name=op.f("fk_pl_cpl_profil_lulusan_id_profil_lulusan"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("profil_lulusan_id", "cpl_id", name=op.f("pk_pl_cpl")),
    )
    op.create_index(op.f("ix_pl_cpl_cpl_id"), "pl_cpl", ["cpl_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_pl_cpl_cpl_id"), table_name="pl_cpl")
    op.drop_table("pl_cpl")
    op.drop_index(op.f("ix_profil_lulusan_kurikulum_id"), table_name="profil_lulusan")
    op.drop_table("profil_lulusan")
