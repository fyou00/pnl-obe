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


class Prodi(UUIDPrimaryKey, Base):
    __tablename__ = "prodi"
    kode_prodi: Mapped[str] = mapped_column(String(20), unique=True)
    nama_prodi: Mapped[str] = mapped_column(String(100))
    jenjang: Mapped[str] = mapped_column(String(10))
    aktif: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))


class User(UUIDPrimaryKey, Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("role IN ('Admin', 'Dosen', 'Mahasiswa')", name="role"),
        CheckConstraint("token_version >= 0", name="token_version"),
    )
    prodi_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("prodi.id", ondelete="RESTRICT"), index=True
    )
    nim_nidn: Mapped[str] = mapped_column(String(20), unique=True)
    nama: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(100), unique=True)
    role: Mapped[str] = mapped_column(String(20))
    password_hash: Mapped[str] = mapped_column(Text)
    aktif: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))
    token_version: Mapped[int] = mapped_column(Integer, server_default=text("0"))


class Angkatan(UUIDPrimaryKey, Base):
    __tablename__ = "angkatan"
    __table_args__ = (UniqueConstraint("prodi_id", "tahun_masuk"),)
    prodi_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("prodi.id", ondelete="RESTRICT"), index=True
    )
    tahun_masuk: Mapped[int] = mapped_column(SmallInteger)
    kurikulum_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("kurikulum.id", ondelete="RESTRICT"), index=True
    )


class Mahasiswa(Base):
    __tablename__ = "mahasiswa"
    id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT"), primary_key=True
    )
    angkatan_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("angkatan.id", ondelete="RESTRICT"), index=True
    )
