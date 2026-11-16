from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    CHAR,
    CheckConstraint,
    DateTime,
    ForeignKey,
    SmallInteger,
    String,
    UniqueConstraint,
    Uuid,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDPrimaryKey


class PeriodeAkademik(UUIDPrimaryKey, Base):
    __tablename__ = "periode_akademik"
    __table_args__ = (
        UniqueConstraint("prodi_id", "tahun_mulai", "semester"),
        CheckConstraint("semester IN ('Ganjil', 'Genap')", name="semester"),
        CheckConstraint("status IN ('Dibuka', 'Ditutup')", name="status"),
    )
    prodi_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("prodi.id", ondelete="RESTRICT"), index=True
    )
    tahun_mulai: Mapped[int] = mapped_column(SmallInteger)
    semester: Mapped[str] = mapped_column(String(6))
    status: Mapped[str] = mapped_column(String(7), server_default=text("'Dibuka'"))
    ditutup_pada: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ditutup_oleh: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )

    @property
    def tahun_akademik(self) -> str:
        return f"{self.tahun_mulai}/{self.tahun_mulai + 1}"


class KelasPeriode(UUIDPrimaryKey, Base):
    __tablename__ = "kelas_periode"
    __table_args__ = (
        UniqueConstraint("periode_id", "angkatan_id", "kode_kelas"),
        CheckConstraint("kode_kelas IN ('A', 'B', 'C', 'D', 'E', 'K')", name="kode_kelas"),
        CheckConstraint(
            "(kode_kelas = 'K' AND semester_studi IS NULL) OR (kode_kelas <> 'K' AND semester_studi IS NOT NULL AND semester_studi BETWEEN 1 AND 8)",
            name="semester_studi",
        ),
    )
    periode_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("periode_akademik.id", ondelete="RESTRICT"), index=True
    )
    angkatan_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("angkatan.id", ondelete="RESTRICT"), index=True
    )
    kode_kelas: Mapped[str] = mapped_column(CHAR(1))
    semester_studi: Mapped[int | None] = mapped_column(SmallInteger)

    @property
    def tingkat(self) -> int | None:
        return (self.semester_studi + 1) // 2 if self.semester_studi is not None else None


class MahasiswaPeriode(UUIDPrimaryKey, Base):
    __tablename__ = "mahasiswa_periode"
    __table_args__ = (
        UniqueConstraint("mahasiswa_id", "periode_id"),
        CheckConstraint("status IN ('Aktif', 'Cuti', 'Nonaktif')", name="status"),
    )
    mahasiswa_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("mahasiswa.id", ondelete="RESTRICT"), index=True
    )
    periode_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("periode_akademik.id", ondelete="RESTRICT"), index=True
    )
    kelas_periode_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("kelas_periode.id", ondelete="RESTRICT"), index=True
    )
    status: Mapped[str] = mapped_column(String(8))


class RancanganPenilaian(UUIDPrimaryKey, Base):
    __tablename__ = "rancangan_penilaian"
    __table_args__ = (UniqueConstraint("periode_id", "kurikulum_mk_id", "dosen_id"),)
    periode_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("periode_akademik.id", ondelete="RESTRICT"), index=True
    )
    kurikulum_mk_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("kurikulum_mk.id", ondelete="RESTRICT"), index=True
    )
    dosen_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    sumber_rancangan_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("rancangan_penilaian.id", ondelete="RESTRICT"), index=True
    )


class KelasMK(UUIDPrimaryKey, Base):
    __tablename__ = "kelas_mk"
    __table_args__ = (UniqueConstraint("kelas_periode_id", "kurikulum_mk_id"),)
    kelas_periode_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("kelas_periode.id", ondelete="RESTRICT"), index=True
    )
    kurikulum_mk_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("kurikulum_mk.id", ondelete="RESTRICT"), index=True
    )
    rancangan_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("rancangan_penilaian.id", ondelete="RESTRICT"), index=True
    )


class PesertaKelasMK(Base):
    __tablename__ = "peserta_kelas_mk"
    __table_args__ = (UniqueConstraint("mahasiswa_id", "mk_id"),)
    kelas_mk_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("kelas_mk.id", ondelete="RESTRICT"), primary_key=True
    )
    mahasiswa_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("mahasiswa.id", ondelete="RESTRICT"), primary_key=True, index=True
    )
    mk_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("mata_kuliah.id", ondelete="RESTRICT"), index=True
    )
