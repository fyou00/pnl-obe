"""Pydantic response schemas for audit log, prodi/cross-class reports, and exports."""

from datetime import datetime
from decimal import Decimal
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_serializer

from app.schemas.grading import Attainment, ClassAverage


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


class StudentPeriodResponse(BaseModel):
    periode_id: UUID
    tahun_mulai: int
    tahun_akademik: str
    semester: str
    status_periode: Literal["Dibuka", "Ditutup"]
    kelas_periode_id: UUID
    kode_kelas: str
    tingkat: int | None
    semester_studi: int | None
    kelas: str
    status_mahasiswa: Literal["Aktif", "Cuti", "Nonaktif"]
    prodi_kode: str
    prodi_nama: str
    kurikulum_id: UUID
    kode_kurikulum: str
    nama_kurikulum: str
    tahun_masuk: int
    jumlah_kelas_mk: int


class StudentInstrumentScore(BaseModel):
    instrumen_id: UUID
    nama_instrumen: str
    bobot_persentase: Decimal
    sub_cpmk_id: UUID
    kode_sub: str
    deskripsi_sub: str
    cpmk_id: UUID
    kode_cpmk: str
    deskripsi_cpmk: str
    cpl_kodes: list[str]
    nilai_mentah: Decimal | None
    status: Literal["Sudah diinput", "Belum diinput"]
    waktu_input: datetime | None

    @field_serializer("bobot_persentase")
    def serialize_weight(self, value: Decimal) -> str:
        return format(value, ".2f")

    @field_serializer("nilai_mentah")
    def serialize_score(self, value: Decimal | None) -> str | None:
        return format(value, ".2f") if value is not None else None


class StudentCourseDetailResponse(BaseModel):
    kelas_mk_id: UUID
    periode_id: UUID
    tahun_akademik: str
    semester: str
    status_periode: Literal["Dibuka", "Ditutup"]
    kelas: str
    kode_mk: str
    nama_mk: str
    sks: int
    semester_mk: int
    dosen_nama: str
    siap_dinilai: bool
    total_bobot: Decimal
    instrumen: list[StudentInstrumentScore]
    hasil: list[Attainment]

    @field_serializer("total_bobot")
    def serialize_total_weight(self, value: Decimal) -> str:
        return format(value, ".2f")
