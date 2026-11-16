from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr

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
