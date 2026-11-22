"""Admin assigns the campus package; students never choose their courses."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.curriculum import Payload


class Assignment(Payload):
    kelas_periode_id: UUID
    kurikulum_mk_id: UUID
    dosen_id: UUID


class ApplyPackage(Payload):
    penugasan: list[Assignment] = Field(min_length=1)

    @model_validator(mode="after")
    def unique_pairs(self):
        pairs = {(item.kelas_periode_id, item.kurikulum_mk_id) for item in self.penugasan}
        if len(pairs) != len(self.penugasan):
            raise ValueError("Setiap pasangan kelas/MK hanya boleh mempunyai satu dosen")
        return self


class LecturerPatch(Payload):
    dosen_id: UUID


class LecturerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    nim_nidn: str
    nama: str
    aktif: bool


class PackageClass(BaseModel):
    kelas_periode_id: UUID
    kode_kelas: str
    label: str
    jumlah_mahasiswa_aktif: int


class PackageCourse(BaseModel):
    kurikulum_mk_id: UUID
    mk_id: UUID
    kode_mk: str
    nama_mk: str
    sks: int


class PackagePair(BaseModel):
    kelas_periode_id: UUID
    kurikulum_mk_id: UUID
    kelas_mk_id: UUID | None
    dosen_id: UUID | None
    rancangan_id: UUID | None


class PackagePreview(BaseModel):
    periode_id: UUID
    angkatan_id: UUID
    kurikulum_id: UUID
    semester_studi: int
    kelas: list[PackageClass]
    mata_kuliah: list[PackageCourse]
    penugasan: list[PackagePair]


class PackageResult(BaseModel):
    periode_id: UUID
    angkatan_id: UUID
    kurikulum_id: UUID
    semester_studi: int
    total_kelas_mk: int
    total_peserta: int
    kelas_mk_dibuat: int
    kelas_mk_diperbarui: int
    rancangan_dibuat: int
    peserta_ditambahkan: int


class AssignmentResponse(Assignment):
    periode_id: UUID
    kelas_mk_id: UUID
    rancangan_id: UUID
