from decimal import Decimal
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from app.schemas.curriculum import Description, Name, PatchPayload, Payload

Code = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=20)]
Weight = Annotated[
    Decimal, Field(gt=0, le=100, max_digits=5, decimal_places=2, allow_inf_nan=False)
]
InstrumentKind = Literal["Tugas", "Kuis", "Praktikum", "UTS", "UAS"]


class CPLIds(Payload):
    cpl_ids: list[UUID]

    @model_validator(mode="after")
    def unique_ids(self):
        if len(set(self.cpl_ids)) != len(self.cpl_ids):
            raise ValueError("CPL duplikat dalam payload")
        return self


class CPMKCreate(Payload):
    kode_cpmk: Code
    deskripsi: Description
    cpl_ids: list[UUID] = []

    @model_validator(mode="after")
    def unique_ids(self):
        CPLIds(cpl_ids=self.cpl_ids)
        return self


class AssessmentPatch(PatchPayload):
    @model_validator(mode="after")
    def description_required(self):
        if "deskripsi" in self.model_fields_set and self.deskripsi is None:
            raise ValueError("deskripsi tidak boleh null")
        return self


class CPMKPatch(AssessmentPatch):
    kode_cpmk: Code | None = None
    deskripsi: Description | None = None
    cpl_ids: list[UUID] | None = None

    @model_validator(mode="after")
    def unique_ids(self):
        if self.cpl_ids is not None:
            CPLIds(cpl_ids=self.cpl_ids)
        return self


class SubCreate(Payload):
    kode_sub: Code
    deskripsi: Description


class SubPatch(AssessmentPatch):
    kode_sub: Code | None = None
    deskripsi: Description | None = None


class InstrumentCreate(Payload):
    nama_instrumen: Name
    jenis_instrumen: InstrumentKind
    bobot_persentase: Weight


class InstrumentPatch(PatchPayload):
    nama_instrumen: Name | None = None
    jenis_instrumen: InstrumentKind | None = None
    bobot_persentase: Weight | None = None


class InstrumentResponse(InstrumentCreate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    sub_cpmk_id: UUID


class SubResponse(SubCreate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    cpmk_id: UUID
    instrumen: list[InstrumentResponse]


class CPMKResponse(BaseModel):
    id: UUID
    rancangan_id: UUID
    kode_cpmk: str
    deskripsi: str
    cpl_ids: list[UUID]
    sub_cpmk: list[SubResponse]


class DesignClass(BaseModel):
    kelas_mk_id: UUID
    kelas_periode_id: UUID
    label: str


class AvailableCPL(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    kode_cpl: str
    kategori: str
    deskripsi: str
    prodi_id: UUID | None


class DesignSummary(BaseModel):
    id: UUID
    periode_id: UUID
    tahun_akademik: str
    semester: Literal["Ganjil", "Genap"]
    kurikulum_mk_id: UUID
    dosen_id: UUID
    sumber_rancangan_id: UUID | None
    total_bobot: Decimal
    siap_dinilai: bool
    boleh_input_nilai: bool
    alasan_belum_siap: list[str]
    sudah_ada_nilai: bool
    periode_ditutup: bool
    struktur_terkunci: bool
    alasan_terkunci: str | None
    kelas_pengguna: list[DesignClass]


class DesignDetail(DesignSummary):
    cpl_tersedia: list[AvailableCPL]
    cpmk: list[CPMKResponse]


class CopyDesign(Payload):
    sumber_rancangan_id: UUID
