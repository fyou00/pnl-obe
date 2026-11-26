"""Data-driven operational demo seed loader from JSON files.

All passwords come from environment variables (`SEED_DOSEN_PASSWORD` and
`SEED_MAHASISWA_PASSWORD`), never from JSON seed files.
"""

import argparse
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Annotated, Literal
from uuid import UUID

from fastapi.encoders import jsonable_encoder
from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    SecretStr,
    StringConstraints,
    TypeAdapter,
    model_validator,
)
from sqlalchemy import inspect, or_, select
from sqlalchemy.orm import Session

from app.core.config import ENV_FILE, DatabaseSettings
from app.core.database import Database
from app.core.security import hash_password
from app.models import (
    CPMK,
    CPMKCPL,
    MKCPL,
    Angkatan,
    AuditLog,
    InstrumenPenilaian,
    KelasMK,
    KelasPeriode,
    Kurikulum,
    KurikulumMK,
    Mahasiswa,
    MahasiswaPeriode,
    MasterCPL,
    MataKuliah,
    NilaiMahasiswa,
    PeriodeAkademik,
    PesertaKelasMK,
    Prodi,
    RancanganPenilaian,
    SubCPMK,
    User,
)

KodeProdi = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=20)]
KodeKurikulum = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=30)
]
KodeMK = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=20)]
KodeCPL = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=10)]
KodeSub = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=20)]
NimNidn = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=20)]
Nama = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
NonEmptyText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
Weight = Annotated[
    Decimal, Field(gt=0, le=100, max_digits=5, decimal_places=2, allow_inf_nan=False)
]
Score = Annotated[Decimal, Field(ge=0, le=100, max_digits=5, decimal_places=2, allow_inf_nan=False)]
ClassCode = Literal["A", "B", "C", "D", "E", "K"]
RegularClassCode = Literal["A", "B", "C", "D", "E"]
SemesterKind = Literal["Ganjil", "Genap"]
PeriodStatus = Literal["Dibuka", "Ditutup"]
StudentStatus = Literal["Aktif", "Cuti", "Nonaktif"]
InstrumentKind = Literal["Tugas", "Kuis", "Praktikum", "UTS", "UAS"]


class DemoSeedSettings(DatabaseSettings):
    seed_dosen_password: SecretStr
    seed_mahasiswa_password: SecretStr


class DemoPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")


class DemoLecturerItem(DemoPayload):
    nim_nidn: NimNidn
    nama: Nama
    email: EmailStr


class DemoAngkatanItem(DemoPayload):
    tahun_masuk: int = Field(ge=2000, le=2100, strict=True)


class DemoStudentItem(DemoPayload):
    nim_nidn: NimNidn
    nama: Nama
    email: EmailStr
    tahun_masuk: int = Field(ge=2000, le=2100, strict=True)


class DemoClassItem(DemoPayload):
    tahun_masuk: int = Field(ge=2000, le=2100, strict=True)
    kode_kelas: ClassCode
    semester_studi: int | None = Field(default=None, ge=1, le=8, strict=True)

    @model_validator(mode="after")
    def validate_class_code(self) -> "DemoClassItem":
        if self.kode_kelas == "K" and self.semester_studi is not None:
            raise ValueError("Kelas K wajib memiliki semester_studi null")
        if self.kode_kelas != "K" and self.semester_studi is None:
            raise ValueError("Kelas reguler A–E wajib memiliki semester_studi 1–8")
        return self


class DemoRosterItem(DemoPayload):
    nim_nidn: NimNidn
    kode_kelas: ClassCode
    status: StudentStatus

    @model_validator(mode="after")
    def validate_status(self) -> "DemoRosterItem":
        if self.kode_kelas == "K" and self.status not in ("Cuti", "Nonaktif"):
            raise ValueError("Kelas K hanya untuk status Cuti atau Nonaktif")
        if self.kode_kelas != "K" and self.status != "Aktif":
            raise ValueError("Kelas reguler A–E hanya untuk status Aktif")
        return self


class DemoAssignmentItem(DemoPayload):
    tahun_masuk: int = Field(ge=2000, le=2100, strict=True)
    kode_kelas: RegularClassCode
    kode_mk: KodeMK
    dosen_nim_nidn: NimNidn


class DemoInstrumentItem(DemoPayload):
    nama_instrumen: Nama
    jenis_instrumen: InstrumentKind
    bobot_persentase: Weight


class DemoSubCpmkItem(DemoPayload):
    kode_sub: KodeSub
    deskripsi: NonEmptyText
    instrumen: list[DemoInstrumentItem] = Field(default_factory=list)


class DemoCpmkItem(DemoPayload):
    kode_cpmk: KodeSub
    deskripsi: NonEmptyText
    cpl: list[KodeCPL] = Field(default_factory=list)
    sub_cpmk: list[DemoSubCpmkItem] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_sub_and_cpl(self) -> "DemoCpmkItem":
        if len(set(self.cpl)) != len(self.cpl):
            raise ValueError(f"CPL duplikat pada {self.kode_cpmk}")
        sub_codes = [sub.kode_sub for sub in self.sub_cpmk]
        if len(set(sub_codes)) != len(sub_codes):
            raise ValueError(f"Kode Sub-CPMK duplikat pada {self.kode_cpmk}")
        return self


class DemoGradeEntry(DemoPayload):
    nim_nidn: NimNidn
    nama_instrumen: Nama
    nilai_mentah: Score


class DemoClassGradesItem(DemoPayload):
    tahun_masuk: int = Field(ge=2000, le=2100, strict=True)
    kode_kelas: RegularClassCode
    skor: list[DemoGradeEntry] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_unique_scores(self) -> "DemoClassGradesItem":
        pairs = {(item.nim_nidn, item.nama_instrumen) for item in self.skor}
        if len(pairs) != len(self.skor):
            raise ValueError("Pasangan mahasiswa dan instrumen duplikat pada skor kelas")
        return self


class DemoDesignItem(DemoPayload):
    kode_mk: KodeMK
    dosen_nim_nidn: NimNidn
    cpmk: list[DemoCpmkItem] = Field(default_factory=list)
    nilai: list[DemoClassGradesItem] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_design(self) -> "DemoDesignItem":
        cpmk_codes = [item.kode_cpmk for item in self.cpmk]
        if len(set(cpmk_codes)) != len(cpmk_codes):
            raise ValueError(f"Kode CPMK duplikat pada rancangan {self.kode_mk}")
        instrument_names = [
            inst.nama_instrumen
            for cpmk in self.cpmk
            for sub in cpmk.sub_cpmk
            for inst in sub.instrumen
        ]
        if len(set(instrument_names)) != len(instrument_names):
            raise ValueError(f"Nama instrumen duplikat pada rancangan {self.kode_mk}")
        total_weight = sum(
            (
                inst.bobot_persentase
                for cpmk in self.cpmk
                for sub in cpmk.sub_cpmk
                for inst in sub.instrumen
            ),
            Decimal("0.00"),
        )
        if total_weight > Decimal("100.00"):
            raise ValueError(f"Total bobot instrumen {self.kode_mk} melebihi 100.00%")
        if self.nilai:
            if not self.cpmk or total_weight != Decimal("100.00"):
                raise ValueError(
                    f"Rancangan {self.kode_mk} memiliki nilai sehingga total bobot wajib 100.00%"
                )
            if any(not cpmk.cpl for cpmk in self.cpmk):
                raise ValueError(
                    f"Setiap CPMK pada {self.kode_mk} wajib terpetakan ke CPL sebelum ada nilai"
                )
            valid_instruments = set(instrument_names)
            for class_grades in self.nilai:
                for score in class_grades.skor:
                    if score.nama_instrumen not in valid_instruments:
                        raise ValueError(
                            f"Instrumen {score.nama_instrumen} tidak ada di rancangan {self.kode_mk}"
                        )
        class_keys = [(item.tahun_masuk, item.kode_kelas) for item in self.nilai]
        if len(set(class_keys)) != len(class_keys):
            raise ValueError(f"Kelas duplikat pada daftar nilai {self.kode_mk}")
        return self


class DemoPeriodItem(DemoPayload):
    tahun_mulai: int = Field(ge=2000, le=2100, strict=True)
    semester: SemesterKind
    status: PeriodStatus = "Dibuka"
    alasan_tutup: str | None = None
    kelas: list[DemoClassItem] = Field(min_length=1)
    roster: list[DemoRosterItem] = Field(default_factory=list)
    penugasan: list[DemoAssignmentItem] = Field(default_factory=list)
    rancangan: list[DemoDesignItem] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_period_consistency(self) -> "DemoPeriodItem":
        class_keys = [(k.tahun_masuk, k.kode_kelas) for k in self.kelas]
        if len(set(class_keys)) != len(class_keys):
            raise ValueError("Kelas duplikat pada periode")
        parity = 1 if self.semester == "Ganjil" else 0
        sem_by_cohort: dict[int, int] = {}
        for klass in self.kelas:
            if klass.tahun_masuk > self.tahun_mulai:
                raise ValueError("Periode tidak boleh mendahului tahun masuk angkatan")
            if klass.kode_kelas != "K":
                assert klass.semester_studi is not None
                if klass.semester_studi % 2 != parity:
                    raise ValueError(
                        f"Semester studi {klass.semester_studi} tidak cocok dengan {self.semester}"
                    )
                prev = sem_by_cohort.setdefault(klass.tahun_masuk, klass.semester_studi)
                if prev != klass.semester_studi:
                    raise ValueError(
                        "Seluruh kelas reguler satu angkatan/periode wajib memakai semester studi sama"
                    )
        roster_nims = [r.nim_nidn for r in self.roster]
        if len(set(roster_nims)) != len(roster_nims):
            raise ValueError("Mahasiswa duplikat pada roster periode")
        assign_keys = [(a.tahun_masuk, a.kode_kelas, a.kode_mk) for a in self.penugasan]
        if len(set(assign_keys)) != len(assign_keys):
            raise ValueError("Penugasan kelas MK duplikat pada periode")
        for a in self.penugasan:
            if (a.tahun_masuk, a.kode_kelas) not in set(class_keys):
                raise ValueError(
                    f"Penugasan MK {a.kode_mk} menunjuk kelas yang belum terdaftar pada periode"
                )
        design_keys = [(d.kode_mk, d.dosen_nim_nidn) for d in self.rancangan]
        if len(set(design_keys)) != len(design_keys):
            raise ValueError("Rancangan duplikat untuk pasangan MK dan dosen pada periode")
        return self


class DemoOperationalSeedFile(DemoPayload):
    sumber: str | None = None
    prodi_kode: KodeProdi
    kurikulum_kode: KodeKurikulum
    aktivasi_kurikulum: bool = True
    dosen: list[DemoLecturerItem] = Field(min_length=1)
    angkatan: list[DemoAngkatanItem] = Field(min_length=1)
    mahasiswa: list[DemoStudentItem] = Field(min_length=1)
    periode: list[DemoPeriodItem] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_references(self) -> "DemoOperationalSeedFile":
        lecturer_ids = [d.nim_nidn for d in self.dosen]
        student_ids = [m.nim_nidn for m in self.mahasiswa]
        all_ids = lecturer_ids + student_ids
        if len(set(all_ids)) != len(all_ids):
            raise ValueError("NIM/NIDN duplikat di antara daftar dosen dan mahasiswa")
        all_emails = [str(d.email).lower() for d in self.dosen] + [
            str(m.email).lower() for m in self.mahasiswa
        ]
        if len(set(all_emails)) != len(all_emails):
            raise ValueError("Email duplikat di antara daftar dosen dan mahasiswa")
        cohort_years = {a.tahun_masuk for a in self.angkatan}
        if len(cohort_years) != len(self.angkatan):
            raise ValueError("Tahun masuk angkatan duplikat")
        student_cohort = {m.nim_nidn: m.tahun_masuk for m in self.mahasiswa}
        for m in self.mahasiswa:
            if m.tahun_masuk not in cohort_years:
                raise ValueError(f"Angkatan {m.tahun_masuk} untuk {m.nim_nidn} belum terdaftar")
        period_keys = [(p.tahun_mulai, p.semester) for p in self.periode]
        if len(set(period_keys)) != len(period_keys):
            raise ValueError("Periode akademik duplikat")
        lecturer_set = set(lecturer_ids)
        for p in self.periode:
            class_set = {(k.tahun_masuk, k.kode_kelas) for k in p.kelas}
            active_students_by_class: dict[tuple[int, str], set[str]] = {}
            for r in p.roster:
                if r.nim_nidn not in student_cohort:
                    raise ValueError(f"Roster {r.nim_nidn} tidak terdaftar pada daftar mahasiswa")
                year = student_cohort[r.nim_nidn]
                if (year, r.kode_kelas) not in class_set:
                    raise ValueError(f"Kelas {r.kode_kelas} angkatan {year} belum ada pada periode")
                if r.status == "Aktif":
                    active_students_by_class.setdefault((year, r.kode_kelas), set()).add(r.nim_nidn)
            assign_by_design: dict[tuple[str, str], set[tuple[int, str]]] = {}
            for a in p.penugasan:
                if a.dosen_nim_nidn not in lecturer_set:
                    raise ValueError(f"Dosen {a.dosen_nim_nidn} belum terdaftar di daftar dosen")
                assign_by_design.setdefault((a.kode_mk, a.dosen_nim_nidn), set()).add(
                    (a.tahun_masuk, a.kode_kelas)
                )
            for d in p.rancangan:
                assigned_classes = assign_by_design.get((d.kode_mk, d.dosen_nim_nidn), set())
                if not assigned_classes:
                    raise ValueError(
                        f"Rancangan {d.kode_mk} ({d.dosen_nim_nidn}) belum memiliki penugasan kelas"
                    )
                for cg in d.nilai:
                    if (cg.tahun_masuk, cg.kode_kelas) not in assigned_classes:
                        raise ValueError(
                            f"Nilai {d.kode_mk} menunjuk kelas {cg.kode_kelas} yang tidak diampu "
                            f"oleh {d.dosen_nim_nidn}"
                        )
                    allowed_students = active_students_by_class.get(
                        (cg.tahun_masuk, cg.kode_kelas), set()
                    )
                    for score in cg.skor:
                        if score.nim_nidn not in allowed_students:
                            raise ValueError(
                                f"Mahasiswa {score.nim_nidn} bukan peserta aktif kelas "
                                f"{cg.kode_kelas} angkatan {cg.tahun_masuk}"
                            )
        return self


def load_demo_seed(path: Path | str) -> DemoOperationalSeedFile:
    """Read and validate an operational demo JSON seed file."""
    return DemoOperationalSeedFile.model_validate_json(Path(path).read_text(encoding="utf-8"))


def _snapshot(row) -> dict:
    raw = {
        attr.key: (
            format(value, ".2f")
            if isinstance(value := getattr(row, attr.key), Decimal)
            else str(value)
            if isinstance(value, UUID)
            else value
        )
        for attr in inspect(row).mapper.column_attrs
    }
    return jsonable_encoder(raw)


def _ensure_account(
    db: Session,
    prodi: Prodi,
    *,
    nama: str,
    nim_nidn: str,
    email: str,
    password: SecretStr,
    role: str,
) -> User:
    normalized_email = str(TypeAdapter(EmailStr).validate_python(email)).lower()
    raw_password = password.get_secret_value()
    if not 12 <= len(raw_password.encode()) <= 72:
        raise ValueError("Password seed harus 12–72 byte UTF-8")
    users = list(
        db.scalars(
            select(User).where(or_(User.email == normalized_email, User.nim_nidn == nim_nidn))
        )
    )
    if users:
        if len(users) != 1:
            raise ValueError("Email dan NIM/NIDN seed bertabrakan dengan akun berbeda")
        user = users[0]
        if (
            user.email != normalized_email
            or user.nim_nidn != nim_nidn
            or user.prodi_id != prodi.id
            or user.role != role
        ):
            raise ValueError(f"Akun seed {nim_nidn} bertabrakan dengan pengguna yang sudah ada")
        return user
    user = User(
        prodi_id=prodi.id,
        nama=nama,
        nim_nidn=nim_nidn,
        email=normalized_email,
        password_hash=hash_password(raw_password),
        role=role,
    )
    db.add(user)
    db.flush()
    return user


def _ensure_active_curriculum(
    db: Session,
    prodi: Prodi,
    admin: User,
    kurikulum_kode: str,
    *,
    activate: bool,
) -> Kurikulum:
    kurikulum = db.scalar(
        select(Kurikulum).where(
            Kurikulum.prodi_id == prodi.id,
            Kurikulum.kode_kurikulum == kurikulum_kode,
        )
    )
    if kurikulum is None:
        raise ValueError(
            f"Kurikulum {kurikulum_kode} pada prodi {prodi.kode_prodi} belum tersedia; "
            "jalankan seed kurikulum terlebih dahulu"
        )
    if kurikulum.status == "Draft" and activate:
        for cpl in db.scalars(select(MasterCPL).where(MasterCPL.kurikulum_id == kurikulum.id)):
            if cpl.prodi_id is not None and cpl.prodi_id != prodi.id:
                raise ValueError("CPL harus berasal dari prodi kurikulum")
        paket = list(
            db.scalars(select(KurikulumMK).where(KurikulumMK.kurikulum_id == kurikulum.id))
        )
        if not paket:
            raise ValueError("Kurikulum harus memiliki minimal satu MK paket sebelum diaktifkan")
        for mk in paket:
            master = db.get(MataKuliah, mk.mk_id)
            if (
                master is None
                or master.prodi_id != prodi.id
                or not 1 <= mk.semester <= 8
                or mk.sks <= 0
            ):
                raise ValueError("Konteks atau isi MK paket tidak valid")
            links = list(db.scalars(select(MKCPL).where(MKCPL.kurikulum_mk_id == mk.id)))
            if not links:
                raise ValueError("Setiap MK paket wajib memiliki pembebanan CPL sebelum aktivasi")
            for link in links:
                cpl = db.get(MasterCPL, link.cpl_id)
                if (
                    cpl is None
                    or cpl.kurikulum_id != kurikulum.id
                    or (cpl.prodi_id is not None and cpl.prodi_id != prodi.id)
                ):
                    raise ValueError("CPL harus berasal dari kurikulum dan prodi yang sama")
        before = _snapshot(kurikulum)
        kurikulum.status = "Aktif"
        db.flush()
        db.add(
            AuditLog(
                aktor_id=admin.id,
                aksi="activate",
                entitas=kurikulum.__tablename__,
                entitas_id=kurikulum.id,
                sebelum=before,
                sesudah=_snapshot(kurikulum),
            )
        )
    if kurikulum.status not in ("Aktif", "Arsip"):
        raise ValueError(f"Kurikulum {kurikulum_kode} harus berstatus Aktif atau Arsip")
    return kurikulum


def _seed_design_and_grades(
    db: Session,
    *,
    kurikulum: Kurikulum,
    periode: PeriodeAkademik,
    was_closed: bool,
    design_item: DemoDesignItem,
    paket_by_code: dict[str, KurikulumMK],
    cpl_by_code: dict[str, MasterCPL],
    lecturer_by_nidn: dict[str, User],
    student_by_nim: dict[str, User],
    kelas_mk_by_key: dict[tuple[int, str, str], KelasMK],
) -> tuple[int, int]:
    def assert_mutable() -> None:
        if was_closed:
            raise ValueError(
                f"Periode {periode.tahun_akademik} {periode.semester} sudah ditutup "
                "dan tidak dapat ditambah data baru oleh seed"
            )

    paket_mk = paket_by_code.get(design_item.kode_mk)
    if paket_mk is None:
        raise ValueError(
            f"MK {design_item.kode_mk} belum ada di kurikulum {kurikulum.kode_kurikulum}"
        )
    dosen = lecturer_by_nidn[design_item.dosen_nim_nidn]
    design = db.scalar(
        select(RancanganPenilaian).where(
            RancanganPenilaian.periode_id == periode.id,
            RancanganPenilaian.kurikulum_mk_id == paket_mk.id,
            RancanganPenilaian.dosen_id == dosen.id,
        )
    )
    if design is None:
        raise ValueError(
            f"Rancangan {design_item.kode_mk} untuk dosen {dosen.nim_nidn} belum ditugaskan"
        )

    allowed_cpl_ids = set(
        db.scalars(select(MKCPL.cpl_id).where(MKCPL.kurikulum_mk_id == paket_mk.id))
    )
    existing_grades = (
        db.scalar(
            select(NilaiMahasiswa.id)
            .join(KelasMK, NilaiMahasiswa.kelas_mk_id == KelasMK.id)
            .where(KelasMK.rancangan_id == design.id)
            .limit(1)
        )
        is not None
    )

    instruments_by_name: dict[str, InstrumenPenilaian] = {}
    for cpmk_item in design_item.cpmk:
        cpmk_row = db.scalar(
            select(CPMK).where(
                CPMK.rancangan_id == design.id, CPMK.kode_cpmk == cpmk_item.kode_cpmk
            )
        )
        if cpmk_row is None:
            assert_mutable()
            if existing_grades:
                raise ValueError(
                    f"Struktur rancangan {design_item.kode_mk} dibekukan karena sudah ada nilai"
                )
            cpmk_row = CPMK(
                rancangan_id=design.id,
                kode_cpmk=cpmk_item.kode_cpmk,
                deskripsi=cpmk_item.deskripsi,
            )
            db.add(cpmk_row)
            db.flush()
        for kode_cpl in cpmk_item.cpl:
            cpl_row = cpl_by_code.get(kode_cpl)
            if cpl_row is None or cpl_row.id not in allowed_cpl_ids:
                raise ValueError(
                    f"CPL {kode_cpl} tidak dibebankan pada MK {design_item.kode_mk} "
                    f"di kurikulum {kurikulum.kode_kurikulum}"
                )
            link = db.scalar(
                select(CPMKCPL).where(CPMKCPL.cpmk_id == cpmk_row.id, CPMKCPL.cpl_id == cpl_row.id)
            )
            if link is None:
                assert_mutable()
                if existing_grades:
                    raise ValueError(
                        f"Pemetaan CPL {design_item.kode_mk} dibekukan karena sudah ada nilai"
                    )
                db.add(CPMKCPL(cpmk_id=cpmk_row.id, cpl_id=cpl_row.id))
        for sub_item in cpmk_item.sub_cpmk:
            sub_row = db.scalar(
                select(SubCPMK).where(
                    SubCPMK.cpmk_id == cpmk_row.id, SubCPMK.kode_sub == sub_item.kode_sub
                )
            )
            if sub_row is None:
                assert_mutable()
                if existing_grades:
                    raise ValueError(
                        f"Sub-CPMK {design_item.kode_mk} dibekukan karena sudah ada nilai"
                    )
                sub_row = SubCPMK(
                    cpmk_id=cpmk_row.id,
                    kode_sub=sub_item.kode_sub,
                    deskripsi=sub_item.deskripsi,
                )
                db.add(sub_row)
                db.flush()
            for inst_item in sub_item.instrumen:
                inst_row = db.scalar(
                    select(InstrumenPenilaian).where(
                        InstrumenPenilaian.sub_cpmk_id == sub_row.id,
                        InstrumenPenilaian.nama_instrumen == inst_item.nama_instrumen,
                    )
                )
                if inst_row is None:
                    assert_mutable()
                    if existing_grades:
                        raise ValueError(
                            f"Instrumen {design_item.kode_mk} dibekukan karena sudah ada nilai"
                        )
                    inst_row = InstrumenPenilaian(
                        sub_cpmk_id=sub_row.id,
                        nama_instrumen=inst_item.nama_instrumen,
                        jenis_instrumen=inst_item.jenis_instrumen,
                        bobot_persentase=inst_item.bobot_persentase,
                    )
                    db.add(inst_row)
                    db.flush()
                instruments_by_name[inst_item.nama_instrumen] = inst_row

    db.flush()
    nilai_created = 0
    nilai_existing = 0

    for class_grades in design_item.nilai:
        kelas_mk = kelas_mk_by_key.get(
            (class_grades.tahun_masuk, class_grades.kode_kelas, design_item.kode_mk)
        )
        if kelas_mk is None or kelas_mk.rancangan_id != design.id:
            raise ValueError(
                f"Kelas MK {design_item.kode_mk} untuk {class_grades.kode_kelas} tidak cocok "
                f"dengan rancangan dosen {dosen.nim_nidn}"
            )
        for score_item in class_grades.skor:
            student = student_by_nim[score_item.nim_nidn]
            inst_row = instruments_by_name[score_item.nama_instrumen]
            grade_row = db.scalar(
                select(NilaiMahasiswa).where(
                    NilaiMahasiswa.instrumen_id == inst_row.id,
                    NilaiMahasiswa.kelas_mk_id == kelas_mk.id,
                    NilaiMahasiswa.mahasiswa_id == student.id,
                )
            )
            if grade_row is None:
                assert_mutable()
                participant = db.scalar(
                    select(PesertaKelasMK).where(
                        PesertaKelasMK.kelas_mk_id == kelas_mk.id,
                        PesertaKelasMK.mahasiswa_id == student.id,
                    )
                )
                if participant is None:
                    raise ValueError(
                        f"Mahasiswa {student.nim_nidn} tidak terdaftar di kelas MK "
                        f"{design_item.kode_mk}"
                    )
                grade_row = NilaiMahasiswa(
                    instrumen_id=inst_row.id,
                    kelas_mk_id=kelas_mk.id,
                    mahasiswa_id=student.id,
                    nilai_mentah=score_item.nilai_mentah,
                    diubah_oleh=dosen.id,
                )
                db.add(grade_row)
                db.flush()
                db.add(
                    AuditLog(
                        aktor_id=dosen.id,
                        periode_id=periode.id,
                        aksi="create",
                        entitas=grade_row.__tablename__,
                        entitas_id=grade_row.id,
                        sebelum=None,
                        sesudah=_snapshot(grade_row),
                    )
                )
                nilai_created += 1
            else:
                nilai_existing += 1

    return nilai_created, nilai_existing


def seed_demo_data(
    db: Session,
    payload: DemoOperationalSeedFile,
    *,
    dosen_password: SecretStr,
    mahasiswa_password: SecretStr,
    admin_user: User | None = None,
) -> dict[str, str | int]:
    """Idempotently seed operational demo lecturers, students, periods, packages, and grades."""
    prodi = db.scalar(select(Prodi).where(Prodi.kode_prodi == payload.prodi_kode))
    if prodi is None:
        raise ValueError(
            f"Prodi {payload.prodi_kode} belum tersedia; jalankan seed awal terlebih dahulu"
        )
    admin = admin_user or db.scalar(
        select(User)
        .where(User.prodi_id == prodi.id, User.role == "Admin", User.aktif.is_(True))
        .order_by(User.id)
        .limit(1)
    )
    if admin is None or admin.prodi_id != prodi.id or admin.role != "Admin":
        raise ValueError("Akun Admin aktif untuk prodi ini wajib tersedia sebelum seed demo")

    kurikulum = _ensure_active_curriculum(
        db,
        prodi,
        admin,
        payload.kurikulum_kode,
        activate=payload.aktivasi_kurikulum,
    )

    lecturer_by_nidn: dict[str, User] = {}
    for item in payload.dosen:
        lecturer_by_nidn[item.nim_nidn] = _ensure_account(
            db,
            prodi,
            nama=item.nama,
            nim_nidn=item.nim_nidn,
            email=str(item.email),
            password=dosen_password,
            role="Dosen",
        )

    cohort_by_year: dict[int, Angkatan] = {}
    for item in payload.angkatan:
        cohort = db.scalar(
            select(Angkatan).where(
                Angkatan.prodi_id == prodi.id,
                Angkatan.tahun_masuk == item.tahun_masuk,
            )
        )
        if cohort is None:
            cohort = Angkatan(
                prodi_id=prodi.id,
                tahun_masuk=item.tahun_masuk,
                kurikulum_id=kurikulum.id,
            )
            db.add(cohort)
            db.flush()
        elif cohort.kurikulum_id != kurikulum.id:
            raise ValueError(
                f"Angkatan {item.tahun_masuk} sudah terikat pada kurikulum yang berbeda"
            )
        cohort_by_year[item.tahun_masuk] = cohort

    student_by_nim: dict[str, User] = {}
    student_year_by_nim: dict[str, int] = {}
    for item in payload.mahasiswa:
        user = _ensure_account(
            db,
            prodi,
            nama=item.nama,
            nim_nidn=item.nim_nidn,
            email=str(item.email),
            password=mahasiswa_password,
            role="Mahasiswa",
        )
        cohort = cohort_by_year[item.tahun_masuk]
        profile = db.get(Mahasiswa, user.id)
        if profile is None:
            db.add(Mahasiswa(id=user.id, angkatan_id=cohort.id))
            db.flush()
        elif profile.angkatan_id != cohort.id:
            raise ValueError(f"Mahasiswa {item.nim_nidn} sudah terdaftar pada angkatan berbeda")
        student_by_nim[item.nim_nidn] = user
        student_year_by_nim[item.nim_nidn] = item.tahun_masuk

    paket_rows = db.execute(
        select(KurikulumMK, MataKuliah.kode_mk)
        .join(MataKuliah, MataKuliah.id == KurikulumMK.mk_id)
        .where(KurikulumMK.kurikulum_id == kurikulum.id)
    ).all()
    paket_by_code = {kode: row for row, kode in paket_rows}
    cpl_by_code = {
        cpl.kode_cpl: cpl
        for cpl in db.scalars(select(MasterCPL).where(MasterCPL.kurikulum_id == kurikulum.id))
    }

    total_kelas_mk = 0
    nilai_created = 0
    nilai_existing = 0

    for period_item in payload.periode:
        periode = db.scalar(
            select(PeriodeAkademik).where(
                PeriodeAkademik.prodi_id == prodi.id,
                PeriodeAkademik.tahun_mulai == period_item.tahun_mulai,
                PeriodeAkademik.semester == period_item.semester,
            )
        )
        if periode is None:
            periode = PeriodeAkademik(
                prodi_id=prodi.id,
                tahun_mulai=period_item.tahun_mulai,
                semester=period_item.semester,
                status="Dibuka",
            )
            db.add(periode)
            db.flush()
            was_closed = False
        else:
            was_closed = periode.status == "Ditutup"

        if was_closed and period_item.status == "Dibuka":
            raise ValueError(
                f"Periode {periode.tahun_akademik} {periode.semester} sudah ditutup "
                "dan tidak dapat dibuka kembali oleh seed"
            )

        def assert_mutable(
            cur_periode: PeriodeAkademik = periode, closed: bool = was_closed
        ) -> None:
            if closed:
                raise ValueError(
                    f"Periode {cur_periode.tahun_akademik} {cur_periode.semester} sudah ditutup "
                    "dan tidak dapat ditambah data baru oleh seed"
                )

        class_by_key: dict[tuple[int, str], KelasPeriode] = {}
        for class_item in period_item.kelas:
            cohort = cohort_by_year[class_item.tahun_masuk]
            klass = db.scalar(
                select(KelasPeriode).where(
                    KelasPeriode.periode_id == periode.id,
                    KelasPeriode.angkatan_id == cohort.id,
                    KelasPeriode.kode_kelas == class_item.kode_kelas,
                )
            )
            if klass is None:
                assert_mutable()
                klass = KelasPeriode(
                    periode_id=periode.id,
                    angkatan_id=cohort.id,
                    kode_kelas=class_item.kode_kelas,
                    semester_studi=class_item.semester_studi,
                )
                db.add(klass)
                db.flush()
            elif klass.semester_studi != class_item.semester_studi:
                raise ValueError(
                    f"Semester studi kelas {class_item.kode_kelas} angkatan "
                    f"{class_item.tahun_masuk} tidak cocok dengan data yang ada"
                )
            class_by_key[(class_item.tahun_masuk, class_item.kode_kelas)] = klass

        active_students_by_class: dict[tuple[int, str], list[User]] = {}
        for roster_item in period_item.roster:
            student = student_by_nim[roster_item.nim_nidn]
            year = student_year_by_nim[roster_item.nim_nidn]
            klass = class_by_key[(year, roster_item.kode_kelas)]
            roster_row = db.scalar(
                select(MahasiswaPeriode).where(
                    MahasiswaPeriode.mahasiswa_id == student.id,
                    MahasiswaPeriode.periode_id == periode.id,
                )
            )
            if roster_row is None:
                assert_mutable()
                roster_row = MahasiswaPeriode(
                    mahasiswa_id=student.id,
                    periode_id=periode.id,
                    kelas_periode_id=klass.id,
                    status=roster_item.status,
                )
                db.add(roster_row)
                db.flush()
            elif roster_row.kelas_periode_id != klass.id or roster_row.status != roster_item.status:
                raise ValueError(
                    f"Roster mahasiswa {roster_item.nim_nidn} pada periode "
                    f"{periode.tahun_akademik} {periode.semester} bertabrakan"
                )
            if roster_item.status == "Aktif":
                active_students_by_class.setdefault((year, roster_item.kode_kelas), []).append(
                    student
                )

        kelas_mk_by_key: dict[tuple[int, str, str], KelasMK] = {}
        for assign in period_item.penugasan:
            klass = class_by_key[(assign.tahun_masuk, assign.kode_kelas)]
            paket_mk = paket_by_code.get(assign.kode_mk)
            if paket_mk is None:
                raise ValueError(
                    f"MK {assign.kode_mk} belum ada di kurikulum {kurikulum.kode_kurikulum}"
                )
            if paket_mk.semester != klass.semester_studi:
                raise ValueError(
                    f"MK {assign.kode_mk} (semester {paket_mk.semester}) tidak sesuai semester "
                    f"studi kelas {assign.kode_kelas} ({klass.semester_studi})"
                )
            dosen = lecturer_by_nidn[assign.dosen_nim_nidn]
            design = db.scalar(
                select(RancanganPenilaian).where(
                    RancanganPenilaian.periode_id == periode.id,
                    RancanganPenilaian.kurikulum_mk_id == paket_mk.id,
                    RancanganPenilaian.dosen_id == dosen.id,
                )
            )
            if design is None:
                assert_mutable()
                design = RancanganPenilaian(
                    periode_id=periode.id,
                    kurikulum_mk_id=paket_mk.id,
                    dosen_id=dosen.id,
                )
                db.add(design)
                db.flush()

            kelas_mk = db.scalar(
                select(KelasMK).where(
                    KelasMK.kelas_periode_id == klass.id,
                    KelasMK.kurikulum_mk_id == paket_mk.id,
                )
            )
            if kelas_mk is None:
                assert_mutable()
                kelas_mk = KelasMK(
                    kelas_periode_id=klass.id,
                    kurikulum_mk_id=paket_mk.id,
                    rancangan_id=design.id,
                )
                db.add(kelas_mk)
                db.flush()
            elif kelas_mk.rancangan_id != design.id:
                raise ValueError(
                    f"Penugasan MK {assign.kode_mk} di kelas {assign.kode_kelas} bertabrakan "
                    "dengan dosen lain"
                )
            kelas_mk_by_key[(assign.tahun_masuk, assign.kode_kelas, assign.kode_mk)] = kelas_mk
            total_kelas_mk += 1

            for student in active_students_by_class.get(
                (assign.tahun_masuk, assign.kode_kelas), []
            ):
                participant = db.scalar(
                    select(PesertaKelasMK).where(
                        PesertaKelasMK.kelas_mk_id == kelas_mk.id,
                        PesertaKelasMK.mahasiswa_id == student.id,
                    )
                )
                if participant is None:
                    assert_mutable()
                    repeated = db.scalar(
                        select(PesertaKelasMK.kelas_mk_id).where(
                            PesertaKelasMK.mahasiswa_id == student.id,
                            PesertaKelasMK.mk_id == paket_mk.mk_id,
                        )
                    )
                    if repeated is not None:
                        raise ValueError(
                            f"Mahasiswa {student.nim_nidn} sudah pernah mengambil MK {assign.kode_mk}"
                        )
                    db.add(
                        PesertaKelasMK(
                            kelas_mk_id=kelas_mk.id,
                            mahasiswa_id=student.id,
                            mk_id=paket_mk.mk_id,
                        )
                    )

        db.flush()

        for design_item in period_item.rancangan:
            created_cnt, existing_cnt = _seed_design_and_grades(
                db,
                kurikulum=kurikulum,
                periode=periode,
                was_closed=was_closed,
                design_item=design_item,
                paket_by_code=paket_by_code,
                cpl_by_code=cpl_by_code,
                lecturer_by_nidn=lecturer_by_nidn,
                student_by_nim=student_by_nim,
                kelas_mk_by_key=kelas_mk_by_key,
            )
            nilai_created += created_cnt
            nilai_existing += existing_cnt

        if period_item.status == "Ditutup" and periode.status == "Dibuka":
            before = _snapshot(periode)
            periode.status = "Ditutup"
            periode.ditutup_pada = datetime.now(UTC)
            periode.ditutup_oleh = admin.id
            db.flush()
            db.add(
                AuditLog(
                    aktor_id=admin.id,
                    periode_id=periode.id,
                    aksi="close",
                    entitas=periode.__tablename__,
                    entitas_id=periode.id,
                    alasan=(period_item.alasan_tutup or "").strip() or None,
                    sebelum=before,
                    sesudah=_snapshot(periode),
                )
            )

    db.flush()
    return {
        "prodi_id": str(prodi.id),
        "kurikulum_id": str(kurikulum.id),
        "dosen_total": len(payload.dosen),
        "mahasiswa_total": len(payload.mahasiswa),
        "periode_total": len(payload.periode),
        "kelas_mk_total": total_kelas_mk,
        "nilai_created": nilai_created,
        "nilai_existing": nilai_existing,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Seed demo operasional PNL OBE dari file JSON (password dari backend/.env)"
    )
    parser.add_argument(
        "file",
        type=Path,
        help="Path file JSON seed demo operasional (mis. seeds/demo_operasional_ti_2024.json)",
    )
    args = parser.parse_args()
    payload = load_demo_seed(args.file)
    config = DemoSeedSettings(_env_file=ENV_FILE)
    database = Database(config)
    try:
        with database.session_factory.begin() as db:
            summary = seed_demo_data(
                db,
                payload,
                dosen_password=config.seed_dosen_password,
                mahasiswa_password=config.seed_mahasiswa_password,
            )
        print(
            "Seed demo operasional selesai "
            f"(dosen={summary['dosen_total']}, mahasiswa={summary['mahasiswa_total']}, "
            f"periode={summary['periode_total']}, kelas_mk={summary['kelas_mk_total']}, "
            f"nilai baru={summary['nilai_created']}, nilai ada={summary['nilai_existing']}). "
            "Kredensial tidak ditampilkan."
        )
    finally:
        database.dispose()


if __name__ == "__main__":
    main()
