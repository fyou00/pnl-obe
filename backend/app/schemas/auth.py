from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator

Role = Literal["Admin", "Dosen", "Mahasiswa"]


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    prodi_id: UUID
    nim_nidn: str
    nama: str
    email: EmailStr
    role: Role
    aktif: bool


class TokenResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int


class ChangePasswordRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    password_lama: str = Field(min_length=1, max_length=72)
    password_baru: str = Field(min_length=12, max_length=72)

    @model_validator(mode="after")
    def validate_passwords(self) -> "ChangePasswordRequest":
        raw_new = self.password_baru.encode("utf-8")
        if not 12 <= len(raw_new) <= 72:
            raise ValueError("Kata sandi baru harus 12–72 byte UTF-8")
        if self.password_baru == self.password_lama:
            raise ValueError("Kata sandi baru harus berbeda dari kata sandi saat ini")
        return self
