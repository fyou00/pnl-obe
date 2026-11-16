from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDPrimaryKey


class CPMK(UUIDPrimaryKey, Base):
    __tablename__ = "cpmk"
    __table_args__ = (UniqueConstraint("rancangan_id", "kode_cpmk"),)
    rancangan_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("rancangan_penilaian.id", ondelete="CASCADE"), index=True
    )
    kode_cpmk: Mapped[str] = mapped_column(String(20))
    deskripsi: Mapped[str] = mapped_column(Text)


class CPMKCPL(Base):
    __tablename__ = "cpmk_cpl"
    cpmk_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("cpmk.id", ondelete="CASCADE"), primary_key=True
    )
    cpl_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("master_cpl.id", ondelete="RESTRICT"), primary_key=True, index=True
    )


class SubCPMK(UUIDPrimaryKey, Base):
    __tablename__ = "sub_cpmk"
    __table_args__ = (UniqueConstraint("cpmk_id", "kode_sub"),)
    cpmk_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("cpmk.id", ondelete="CASCADE"), index=True
    )
    kode_sub: Mapped[str] = mapped_column(String(20))
    deskripsi: Mapped[str] = mapped_column(Text)


class InstrumenPenilaian(UUIDPrimaryKey, Base):
    __tablename__ = "instrumen_penilaian"
    __table_args__ = (
        CheckConstraint(
            "jenis_instrumen IN ('Tugas', 'Kuis', 'Praktikum', 'UTS', 'UAS')",
            name="jenis_instrumen",
        ),
        CheckConstraint("bobot_persentase > 0 AND bobot_persentase <= 100", name="bobot"),
    )
    sub_cpmk_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("sub_cpmk.id", ondelete="CASCADE"), index=True
    )
    nama_instrumen: Mapped[str] = mapped_column(String(100))
    jenis_instrumen: Mapped[str] = mapped_column(String(20))
    bobot_persentase: Mapped[Decimal] = mapped_column(Numeric(5, 2))


class NilaiMahasiswa(UUIDPrimaryKey, Base):
    __tablename__ = "nilai_mahasiswa"
    __table_args__ = (
        ForeignKeyConstraint(
            ["kelas_mk_id", "mahasiswa_id"],
            ["peserta_kelas_mk.kelas_mk_id", "peserta_kelas_mk.mahasiswa_id"],
            ondelete="RESTRICT",
        ),
        UniqueConstraint("instrumen_id", "kelas_mk_id", "mahasiswa_id"),
        CheckConstraint("nilai_mentah BETWEEN 0 AND 100", name="nilai_mentah"),
    )
    instrumen_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("instrumen_penilaian.id", ondelete="RESTRICT"), index=True
    )
    kelas_mk_id: Mapped[UUID] = mapped_column(Uuid, index=True)
    mahasiswa_id: Mapped[UUID] = mapped_column(Uuid, index=True)
    nilai_mentah: Mapped[Decimal] = mapped_column(Numeric(5, 2))
    waktu_input: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    diubah_oleh: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
