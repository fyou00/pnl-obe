from typing import Annotated, Literal
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

from app.schemas.auth import Role

ManageableRole = Literal["Dosen", "Mahasiswa"]
NimNidn = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=20)]
NamaUser = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]


def validate_utf8_password(value: str) -> str:
    raw = value.encode("utf-8")
    if not 12 <= len(raw) <= 72:
        raise ValueError("Kata sandi harus 12–72 byte UTF-8")
    return value


class UserCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nim_nidn: NimNidn
    nama: NamaUser
    email: EmailStr
    role: ManageableRole
    password: str
    aktif: bool = True
    angkatan_id: UUID | None = None

    @field_validator("email", mode="after")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> str:
        return str(value).strip().lower()

    @field_validator("password")
    @classmethod
    def check_password(cls, value: str) -> str:
        return validate_utf8_password(value)

    @model_validator(mode="after")
    def validate_role_angkatan(self) -> "UserCreate":
        if self.role != "Mahasiswa" and self.angkatan_id is not None:
            raise ValueError("angkatan_id hanya berlaku untuk peran Mahasiswa")
        return self


class UserUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nim_nidn: NimNidn | None = None
    nama: NamaUser | None = None
    email: EmailStr | None = None
    aktif: bool | None = None
    angkatan_id: UUID | None = None

    @field_validator("email", mode="after")
    @classmethod
    def normalize_email(cls, value: EmailStr | None) -> str | None:
        return str(value).strip().lower() if value is not None else None

    @model_validator(mode="after")
    def validate_patch(self) -> "UserUpdate":
        if not self.model_fields_set:
            raise ValueError("Isi minimal satu perubahan")
        for name in self.model_fields_set:
            if getattr(self, name) is None:
                raise ValueError(f"{name} tidak boleh null")
        return self


class AdminResetPasswordRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    password_baru: str
    alasan: str | None = Field(default=None, max_length=500)

    @field_validator("password_baru")
    @classmethod
    def check_password(cls, value: str) -> str:
        return validate_utf8_password(value)

    @field_validator("alasan")
    @classmethod
    def normalize_alasan(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None


class UserManageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    prodi_id: UUID
    nim_nidn: str
    nama: str
    email: EmailStr
    role: Role
    aktif: bool
    angkatan_id: UUID | None = None
    tahun_masuk: int | None = None
