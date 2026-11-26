from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Integer,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDPrimaryKey


class Kurikulum(UUIDPrimaryKey, Base):
    __tablename__ = "kurikulum"
    __table_args__ = (
        UniqueConstraint("prodi_id", "kode_kurikulum"),
        CheckConstraint("status IN ('Draft', 'Aktif', 'Arsip')", name="status"),
    )
    prodi_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("prodi.id", ondelete="RESTRICT"), index=True
    )
    kode_kurikulum: Mapped[str] = mapped_column(String(30))
    nama: Mapped[str] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(10), server_default=text("'Draft'"))


class MataKuliah(UUIDPrimaryKey, Base):
    __tablename__ = "mata_kuliah"
    __table_args__ = (UniqueConstraint("prodi_id", "kode_mk"),)
    prodi_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("prodi.id", ondelete="RESTRICT"), index=True
    )
    kode_mk: Mapped[str] = mapped_column(String(20))
    nama_mk: Mapped[str] = mapped_column(String(100))
    deskripsi: Mapped[str | None] = mapped_column(Text)
    aktif: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))


class KurikulumMK(UUIDPrimaryKey, Base):
    __tablename__ = "kurikulum_mk"
    __table_args__ = (
        UniqueConstraint("kurikulum_id", "mk_id"),
        CheckConstraint("sks > 0", name="sks"),
        CheckConstraint("semester BETWEEN 1 AND 8", name="semester"),
    )
    kurikulum_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("kurikulum.id", ondelete="RESTRICT"), index=True
    )
    mk_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("mata_kuliah.id", ondelete="RESTRICT"), index=True
    )
    nama_mk: Mapped[str] = mapped_column(String(100))
    sks: Mapped[int] = mapped_column(SmallInteger)
    semester: Mapped[int] = mapped_column(SmallInteger)
    deskripsi: Mapped[str | None] = mapped_column(Text)


class MasterCPL(UUIDPrimaryKey, Base):
    __tablename__ = "master_cpl"
    __table_args__ = (
        UniqueConstraint("kurikulum_id", "kode_cpl"),
        CheckConstraint("kategori IN ('S', 'KU', 'P', 'KK')", name="kategori"),
        CheckConstraint("prodi_id IS NOT NULL OR kategori IN ('S', 'KU')", name="nasional"),
    )
    kurikulum_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("kurikulum.id", ondelete="RESTRICT"), index=True
    )
    prodi_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("prodi.id", ondelete="RESTRICT"), index=True
    )
    kode_cpl: Mapped[str] = mapped_column(String(10))
    kategori: Mapped[str] = mapped_column(String(5))
    deskripsi: Mapped[str] = mapped_column(Text)


class MKCPL(Base):
    __tablename__ = "mk_cpl"
    __table_args__ = (CheckConstraint("urutan_rps > 0", name="urutan_rps"),)
    kurikulum_mk_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("kurikulum_mk.id", ondelete="CASCADE"), primary_key=True
    )
    cpl_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("master_cpl.id", ondelete="RESTRICT"), primary_key=True, index=True
    )
    urutan_rps: Mapped[int | None] = mapped_column(Integer)


class ProfilLulusan(UUIDPrimaryKey, Base):
    __tablename__ = "profil_lulusan"
    __table_args__ = (UniqueConstraint("kurikulum_id", "kode_pl"),)
    kurikulum_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("kurikulum.id", ondelete="RESTRICT"), index=True
    )
    kode_pl: Mapped[str] = mapped_column(String(10))
    nama_pl: Mapped[str] = mapped_column(String(150))
    bidang_kerja: Mapped[str | None] = mapped_column(Text)
    deskripsi: Mapped[str] = mapped_column(Text)


class PLCPL(Base):
    __tablename__ = "pl_cpl"
    profil_lulusan_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("profil_lulusan.id", ondelete="CASCADE"), primary_key=True
    )
    cpl_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("master_cpl.id", ondelete="RESTRICT"), primary_key=True, index=True
    )
