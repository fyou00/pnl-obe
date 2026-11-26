"""Import every mapped table so Alembic sees the complete schema."""

from app.models.academic import (
    KelasMK,
    KelasPeriode,
    MahasiswaPeriode,
    PeriodeAkademik,
    PesertaKelasMK,
    RancanganPenilaian,
)
from app.models.assessment import CPMK, CPMKCPL, InstrumenPenilaian, NilaiMahasiswa, SubCPMK
from app.models.audit import AuditLog
from app.models.base import Base
from app.models.curriculum import (
    MKCPL,
    PLCPL,
    Kurikulum,
    KurikulumMK,
    MasterCPL,
    MataKuliah,
    ProfilLulusan,
)
from app.models.identity import Angkatan, Mahasiswa, Prodi, User

__all__ = [
    "Base",
    "Prodi",
    "User",
    "Angkatan",
    "Mahasiswa",
    "Kurikulum",
    "MataKuliah",
    "KurikulumMK",
    "MasterCPL",
    "MKCPL",
    "ProfilLulusan",
    "PLCPL",
    "PeriodeAkademik",
    "KelasPeriode",
    "MahasiswaPeriode",
    "RancanganPenilaian",
    "KelasMK",
    "PesertaKelasMK",
    "CPMK",
    "CPMKCPL",
    "SubCPMK",
    "InstrumenPenilaian",
    "NilaiMahasiswa",
    "AuditLog",
]
