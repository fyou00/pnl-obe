"""Academic setup is managed by Admin; no student self-enrollment payloads."""

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.curriculum import PatchPayload, Payload

Semester = Literal["Ganjil", "Genap"]
KodeKelas = Literal["A", "B", "C", "D", "E", "K"]
StatusMahasiswa = Literal["Aktif", "Cuti", "Nonaktif"]


class AngkatanCreate(Payload):
    tahun_masuk: int = Field(ge=1900, le=9998, strict=True)
    kurikulum_id: UUID


class AngkatanPatch(PatchPayload):
    tahun_masuk: int | None = Field(default=None, ge=1900, le=9998, strict=True)
    kurikulum_id: UUID | None = None


class AngkatanResponse(AngkatanCreate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    prodi_id: UUID


class PeriodeCreate(Payload):
    tahun_mulai: int = Field(ge=1900, le=9998, strict=True)
    semester: Semester


class PeriodePatch(PatchPayload):
    tahun_mulai: int | None = Field(default=None, ge=1900, le=9998, strict=True)
    semester: Semester | None = None


class PeriodeResponse(PeriodeCreate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    prodi_id: UUID
    tahun_akademik: str
    status: Literal["Dibuka", "Ditutup"]


class KelasCreate(Payload):
    angkatan_id: UUID
    kode_kelas: KodeKelas
    semester_studi: int | None = Field(default=None, ge=1, le=8, strict=True)

    @model_validator(mode="after")
    def validate_semester(self):
        if (self.kode_kelas == "K") != (self.semester_studi is None):
            raise ValueError("K wajib semester_studi null; A–E wajib semester studi 1–8")
        return self


class KelasPatch(Payload):
    kode_kelas: KodeKelas | None = None
    semester_studi: int | None = Field(default=None, ge=1, le=8, strict=True)

    @model_validator(mode="after")
    def validate_patch(self):
        if not self.model_fields_set or (
            "kode_kelas" in self.model_fields_set and self.kode_kelas is None
        ):
            raise ValueError("Isi perubahan yang valid; kode_kelas tidak boleh null")
        return self


class KelasResponse(KelasCreate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    periode_id: UUID
    tingkat: int | None
    label: str


class MahasiswaLink(Payload):
    user_id: UUID


class MahasiswaResponse(BaseModel):
    id: UUID
    angkatan_id: UUID
    nim_nidn: str
    nama: str
    aktif: bool


class RosterCreate(Payload):
    mahasiswa_id: UUID
    kelas_periode_id: UUID
    status: StatusMahasiswa


class RosterPatch(PatchPayload):
    kelas_periode_id: UUID | None = None
    status: StatusMahasiswa | None = None


class RosterResponse(RosterCreate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    periode_id: UUID
