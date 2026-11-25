"""Pydantic response schemas for audit log, prodi/cross-class reports, and exports."""

from datetime import datetime
from decimal import Decimal
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_serializer

from app.schemas.grading import ClassAverage


class AuditLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    aktor_id: UUID
    aktor_nama: str
    aktor_role: str
    periode_id: UUID | None
    aksi: str
    entitas: str
    entitas_id: UUID
    alasan: str | None
    sebelum: dict[str, Any] | None
    sesudah: dict[str, Any] | None
    waktu: datetime


class ProdiClassSummary(BaseModel):
    kelas_mk_id: UUID
    kelas: str
    kode_mk: str
    nama_mk: str
    sks: int
    semester: int
    dosen_id: UUID
    dosen_nama: str
    rancangan_id: UUID
    siap_dinilai: bool
    total_bobot: Decimal
    total_mahasiswa: int
    mahasiswa_lengkap: int
    status: Literal["Lengkap", "Belum lengkap", "Belum siap dinilai"]
    capaian_mk: Decimal | None
    capaian_cpl: list[ClassAverage]

    @field_serializer("total_bobot")
    def serialize_weight(self, value: Decimal) -> str:
        return format(value, ".2f")


class ProdiReportResponse(BaseModel):
    prodi_kode: str
    prodi_nama: str
    periode_id: UUID
    tahun_akademik: str
    semester: str
    status_periode: str
    kurikulum_id: UUID
    kode_kurikulum: str
    nama_kurikulum: str
    semester_filter: int | None
    total_kelas_mk: int
    total_peserta: int
    total_peserta_lengkap: int
    total_audit_periode: int
    rekap_cpl: list[ClassAverage]
    kelas: list[ProdiClassSummary]


class CrossClassReportResponse(BaseModel):
    periode_id: UUID
    tahun_akademik: str
    semester: str
    kurikulum_id: UUID
    kode_kurikulum: str
    kelas_mk_ids: list[UUID]
    kelas_labels: list[str]
    rekap: list[ClassAverage]
