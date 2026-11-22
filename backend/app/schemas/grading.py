from datetime import datetime
from decimal import Decimal
from typing import Annotated, Literal
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_serializer,
    model_validator,
)

from app.schemas.academic_admin import PeriodeResponse
from app.schemas.curriculum import Payload

Score = Annotated[Decimal, Field(ge=0, le=100, max_digits=5, decimal_places=2, allow_inf_nan=False)]


class GradeItem(Payload):
    instrumen_id: UUID
    mahasiswa_id: UUID
    nilai_mentah: Score


class GradeBatch(Payload):
    items: list[GradeItem] = Field(min_length=1, max_length=2000)

    @model_validator(mode="after")
    def unique_pairs(self):
        keys = {(i.instrumen_id, i.mahasiswa_id) for i in self.items}
        if len(keys) != len(self.items):
            raise ValueError("Pasangan instrumen/mahasiswa duplikat")
        return self


class GradeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    kelas_mk_id: UUID
    instrumen_id: UUID
    mahasiswa_id: UUID
    nilai_mentah: Decimal
    waktu_input: datetime
    diubah_oleh: UUID

    @field_serializer("nilai_mentah")
    def serialize_score(self, value: Decimal):
        return format(value, ".2f")


class ReopenPeriod(Payload):
    alasan: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)]


class PeriodState(PeriodeResponse):
    ditutup_pada: datetime | None
    ditutup_oleh: UUID | None


class Attainment(BaseModel):
    jenis: Literal["Mata kuliah", "Sub-CPMK", "CPMK", "CPL"]
    id: UUID
    kode: str
    label: str
    kurikulum_id: UUID
    capaian: Decimal | None
    status: Literal["Lengkap", "Belum lengkap", "Belum siap dinilai"]
    instrumen_lengkap: int
    total_instrumen: int


class StudentAttainment(BaseModel):
    mahasiswa_id: UUID
    hasil: list[Attainment]


class ClassAverage(BaseModel):
    jenis: Literal["Mata kuliah", "Sub-CPMK", "CPMK", "CPL"]
    id: UUID
    kode: str
    label: str
    kurikulum_id: UUID
    capaian: Decimal | None
    status: Literal["Lengkap", "Belum lengkap", "Belum siap dinilai"]
    mahasiswa_lengkap: int
    total_mahasiswa: int


class ClassAttainment(BaseModel):
    kelas_mk_id: UUID
    periode_id: UUID
    peserta: list[StudentAttainment]
    rekap: list[ClassAverage]


class PersonalAttainment(BaseModel):
    mahasiswa_id: UUID
    periode_id: UUID
    tahun_akademik: str
    semester: str
    kumulatif: bool
    kelas_mk_ids: list[UUID]
    hasil: list[Attainment]
