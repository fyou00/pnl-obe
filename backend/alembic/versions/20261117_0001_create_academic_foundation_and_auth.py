"""Create academic foundation and auth

Revision ID: 20261117_0001
Revises:
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20261117_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "prodi",
        sa.Column("kode_prodi", sa.String(length=20), nullable=False),
        sa.Column("nama_prodi", sa.String(length=100), nullable=False),
        sa.Column("jenjang", sa.String(length=10), nullable=False),
        sa.Column("aktif", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_prodi")),
        sa.UniqueConstraint("kode_prodi", name=op.f("uq_prodi_kode_prodi")),
    )
    op.create_table(
        "kurikulum",
        sa.Column("prodi_id", sa.Uuid(), nullable=False),
        sa.Column("kode_kurikulum", sa.String(length=30), nullable=False),
        sa.Column("nama", sa.String(length=100), nullable=False),
        sa.Column(
            "status", sa.String(length=10), server_default=sa.text("'Draft'"), nullable=False
        ),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.CheckConstraint(
            "status IN ('Draft', 'Aktif', 'Arsip')", name=op.f("ck_kurikulum_status")
        ),
        sa.ForeignKeyConstraint(
            ["prodi_id"],
            ["prodi.id"],
            name=op.f("fk_kurikulum_prodi_id_prodi"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_kurikulum")),
        sa.UniqueConstraint("prodi_id", "kode_kurikulum", name=op.f("uq_kurikulum_prodi_id")),
    )
    op.create_index(op.f("ix_kurikulum_prodi_id"), "kurikulum", ["prodi_id"], unique=False)
    op.create_table(
        "mata_kuliah",
        sa.Column("prodi_id", sa.Uuid(), nullable=False),
        sa.Column("kode_mk", sa.String(length=20), nullable=False),
        sa.Column("nama_mk", sa.String(length=100), nullable=False),
        sa.Column("deskripsi", sa.Text(), nullable=True),
        sa.Column("aktif", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["prodi_id"],
            ["prodi.id"],
            name=op.f("fk_mata_kuliah_prodi_id_prodi"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_mata_kuliah")),
        sa.UniqueConstraint("prodi_id", "kode_mk", name=op.f("uq_mata_kuliah_prodi_id")),
    )
    op.create_index(op.f("ix_mata_kuliah_prodi_id"), "mata_kuliah", ["prodi_id"], unique=False)
    op.create_table(
        "users",
        sa.Column("prodi_id", sa.Uuid(), nullable=False),
        sa.Column("nim_nidn", sa.String(length=20), nullable=False),
        sa.Column("nama", sa.String(length=100), nullable=False),
        sa.Column("email", sa.String(length=100), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("aktif", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("token_version", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.CheckConstraint("role IN ('Admin', 'Dosen', 'Mahasiswa')", name=op.f("ck_users_role")),
        sa.CheckConstraint("token_version >= 0", name=op.f("ck_users_token_version")),
        sa.ForeignKeyConstraint(
            ["prodi_id"], ["prodi.id"], name=op.f("fk_users_prodi_id_prodi"), ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
        sa.UniqueConstraint("email", name=op.f("uq_users_email")),
        sa.UniqueConstraint("nim_nidn", name=op.f("uq_users_nim_nidn")),
    )
    op.create_index(op.f("ix_users_prodi_id"), "users", ["prodi_id"], unique=False)
    op.create_table(
        "angkatan",
        sa.Column("prodi_id", sa.Uuid(), nullable=False),
        sa.Column("tahun_masuk", sa.SmallInteger(), nullable=False),
        sa.Column("kurikulum_id", sa.Uuid(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["kurikulum_id"],
            ["kurikulum.id"],
            name=op.f("fk_angkatan_kurikulum_id_kurikulum"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["prodi_id"], ["prodi.id"], name=op.f("fk_angkatan_prodi_id_prodi"), ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_angkatan")),
        sa.UniqueConstraint("prodi_id", "tahun_masuk", name=op.f("uq_angkatan_prodi_id")),
    )
    op.create_index(op.f("ix_angkatan_kurikulum_id"), "angkatan", ["kurikulum_id"], unique=False)
    op.create_index(op.f("ix_angkatan_prodi_id"), "angkatan", ["prodi_id"], unique=False)
    op.create_table(
        "kurikulum_mk",
        sa.Column("kurikulum_id", sa.Uuid(), nullable=False),
        sa.Column("mk_id", sa.Uuid(), nullable=False),
        sa.Column("nama_mk", sa.String(length=100), nullable=False),
        sa.Column("sks", sa.SmallInteger(), nullable=False),
        sa.Column("semester", sa.SmallInteger(), nullable=False),
        sa.Column("deskripsi", sa.Text(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.CheckConstraint("semester BETWEEN 1 AND 8", name=op.f("ck_kurikulum_mk_semester")),
        sa.CheckConstraint("sks > 0", name=op.f("ck_kurikulum_mk_sks")),
        sa.ForeignKeyConstraint(
            ["kurikulum_id"],
            ["kurikulum.id"],
            name=op.f("fk_kurikulum_mk_kurikulum_id_kurikulum"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["mk_id"],
            ["mata_kuliah.id"],
            name=op.f("fk_kurikulum_mk_mk_id_mata_kuliah"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_kurikulum_mk")),
        sa.UniqueConstraint("kurikulum_id", "mk_id", name=op.f("uq_kurikulum_mk_kurikulum_id")),
    )
    op.create_index(
        op.f("ix_kurikulum_mk_kurikulum_id"), "kurikulum_mk", ["kurikulum_id"], unique=False
    )
    op.create_index(op.f("ix_kurikulum_mk_mk_id"), "kurikulum_mk", ["mk_id"], unique=False)
    op.create_table(
        "master_cpl",
        sa.Column("kurikulum_id", sa.Uuid(), nullable=False),
        sa.Column("prodi_id", sa.Uuid(), nullable=True),
        sa.Column("kode_cpl", sa.String(length=10), nullable=False),
        sa.Column("kategori", sa.String(length=5), nullable=False),
        sa.Column("deskripsi", sa.Text(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.CheckConstraint(
            "kategori IN ('S', 'KU', 'P', 'KK')", name=op.f("ck_master_cpl_kategori")
        ),
        sa.CheckConstraint(
            "prodi_id IS NOT NULL OR kategori IN ('S', 'KU')", name=op.f("ck_master_cpl_nasional")
        ),
        sa.ForeignKeyConstraint(
            ["kurikulum_id"],
            ["kurikulum.id"],
            name=op.f("fk_master_cpl_kurikulum_id_kurikulum"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["prodi_id"],
            ["prodi.id"],
            name=op.f("fk_master_cpl_prodi_id_prodi"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_master_cpl")),
        sa.UniqueConstraint("kurikulum_id", "kode_cpl", name=op.f("uq_master_cpl_kurikulum_id")),
    )
    op.create_index(
        op.f("ix_master_cpl_kurikulum_id"), "master_cpl", ["kurikulum_id"], unique=False
    )
    op.create_index(op.f("ix_master_cpl_prodi_id"), "master_cpl", ["prodi_id"], unique=False)
    op.create_table(
        "periode_akademik",
        sa.Column("prodi_id", sa.Uuid(), nullable=False),
        sa.Column("tahun_mulai", sa.SmallInteger(), nullable=False),
        sa.Column("semester", sa.String(length=6), nullable=False),
        sa.Column(
            "status", sa.String(length=7), server_default=sa.text("'Dibuka'"), nullable=False
        ),
        sa.Column("ditutup_pada", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ditutup_oleh", sa.Uuid(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.CheckConstraint(
            "semester IN ('Ganjil', 'Genap')", name=op.f("ck_periode_akademik_semester")
        ),
        sa.CheckConstraint(
            "status IN ('Dibuka', 'Ditutup')", name=op.f("ck_periode_akademik_status")
        ),
        sa.ForeignKeyConstraint(
            ["ditutup_oleh"],
            ["users.id"],
            name=op.f("fk_periode_akademik_ditutup_oleh_users"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["prodi_id"],
            ["prodi.id"],
            name=op.f("fk_periode_akademik_prodi_id_prodi"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_periode_akademik")),
        sa.UniqueConstraint(
            "prodi_id", "tahun_mulai", "semester", name=op.f("uq_periode_akademik_prodi_id")
        ),
    )
    op.create_index(
        op.f("ix_periode_akademik_ditutup_oleh"), "periode_akademik", ["ditutup_oleh"], unique=False
    )
    op.create_index(
        op.f("ix_periode_akademik_prodi_id"), "periode_akademik", ["prodi_id"], unique=False
    )
    op.create_table(
        "audit_log",
        sa.Column("aktor_id", sa.Uuid(), nullable=False),
        sa.Column("periode_id", sa.Uuid(), nullable=True),
        sa.Column("aksi", sa.String(length=50), nullable=False),
        sa.Column("entitas", sa.String(length=50), nullable=False),
        sa.Column("entitas_id", sa.Uuid(), nullable=False),
        sa.Column("alasan", sa.Text(), nullable=True),
        sa.Column("sebelum", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("sesudah", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "waktu", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["aktor_id"],
            ["users.id"],
            name=op.f("fk_audit_log_aktor_id_users"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["periode_id"],
            ["periode_akademik.id"],
            name=op.f("fk_audit_log_periode_id_periode_akademik"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_audit_log")),
    )
    op.create_index(op.f("ix_audit_log_aktor_id"), "audit_log", ["aktor_id"], unique=False)
    op.create_index(op.f("ix_audit_log_periode_id"), "audit_log", ["periode_id"], unique=False)
    op.create_index(
        "ix_audit_log_periode_waktu", "audit_log", ["periode_id", "waktu"], unique=False
    )
    op.create_table(
        "kelas_periode",
        sa.Column("periode_id", sa.Uuid(), nullable=False),
        sa.Column("angkatan_id", sa.Uuid(), nullable=False),
        sa.Column("kode_kelas", sa.CHAR(length=1), nullable=False),
        sa.Column("semester_studi", sa.SmallInteger(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.CheckConstraint(
            "(kode_kelas = 'K' AND semester_studi IS NULL) OR (kode_kelas <> 'K' AND semester_studi IS NOT NULL AND semester_studi BETWEEN 1 AND 8)",
            name=op.f("ck_kelas_periode_semester_studi"),
        ),
        sa.CheckConstraint(
            "kode_kelas IN ('A', 'B', 'C', 'D', 'E', 'K')", name=op.f("ck_kelas_periode_kode_kelas")
        ),
        sa.ForeignKeyConstraint(
            ["angkatan_id"],
            ["angkatan.id"],
            name=op.f("fk_kelas_periode_angkatan_id_angkatan"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["periode_id"],
            ["periode_akademik.id"],
            name=op.f("fk_kelas_periode_periode_id_periode_akademik"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_kelas_periode")),
        sa.UniqueConstraint(
            "periode_id", "angkatan_id", "kode_kelas", name=op.f("uq_kelas_periode_periode_id")
        ),
    )
    op.create_index(
        op.f("ix_kelas_periode_angkatan_id"), "kelas_periode", ["angkatan_id"], unique=False
    )
    op.create_index(
        op.f("ix_kelas_periode_periode_id"), "kelas_periode", ["periode_id"], unique=False
    )
    op.create_table(
        "mahasiswa",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("angkatan_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["angkatan_id"],
            ["angkatan.id"],
            name=op.f("fk_mahasiswa_angkatan_id_angkatan"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["id"], ["users.id"], name=op.f("fk_mahasiswa_id_users"), ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_mahasiswa")),
    )
    op.create_index(op.f("ix_mahasiswa_angkatan_id"), "mahasiswa", ["angkatan_id"], unique=False)
    op.create_table(
        "mk_cpl",
        sa.Column("kurikulum_mk_id", sa.Uuid(), nullable=False),
        sa.Column("cpl_id", sa.Uuid(), nullable=False),
        sa.Column("urutan_rps", sa.Integer(), nullable=True),
        sa.CheckConstraint("urutan_rps > 0", name=op.f("ck_mk_cpl_urutan_rps")),
        sa.ForeignKeyConstraint(
            ["cpl_id"],
            ["master_cpl.id"],
            name=op.f("fk_mk_cpl_cpl_id_master_cpl"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["kurikulum_mk_id"],
            ["kurikulum_mk.id"],
            name=op.f("fk_mk_cpl_kurikulum_mk_id_kurikulum_mk"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("kurikulum_mk_id", "cpl_id", name=op.f("pk_mk_cpl")),
    )
    op.create_index(op.f("ix_mk_cpl_cpl_id"), "mk_cpl", ["cpl_id"], unique=False)
    op.create_table(
        "rancangan_penilaian",
        sa.Column("periode_id", sa.Uuid(), nullable=False),
        sa.Column("kurikulum_mk_id", sa.Uuid(), nullable=False),
        sa.Column("dosen_id", sa.Uuid(), nullable=False),
        sa.Column("sumber_rancangan_id", sa.Uuid(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["dosen_id"],
            ["users.id"],
            name=op.f("fk_rancangan_penilaian_dosen_id_users"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["kurikulum_mk_id"],
            ["kurikulum_mk.id"],
            name=op.f("fk_rancangan_penilaian_kurikulum_mk_id_kurikulum_mk"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["periode_id"],
            ["periode_akademik.id"],
            name=op.f("fk_rancangan_penilaian_periode_id_periode_akademik"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["sumber_rancangan_id"],
            ["rancangan_penilaian.id"],
            name=op.f("fk_rancangan_penilaian_sumber_rancangan_id_rancangan_penilaian"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_rancangan_penilaian")),
        sa.UniqueConstraint(
            "periode_id",
            "kurikulum_mk_id",
            "dosen_id",
            name=op.f("uq_rancangan_penilaian_periode_id"),
        ),
    )
    op.create_index(
        op.f("ix_rancangan_penilaian_dosen_id"), "rancangan_penilaian", ["dosen_id"], unique=False
    )
    op.create_index(
        op.f("ix_rancangan_penilaian_kurikulum_mk_id"),
        "rancangan_penilaian",
        ["kurikulum_mk_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_rancangan_penilaian_periode_id"),
        "rancangan_penilaian",
        ["periode_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_rancangan_penilaian_sumber_rancangan_id"),
        "rancangan_penilaian",
        ["sumber_rancangan_id"],
        unique=False,
    )
    op.create_table(
        "cpmk",
        sa.Column("rancangan_id", sa.Uuid(), nullable=False),
        sa.Column("kode_cpmk", sa.String(length=20), nullable=False),
        sa.Column("deskripsi", sa.Text(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["rancangan_id"],
            ["rancangan_penilaian.id"],
            name=op.f("fk_cpmk_rancangan_id_rancangan_penilaian"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_cpmk")),
        sa.UniqueConstraint("rancangan_id", "kode_cpmk", name=op.f("uq_cpmk_rancangan_id")),
    )
    op.create_index(op.f("ix_cpmk_rancangan_id"), "cpmk", ["rancangan_id"], unique=False)
    op.create_table(
        "kelas_mk",
        sa.Column("kelas_periode_id", sa.Uuid(), nullable=False),
        sa.Column("kurikulum_mk_id", sa.Uuid(), nullable=False),
        sa.Column("rancangan_id", sa.Uuid(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["kelas_periode_id"],
            ["kelas_periode.id"],
            name=op.f("fk_kelas_mk_kelas_periode_id_kelas_periode"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["kurikulum_mk_id"],
            ["kurikulum_mk.id"],
            name=op.f("fk_kelas_mk_kurikulum_mk_id_kurikulum_mk"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["rancangan_id"],
            ["rancangan_penilaian.id"],
            name=op.f("fk_kelas_mk_rancangan_id_rancangan_penilaian"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_kelas_mk")),
        sa.UniqueConstraint(
            "kelas_periode_id", "kurikulum_mk_id", name=op.f("uq_kelas_mk_kelas_periode_id")
        ),
    )
    op.create_index(
        op.f("ix_kelas_mk_kelas_periode_id"), "kelas_mk", ["kelas_periode_id"], unique=False
    )
    op.create_index(
        op.f("ix_kelas_mk_kurikulum_mk_id"), "kelas_mk", ["kurikulum_mk_id"], unique=False
    )
    op.create_index(op.f("ix_kelas_mk_rancangan_id"), "kelas_mk", ["rancangan_id"], unique=False)
    op.create_table(
        "mahasiswa_periode",
        sa.Column("mahasiswa_id", sa.Uuid(), nullable=False),
        sa.Column("periode_id", sa.Uuid(), nullable=False),
        sa.Column("kelas_periode_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=8), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.CheckConstraint(
            "status IN ('Aktif', 'Cuti', 'Nonaktif')", name=op.f("ck_mahasiswa_periode_status")
        ),
        sa.ForeignKeyConstraint(
            ["kelas_periode_id"],
            ["kelas_periode.id"],
            name=op.f("fk_mahasiswa_periode_kelas_periode_id_kelas_periode"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["mahasiswa_id"],
            ["mahasiswa.id"],
            name=op.f("fk_mahasiswa_periode_mahasiswa_id_mahasiswa"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["periode_id"],
            ["periode_akademik.id"],
            name=op.f("fk_mahasiswa_periode_periode_id_periode_akademik"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_mahasiswa_periode")),
        sa.UniqueConstraint(
            "mahasiswa_id", "periode_id", name=op.f("uq_mahasiswa_periode_mahasiswa_id")
        ),
    )
    op.create_index(
        op.f("ix_mahasiswa_periode_kelas_periode_id"),
        "mahasiswa_periode",
        ["kelas_periode_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_mahasiswa_periode_mahasiswa_id"),
        "mahasiswa_periode",
        ["mahasiswa_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_mahasiswa_periode_periode_id"), "mahasiswa_periode", ["periode_id"], unique=False
    )
    op.create_table(
        "cpmk_cpl",
        sa.Column("cpmk_id", sa.Uuid(), nullable=False),
        sa.Column("cpl_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["cpl_id"],
            ["master_cpl.id"],
            name=op.f("fk_cpmk_cpl_cpl_id_master_cpl"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["cpmk_id"], ["cpmk.id"], name=op.f("fk_cpmk_cpl_cpmk_id_cpmk"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("cpmk_id", "cpl_id", name=op.f("pk_cpmk_cpl")),
    )
    op.create_index(op.f("ix_cpmk_cpl_cpl_id"), "cpmk_cpl", ["cpl_id"], unique=False)
    op.create_table(
        "peserta_kelas_mk",
        sa.Column("kelas_mk_id", sa.Uuid(), nullable=False),
        sa.Column("mahasiswa_id", sa.Uuid(), nullable=False),
        sa.Column("mk_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["kelas_mk_id"],
            ["kelas_mk.id"],
            name=op.f("fk_peserta_kelas_mk_kelas_mk_id_kelas_mk"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["mahasiswa_id"],
            ["mahasiswa.id"],
            name=op.f("fk_peserta_kelas_mk_mahasiswa_id_mahasiswa"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["mk_id"],
            ["mata_kuliah.id"],
            name=op.f("fk_peserta_kelas_mk_mk_id_mata_kuliah"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("kelas_mk_id", "mahasiswa_id", name=op.f("pk_peserta_kelas_mk")),
        sa.UniqueConstraint("mahasiswa_id", "mk_id", name=op.f("uq_peserta_kelas_mk_mahasiswa_id")),
    )
    op.create_index(
        op.f("ix_peserta_kelas_mk_mahasiswa_id"), "peserta_kelas_mk", ["mahasiswa_id"], unique=False
    )
    op.create_index(op.f("ix_peserta_kelas_mk_mk_id"), "peserta_kelas_mk", ["mk_id"], unique=False)
    op.create_table(
        "sub_cpmk",
        sa.Column("cpmk_id", sa.Uuid(), nullable=False),
        sa.Column("kode_sub", sa.String(length=20), nullable=False),
        sa.Column("deskripsi", sa.Text(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["cpmk_id"], ["cpmk.id"], name=op.f("fk_sub_cpmk_cpmk_id_cpmk"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_sub_cpmk")),
        sa.UniqueConstraint("cpmk_id", "kode_sub", name=op.f("uq_sub_cpmk_cpmk_id")),
    )
    op.create_index(op.f("ix_sub_cpmk_cpmk_id"), "sub_cpmk", ["cpmk_id"], unique=False)
    op.create_table(
        "instrumen_penilaian",
        sa.Column("sub_cpmk_id", sa.Uuid(), nullable=False),
        sa.Column("nama_instrumen", sa.String(length=100), nullable=False),
        sa.Column("jenis_instrumen", sa.String(length=20), nullable=False),
        sa.Column("bobot_persentase", sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.CheckConstraint(
            "jenis_instrumen IN ('Tugas', 'Kuis', 'Praktikum', 'UTS', 'UAS')",
            name=op.f("ck_instrumen_penilaian_jenis_instrumen"),
        ),
        sa.CheckConstraint(
            "bobot_persentase > 0 AND bobot_persentase <= 100",
            name=op.f("ck_instrumen_penilaian_bobot"),
        ),
        sa.ForeignKeyConstraint(
            ["sub_cpmk_id"],
            ["sub_cpmk.id"],
            name=op.f("fk_instrumen_penilaian_sub_cpmk_id_sub_cpmk"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_instrumen_penilaian")),
    )
    op.create_index(
        op.f("ix_instrumen_penilaian_sub_cpmk_id"),
        "instrumen_penilaian",
        ["sub_cpmk_id"],
        unique=False,
    )
    op.create_table(
        "nilai_mahasiswa",
        sa.Column("instrumen_id", sa.Uuid(), nullable=False),
        sa.Column("kelas_mk_id", sa.Uuid(), nullable=False),
        sa.Column("mahasiswa_id", sa.Uuid(), nullable=False),
        sa.Column("nilai_mentah", sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column(
            "waktu_input",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("diubah_oleh", sa.Uuid(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.CheckConstraint(
            "nilai_mentah BETWEEN 0 AND 100", name=op.f("ck_nilai_mahasiswa_nilai_mentah")
        ),
        sa.ForeignKeyConstraint(
            ["diubah_oleh"],
            ["users.id"],
            name=op.f("fk_nilai_mahasiswa_diubah_oleh_users"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["instrumen_id"],
            ["instrumen_penilaian.id"],
            name=op.f("fk_nilai_mahasiswa_instrumen_id_instrumen_penilaian"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["kelas_mk_id", "mahasiswa_id"],
            ["peserta_kelas_mk.kelas_mk_id", "peserta_kelas_mk.mahasiswa_id"],
            name=op.f("fk_nilai_mahasiswa_kelas_mk_id_peserta_kelas_mk"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_nilai_mahasiswa")),
        sa.UniqueConstraint(
            "instrumen_id",
            "kelas_mk_id",
            "mahasiswa_id",
            name=op.f("uq_nilai_mahasiswa_instrumen_id"),
        ),
    )
    op.create_index(
        op.f("ix_nilai_mahasiswa_diubah_oleh"), "nilai_mahasiswa", ["diubah_oleh"], unique=False
    )
    op.create_index(
        op.f("ix_nilai_mahasiswa_instrumen_id"), "nilai_mahasiswa", ["instrumen_id"], unique=False
    )
    op.create_index(
        op.f("ix_nilai_mahasiswa_kelas_mk_id"), "nilai_mahasiswa", ["kelas_mk_id"], unique=False
    )
    op.create_index(
        op.f("ix_nilai_mahasiswa_mahasiswa_id"), "nilai_mahasiswa", ["mahasiswa_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_nilai_mahasiswa_mahasiswa_id"), table_name="nilai_mahasiswa")
    op.drop_index(op.f("ix_nilai_mahasiswa_kelas_mk_id"), table_name="nilai_mahasiswa")
    op.drop_index(op.f("ix_nilai_mahasiswa_instrumen_id"), table_name="nilai_mahasiswa")
    op.drop_index(op.f("ix_nilai_mahasiswa_diubah_oleh"), table_name="nilai_mahasiswa")
    op.drop_table("nilai_mahasiswa")
    op.drop_index(op.f("ix_instrumen_penilaian_sub_cpmk_id"), table_name="instrumen_penilaian")
    op.drop_table("instrumen_penilaian")
    op.drop_index(op.f("ix_sub_cpmk_cpmk_id"), table_name="sub_cpmk")
    op.drop_table("sub_cpmk")
    op.drop_index(op.f("ix_peserta_kelas_mk_mk_id"), table_name="peserta_kelas_mk")
    op.drop_index(op.f("ix_peserta_kelas_mk_mahasiswa_id"), table_name="peserta_kelas_mk")
    op.drop_table("peserta_kelas_mk")
    op.drop_index(op.f("ix_cpmk_cpl_cpl_id"), table_name="cpmk_cpl")
    op.drop_table("cpmk_cpl")
    op.drop_index(op.f("ix_mahasiswa_periode_periode_id"), table_name="mahasiswa_periode")
    op.drop_index(op.f("ix_mahasiswa_periode_mahasiswa_id"), table_name="mahasiswa_periode")
    op.drop_index(op.f("ix_mahasiswa_periode_kelas_periode_id"), table_name="mahasiswa_periode")
    op.drop_table("mahasiswa_periode")
    op.drop_index(op.f("ix_kelas_mk_rancangan_id"), table_name="kelas_mk")
    op.drop_index(op.f("ix_kelas_mk_kurikulum_mk_id"), table_name="kelas_mk")
    op.drop_index(op.f("ix_kelas_mk_kelas_periode_id"), table_name="kelas_mk")
    op.drop_table("kelas_mk")
    op.drop_index(op.f("ix_cpmk_rancangan_id"), table_name="cpmk")
    op.drop_table("cpmk")
    op.drop_index(
        op.f("ix_rancangan_penilaian_sumber_rancangan_id"), table_name="rancangan_penilaian"
    )
    op.drop_index(op.f("ix_rancangan_penilaian_periode_id"), table_name="rancangan_penilaian")
    op.drop_index(op.f("ix_rancangan_penilaian_kurikulum_mk_id"), table_name="rancangan_penilaian")
    op.drop_index(op.f("ix_rancangan_penilaian_dosen_id"), table_name="rancangan_penilaian")
    op.drop_table("rancangan_penilaian")
    op.drop_index(op.f("ix_mk_cpl_cpl_id"), table_name="mk_cpl")
    op.drop_table("mk_cpl")
    op.drop_index(op.f("ix_mahasiswa_angkatan_id"), table_name="mahasiswa")
    op.drop_table("mahasiswa")
    op.drop_index(op.f("ix_kelas_periode_periode_id"), table_name="kelas_periode")
    op.drop_index(op.f("ix_kelas_periode_angkatan_id"), table_name="kelas_periode")
    op.drop_table("kelas_periode")
    op.drop_index("ix_audit_log_periode_waktu", table_name="audit_log")
    op.drop_index(op.f("ix_audit_log_periode_id"), table_name="audit_log")
    op.drop_index(op.f("ix_audit_log_aktor_id"), table_name="audit_log")
    op.drop_table("audit_log")
    op.drop_index(op.f("ix_periode_akademik_prodi_id"), table_name="periode_akademik")
    op.drop_index(op.f("ix_periode_akademik_ditutup_oleh"), table_name="periode_akademik")
    op.drop_table("periode_akademik")
    op.drop_index(op.f("ix_master_cpl_prodi_id"), table_name="master_cpl")
    op.drop_index(op.f("ix_master_cpl_kurikulum_id"), table_name="master_cpl")
    op.drop_table("master_cpl")
    op.drop_index(op.f("ix_kurikulum_mk_mk_id"), table_name="kurikulum_mk")
    op.drop_index(op.f("ix_kurikulum_mk_kurikulum_id"), table_name="kurikulum_mk")
    op.drop_table("kurikulum_mk")
    op.drop_index(op.f("ix_angkatan_prodi_id"), table_name="angkatan")
    op.drop_index(op.f("ix_angkatan_kurikulum_id"), table_name="angkatan")
    op.drop_table("angkatan")
    op.drop_index(op.f("ix_users_prodi_id"), table_name="users")
    op.drop_table("users")
    op.drop_index(op.f("ix_mata_kuliah_prodi_id"), table_name="mata_kuliah")
    op.drop_table("mata_kuliah")
    op.drop_index(op.f("ix_kurikulum_prodi_id"), table_name="kurikulum")
    op.drop_table("kurikulum")
    op.drop_table("prodi")
