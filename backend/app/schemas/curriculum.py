"""Admin payloads exclude prodi/status/parent IDs that the server owns."""

from typing import Annotated, ClassVar, Literal
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

CodeMK = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=20)]
CodeKurikulum = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=30)
]
CodeCPL = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=10)]
CodePL = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=10)]
Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
NamePL = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=150)]
Description = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
Kategori = Literal["S", "KU", "P", "KK"]
StatusKurikulum = Literal["Draft", "Aktif", "Arsip"]


class Payload(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PatchPayload(Payload):
    _nullable_fields: ClassVar[set[str]] = {"deskripsi"}

    @model_validator(mode="after")
    def validate_patch(self):
        if not self.model_fields_set:
            raise ValueError("Isi minimal satu perubahan")
        for name in self.model_fields_set:
            if getattr(self, name) is None and name not in self._nullable_fields:
                raise ValueError(f"{name} tidak boleh null")
        return self


class MKCreate(Payload):
    kode_mk: CodeMK
    nama_mk: Name
    deskripsi: str | None = None
    aktif: bool = True


class MKPatch(PatchPayload):
    kode_mk: CodeMK | None = None
    nama_mk: Name | None = None
    deskripsi: str | None = None
    aktif: bool | None = None


class MKResponse(MKCreate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    prodi_id: UUID


class KurikulumCreate(Payload):
    kode_kurikulum: CodeKurikulum
    nama: Name


class KurikulumPatch(PatchPayload):
    kode_kurikulum: CodeKurikulum | None = None
    nama: Name | None = None


class KurikulumResponse(KurikulumCreate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    prodi_id: UUID
    status: StatusKurikulum


class PaketCreate(Payload):
    mk_id: UUID
    nama_mk: Name
    sks: int = Field(gt=0, le=32767, strict=True)
    semester: int = Field(ge=1, le=8, strict=True)
    deskripsi: str | None = None


class PaketPatch(PatchPayload):
    nama_mk: Name | None = None
    sks: int | None = Field(default=None, gt=0, le=32767, strict=True)
    semester: int | None = Field(default=None, ge=1, le=8, strict=True)
    deskripsi: str | None = None


class PaketResponse(PaketCreate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    kurikulum_id: UUID


class CPLCreate(Payload):
    kode_cpl: CodeCPL
    kategori: Kategori
    deskripsi: Description
    nasional: bool = False


class CPLPatch(PatchPayload):
    kode_cpl: CodeCPL | None = None
    kategori: Kategori | None = None
    deskripsi: Description | None = None
    nasional: bool | None = None

    @model_validator(mode="after")
    def description_not_null(self):
        if "deskripsi" in self.model_fields_set and self.deskripsi is None:
            raise ValueError("deskripsi tidak boleh null")
        return self


class CPLResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    kurikulum_id: UUID
    prodi_id: UUID | None
    kode_cpl: str
    kategori: Kategori
    deskripsi: str


class Pembebanan(Payload):
    model_config = ConfigDict(extra="forbid", from_attributes=True)
    cpl_id: UUID
    urutan_rps: int | None = Field(default=None, gt=0, le=2147483647, strict=True)


class MatriksReplace(Payload):
    items: list[Pembebanan]

    @model_validator(mode="after")
    def unique_cpl(self):
        if len({item.cpl_id for item in self.items}) != len(self.items):
            raise ValueError("CPL duplikat dalam payload")
        return self


def _normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


class ProfilLulusanCreate(Payload):
    kode_pl: CodePL
    nama_pl: NamePL
    bidang_kerja: str | None = None
    deskripsi: Description

    @field_validator("bidang_kerja")
    @classmethod
    def normalize_bidang_kerja(cls, value: str | None) -> str | None:
        return _normalize_optional_text(value)


class ProfilLulusanPatch(PatchPayload):
    _nullable_fields: ClassVar[set[str]] = {"bidang_kerja"}

    kode_pl: CodePL | None = None
    nama_pl: NamePL | None = None
    bidang_kerja: str | None = None
    deskripsi: Description | None = None

    @field_validator("bidang_kerja")
    @classmethod
    def normalize_bidang_kerja(cls, value: str | None) -> str | None:
        return _normalize_optional_text(value)


class ProfilLulusanResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    kurikulum_id: UUID
    kode_pl: str
    nama_pl: str
    bidang_kerja: str | None
    deskripsi: str


class ProfilLulusanCplLink(Payload):
    model_config = ConfigDict(extra="forbid", from_attributes=True)
    cpl_id: UUID


class PlMatriksReplace(Payload):
    cpl_ids: list[UUID]

    @model_validator(mode="after")
    def unique_cpl(self):
        if len(set(self.cpl_ids)) != len(self.cpl_ids):
            raise ValueError("CPL duplikat dalam payload")
        return self


class ProfilLulusanMatrixItem(ProfilLulusanResponse):
    cpl_ids: list[UUID]


class ProfilLulusanOverviewResponse(BaseModel):
    kurikulum_id: UUID
    kode_kurikulum: str
    nama_kurikulum: str
    status: StatusKurikulum
    profil_lulusan: list[ProfilLulusanMatrixItem]
    cpl: list[CPLResponse]
