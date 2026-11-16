from uuid import UUID

from pydantic import BaseModel


class KelasMKResponse(BaseModel):
    id: UUID
    periode_id: UUID
    tahun_akademik: str
    semester: str
    kelas: str
    kurikulum_mk_id: UUID
    kode_mk: str
    nama_mk: str
    dosen_id: UUID
    rancangan_id: UUID
