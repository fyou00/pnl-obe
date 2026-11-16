from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, Uuid, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDPrimaryKey


class AuditLog(UUIDPrimaryKey, Base):
    __tablename__ = "audit_log"
    __table_args__ = (Index("ix_audit_log_periode_waktu", "periode_id", "waktu"),)
    aktor_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    periode_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("periode_akademik.id", ondelete="RESTRICT"), index=True
    )
    aksi: Mapped[str] = mapped_column(String(50))
    entitas: Mapped[str] = mapped_column(String(50))
    entitas_id: Mapped[UUID] = mapped_column(Uuid)
    alasan: Mapped[str | None] = mapped_column(Text)
    sebelum: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    sesudah: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    waktu: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
