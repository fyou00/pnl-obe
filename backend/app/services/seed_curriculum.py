"""Data-driven curriculum and course seed loader from JSON files."""

import argparse
from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import ENV_FILE, DatabaseSettings
from app.core.database import Database
from app.models import (
    MKCPL,
    PLCPL,
    Kurikulum,
    KurikulumMK,
    MasterCPL,
    MataKuliah,
    Prodi,
    ProfilLulusan,
)

KodeProdi = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=20)]
NamaProdi = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
Jenjang = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=10)]
KodeKurikulum = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=30)
]
Nama = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
KodeMK = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=20)]
KodeCPL = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=10)]
KodePL = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=10)]
NamaPL = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=150)]
KategoriCPL = Literal["S", "KU", "P", "KK"]
NonEmptyText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class SeedPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ProdiSeed(SeedPayload):
    kode_prodi: KodeProdi
    nama_prodi: NamaProdi
    jenjang: Jenjang


class KurikulumSeed(SeedPayload):
    kode_kurikulum: KodeKurikulum
    nama: Nama


class CourseSeedItem(SeedPayload):
    no: int = Field(ge=1, strict=True)
    kode_mk: KodeMK
    nama_mk: Nama
    semester: int = Field(ge=1, le=8, strict=True)
    sks: int = Field(gt=0, le=32767, strict=True)
    jam_per_minggu: int | None = Field(default=None, gt=0, le=32767, strict=True)
    prasyarat: str | None = None
    deskripsi_singkat: NonEmptyText
    learning_outcome: NonEmptyText | None = None


class CplSeedItem(SeedPayload):
    kode_cpl: KodeCPL
    kategori: KategoriCPL
    unsur: list[KategoriCPL] = Field(default_factory=list)
    nasional: bool = False
    deskripsi: NonEmptyText

    @model_validator(mode="after")
    def validate_cpl(self) -> "CplSeedItem":
        if self.nasional and self.kategori not in ("S", "KU"):
            raise ValueError("CPL nasional hanya boleh kategori S atau KU")
        if self.unsur:
            if len(set(self.unsur)) != len(self.unsur):
                raise ValueError("Unsur CPL tidak boleh duplikat")
            if self.kategori not in self.unsur:
                raise ValueError("Kategori utama CPL harus termasuk dalam daftar unsur")
        return self


class MkCplSeedLink(SeedPayload):
    kode_cpl: KodeCPL
    urutan_rps: int | None = Field(default=None, gt=0, le=2147483647, strict=True)


class MkCplSeedItem(SeedPayload):
    kode_mk: KodeMK
    cpl: list[MkCplSeedLink] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_unique_cpl(self) -> "MkCplSeedItem":
        if len({link.kode_cpl for link in self.cpl}) != len(self.cpl):
            raise ValueError("Kode CPL duplikat dalam pemetaan MK yang sama")
        return self


class ProfilLulusanSeedItem(SeedPayload):
    kode_pl: KodePL
    nama_pl: NamaPL
    bidang_kerja: str | None = None
    deskripsi: NonEmptyText


class PlCplSeedItem(SeedPayload):
    kode_pl: KodePL
    cpl: list[KodeCPL] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_unique_cpl(self) -> "PlCplSeedItem":
        if len(set(self.cpl)) != len(self.cpl):
            raise ValueError("Kode CPL duplikat dalam pemetaan PL yang sama")
        return self


class CurriculumSeedFile(SeedPayload):
    sumber: str | None = None
    prodi: ProdiSeed
    kurikulum: KurikulumSeed
    catatan_normalisasi: list[str] = Field(default_factory=list)
    mata_kuliah: list[CourseSeedItem] = Field(default_factory=list)
    cpl: list[CplSeedItem] = Field(default_factory=list)
    mk_cpl: list[MkCplSeedItem] = Field(default_factory=list)
    profil_lulusan: list[ProfilLulusanSeedItem] = Field(default_factory=list)
    pl_cpl: list[PlCplSeedItem] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_contents(self) -> "CurriculumSeedFile":
        if (
            not self.mata_kuliah
            and not self.cpl
            and not self.mk_cpl
            and not self.profil_lulusan
            and not self.pl_cpl
        ):
            raise ValueError(
                "File seed harus memuat minimal mata_kuliah, cpl, mk_cpl, profil_lulusan, atau pl_cpl"
            )
        if self.mata_kuliah:
            if len({item.kode_mk for item in self.mata_kuliah}) != len(self.mata_kuliah):
                raise ValueError("Kode mata kuliah duplikat pada file seed")
            if len({item.no for item in self.mata_kuliah}) != len(self.mata_kuliah):
                raise ValueError("Nomor urut mata kuliah duplikat pada file seed")
        if self.cpl and len({item.kode_cpl for item in self.cpl}) != len(self.cpl):
            raise ValueError("Kode CPL duplikat pada file seed")
        if self.mk_cpl and len({entry.kode_mk for entry in self.mk_cpl}) != len(self.mk_cpl):
            raise ValueError("Kode MK duplikat pada daftar mk_cpl")
        if self.profil_lulusan and len({item.kode_pl for item in self.profil_lulusan}) != len(
            self.profil_lulusan
        ):
            raise ValueError("Kode profil lulusan duplikat pada file seed")
        if self.pl_cpl and len({entry.kode_pl for entry in self.pl_cpl}) != len(self.pl_cpl):
            raise ValueError("Kode PL duplikat pada daftar pl_cpl")
        return self


def load_curriculum_seed(path: Path | str) -> CurriculumSeedFile:
    """Read and validate a curriculum JSON seed file."""
    content = Path(path).read_text(encoding="utf-8")
    return CurriculumSeedFile.model_validate_json(content)


def format_course_description(item: CourseSeedItem) -> str:
    """Format short description and learning outcome for database storage."""
    if item.learning_outcome:
        return f"{item.deskripsi_singkat}\n\nLearning Outcome: {item.learning_outcome}"
    return item.deskripsi_singkat


def _ensure_prodi(db: Session, prodi_seed: ProdiSeed) -> Prodi:
    prodi = db.scalar(select(Prodi).where(Prodi.kode_prodi == prodi_seed.kode_prodi))
    if prodi is None:
        prodi = Prodi(
            kode_prodi=prodi_seed.kode_prodi,
            nama_prodi=prodi_seed.nama_prodi,
            jenjang=prodi_seed.jenjang,
        )
        db.add(prodi)
        db.flush()
        return prodi
    if prodi.nama_prodi != prodi_seed.nama_prodi or prodi.jenjang != prodi_seed.jenjang:
        raise ValueError("Kode prodi seed sudah dipakai dengan identitas berbeda")
    return prodi


def _ensure_kurikulum(db: Session, prodi: Prodi, kurikulum_seed: KurikulumSeed) -> Kurikulum:
    kurikulum = db.scalar(
        select(Kurikulum).where(
            Kurikulum.prodi_id == prodi.id,
            Kurikulum.kode_kurikulum == kurikulum_seed.kode_kurikulum,
        )
    )
    if kurikulum is None:
        kurikulum = Kurikulum(
            prodi_id=prodi.id,
            kode_kurikulum=kurikulum_seed.kode_kurikulum,
            nama=kurikulum_seed.nama,
            status="Draft",
        )
        db.add(kurikulum)
        db.flush()
        return kurikulum
    if kurikulum.nama != kurikulum_seed.nama:
        raise ValueError("Kode kurikulum seed sudah dipakai dengan nama berbeda")
    return kurikulum


def seed_curriculum_data(db: Session, payload: CurriculumSeedFile) -> dict[str, str | int]:
    """Idempotently seed prodi, draft curriculum, MK, CPL, and MK-CPL mappings."""
    prodi = _ensure_prodi(db, payload.prodi)
    kurikulum = _ensure_kurikulum(db, prodi, payload.kurikulum)

    mk_created = 0
    mk_existing = 0
    paket_created = 0
    paket_existing = 0
    cpl_created = 0
    cpl_existing = 0
    mk_cpl_created = 0
    mk_cpl_existing = 0
    pl_created = 0
    pl_existing = 0
    pl_cpl_created = 0
    pl_cpl_existing = 0

    for item in payload.mata_kuliah:
        deskripsi = format_course_description(item)

        mk = db.scalar(
            select(MataKuliah).where(
                MataKuliah.prodi_id == prodi.id,
                MataKuliah.kode_mk == item.kode_mk,
            )
        )
        if mk is None:
            mk = MataKuliah(
                prodi_id=prodi.id,
                kode_mk=item.kode_mk,
                nama_mk=item.nama_mk,
                deskripsi=deskripsi,
                aktif=True,
            )
            db.add(mk)
            db.flush()
            mk_created += 1
        else:
            if mk.nama_mk != item.nama_mk:
                raise ValueError(f"Kode MK {item.kode_mk} sudah terdaftar dengan nama berbeda")
            if mk.deskripsi is None:
                mk.deskripsi = deskripsi
            mk_existing += 1

        existing = db.scalar(
            select(KurikulumMK).where(
                KurikulumMK.kurikulum_id == kurikulum.id,
                KurikulumMK.mk_id == mk.id,
            )
        )
        if existing is None:
            if kurikulum.status != "Draft":
                raise ValueError("Kurikulum Aktif/Arsip tidak dapat ditambah MK paket oleh seed")
            db.add(
                KurikulumMK(
                    kurikulum_id=kurikulum.id,
                    mk_id=mk.id,
                    nama_mk=item.nama_mk,
                    sks=item.sks,
                    semester=item.semester,
                    deskripsi=deskripsi,
                )
            )
            paket_created += 1
        else:
            if (existing.nama_mk, existing.sks, existing.semester) != (
                item.nama_mk,
                item.sks,
                item.semester,
            ):
                raise ValueError(
                    f"Snapshot MK {item.kode_mk} pada kurikulum {kurikulum.kode_kurikulum} "
                    "bertabrakan dengan data yang ada"
                )
            if existing.deskripsi is None and kurikulum.status == "Draft":
                existing.deskripsi = deskripsi
            paket_existing += 1

    for item in payload.cpl:
        expected_prodi_id = None if item.nasional else prodi.id
        existing_cpl = db.scalar(
            select(MasterCPL).where(
                MasterCPL.kurikulum_id == kurikulum.id,
                MasterCPL.kode_cpl == item.kode_cpl,
            )
        )
        if existing_cpl is None:
            if kurikulum.status != "Draft":
                raise ValueError("Kurikulum Aktif/Arsip tidak dapat ditambah CPL oleh seed")
            db.add(
                MasterCPL(
                    kurikulum_id=kurikulum.id,
                    prodi_id=expected_prodi_id,
                    kode_cpl=item.kode_cpl,
                    kategori=item.kategori,
                    deskripsi=item.deskripsi,
                )
            )
            cpl_created += 1
        else:
            if existing_cpl.prodi_id != expected_prodi_id or existing_cpl.kategori != item.kategori:
                raise ValueError(
                    f"CPL {item.kode_cpl} pada kurikulum {kurikulum.kode_kurikulum} "
                    "bertabrakan dengan data yang ada"
                )
            cpl_existing += 1

    db.flush()

    for entry in payload.mk_cpl:
        paket = db.scalar(
            select(KurikulumMK)
            .join(MataKuliah, MataKuliah.id == KurikulumMK.mk_id)
            .where(
                KurikulumMK.kurikulum_id == kurikulum.id,
                MataKuliah.prodi_id == prodi.id,
                MataKuliah.kode_mk == entry.kode_mk,
            )
        )
        if paket is None:
            raise ValueError(
                f"MK paket {entry.kode_mk} belum ada pada kurikulum {kurikulum.kode_kurikulum}; "
                "jalankan seed mata kuliah terlebih dahulu"
            )
        for link_item in entry.cpl:
            cpl_row = db.scalar(
                select(MasterCPL).where(
                    MasterCPL.kurikulum_id == kurikulum.id,
                    MasterCPL.kode_cpl == link_item.kode_cpl,
                )
            )
            if cpl_row is None:
                raise ValueError(
                    f"CPL {link_item.kode_cpl} belum ada pada kurikulum "
                    f"{kurikulum.kode_kurikulum}; jalankan seed CPL terlebih dahulu"
                )
            if cpl_row.prodi_id is not None and cpl_row.prodi_id != prodi.id:
                raise ValueError(f"CPL {link_item.kode_cpl} berasal dari prodi berbeda")
            existing_link = db.scalar(
                select(MKCPL).where(
                    MKCPL.kurikulum_mk_id == paket.id,
                    MKCPL.cpl_id == cpl_row.id,
                )
            )
            if existing_link is None:
                if kurikulum.status != "Draft":
                    raise ValueError(
                        "Kurikulum Aktif/Arsip tidak dapat ditambah pemetaan MK-CPL oleh seed"
                    )
                db.add(
                    MKCPL(
                        kurikulum_mk_id=paket.id,
                        cpl_id=cpl_row.id,
                        urutan_rps=link_item.urutan_rps,
                    )
                )
                mk_cpl_created += 1
            else:
                if (
                    existing_link.urutan_rps is None
                    and link_item.urutan_rps is not None
                    and kurikulum.status == "Draft"
                ):
                    existing_link.urutan_rps = link_item.urutan_rps
                mk_cpl_existing += 1

    db.flush()

    for item in payload.profil_lulusan:
        bidang_kerja = item.bidang_kerja.strip() if item.bidang_kerja else None
        bidang_kerja = bidang_kerja or None
        existing_pl = db.scalar(
            select(ProfilLulusan).where(
                ProfilLulusan.kurikulum_id == kurikulum.id,
                ProfilLulusan.kode_pl == item.kode_pl,
            )
        )
        if existing_pl is None:
            if kurikulum.status != "Draft":
                raise ValueError(
                    "Kurikulum Aktif/Arsip tidak dapat ditambah profil lulusan oleh seed"
                )
            db.add(
                ProfilLulusan(
                    kurikulum_id=kurikulum.id,
                    kode_pl=item.kode_pl,
                    nama_pl=item.nama_pl,
                    bidang_kerja=bidang_kerja,
                    deskripsi=item.deskripsi,
                )
            )
            pl_created += 1
        else:
            if existing_pl.nama_pl != item.nama_pl:
                raise ValueError(
                    f"Profil Lulusan {item.kode_pl} pada kurikulum {kurikulum.kode_kurikulum} "
                    "bertabrakan dengan data yang ada"
                )
            if (
                existing_pl.bidang_kerja is None
                and bidang_kerja is not None
                and kurikulum.status == "Draft"
            ):
                existing_pl.bidang_kerja = bidang_kerja
            pl_existing += 1

    db.flush()

    for entry in payload.pl_cpl:
        pl_row = db.scalar(
            select(ProfilLulusan).where(
                ProfilLulusan.kurikulum_id == kurikulum.id,
                ProfilLulusan.kode_pl == entry.kode_pl,
            )
        )
        if pl_row is None:
            raise ValueError(
                f"Profil lulusan {entry.kode_pl} belum ada pada kurikulum "
                f"{kurikulum.kode_kurikulum}; jalankan seed profil lulusan terlebih dahulu"
            )
        for kode_cpl in entry.cpl:
            cpl_row = db.scalar(
                select(MasterCPL).where(
                    MasterCPL.kurikulum_id == kurikulum.id,
                    MasterCPL.kode_cpl == kode_cpl,
                )
            )
            if cpl_row is None:
                raise ValueError(
                    f"CPL {kode_cpl} belum ada pada kurikulum "
                    f"{kurikulum.kode_kurikulum}; jalankan seed CPL terlebih dahulu"
                )
            if cpl_row.prodi_id is not None and cpl_row.prodi_id != prodi.id:
                raise ValueError(f"CPL {kode_cpl} berasal dari prodi berbeda")
            existing_pl_cpl = db.scalar(
                select(PLCPL).where(
                    PLCPL.profil_lulusan_id == pl_row.id,
                    PLCPL.cpl_id == cpl_row.id,
                )
            )
            if existing_pl_cpl is None:
                if kurikulum.status != "Draft":
                    raise ValueError(
                        "Kurikulum Aktif/Arsip tidak dapat ditambah pemetaan PL-CPL oleh seed"
                    )
                db.add(PLCPL(profil_lulusan_id=pl_row.id, cpl_id=cpl_row.id))
                pl_cpl_created += 1
            else:
                pl_cpl_existing += 1

    db.flush()
    return {
        "prodi_id": str(prodi.id),
        "kurikulum_id": str(kurikulum.id),
        "mk_created": mk_created,
        "mk_existing": mk_existing,
        "paket_created": paket_created,
        "paket_existing": paket_existing,
        "total_mk": len(payload.mata_kuliah),
        "total_sks": sum(item.sks for item in payload.mata_kuliah),
        "cpl_created": cpl_created,
        "cpl_existing": cpl_existing,
        "total_cpl": len(payload.cpl),
        "mk_cpl_created": mk_cpl_created,
        "mk_cpl_existing": mk_cpl_existing,
        "total_mk_cpl": sum(len(entry.cpl) for entry in payload.mk_cpl),
        "pl_created": pl_created,
        "pl_existing": pl_existing,
        "total_pl": len(payload.profil_lulusan),
        "pl_cpl_created": pl_cpl_created,
        "pl_cpl_existing": pl_cpl_existing,
        "total_pl_cpl": sum(len(entry.cpl) for entry in payload.pl_cpl),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Seed kurikulum, mata kuliah, CPL, dan matriks MK-CPL dari file JSON PNL OBE"
    )
    parser.add_argument(
        "files",
        nargs="+",
        type=Path,
        help=(
            "Path satu atau lebih file JSON seed kurikulum "
            "(mis. seeds/kurikulum_ti_2024_mk_cpl.json)"
        ),
    )
    args = parser.parse_args()
    payloads = [(file_path, load_curriculum_seed(file_path)) for file_path in args.files]
    config = DatabaseSettings(_env_file=ENV_FILE)
    database = Database(config)
    try:
        summaries = []
        with database.session_factory.begin() as db:
            for file_path, payload in payloads:
                summaries.append((file_path, payload, seed_curriculum_data(db, payload)))
        for file_path, payload, summary in summaries:
            print(
                f"Seed kurikulum selesai ({file_path.name}, "
                f"kurikulum={payload.kurikulum.kode_kurikulum}, "
                f"MK baru={summary['mk_created']}, MK ada={summary['mk_existing']}, "
                f"paket baru={summary['paket_created']}, paket ada={summary['paket_existing']}, "
                f"total={summary['total_mk']} MK / {summary['total_sks']} SKS, "
                f"CPL baru={summary['cpl_created']}, CPL ada={summary['cpl_existing']}, "
                f"total CPL={summary['total_cpl']}, "
                f"MK-CPL baru={summary['mk_cpl_created']}, MK-CPL ada={summary['mk_cpl_existing']}, "
                f"total MK-CPL={summary['total_mk_cpl']}, "
                f"PL baru={summary['pl_created']}, PL ada={summary['pl_existing']}, "
                f"total PL={summary['total_pl']}, "
                f"PL-CPL baru={summary['pl_cpl_created']}, PL-CPL ada={summary['pl_cpl_existing']}, "
                f"total PL-CPL={summary['total_pl_cpl']})."
            )
    finally:
        database.dispose()


if __name__ == "__main__":
    main()
