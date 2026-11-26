from decimal import Decimal
from uuid import UUID

import pytest
from conftest import BACKEND
from sqlalchemy import func, select

from app.core.security import create_access_token
from app.models import (
    AuditLog,
    KelasMK,
    KelasPeriode,
    Kurikulum,
    KurikulumMK,
    MataKuliah,
    NilaiMahasiswa,
    PeriodeAkademik,
    PesertaKelasMK,
    User,
)
from app.services.seed import seed
from app.services.seed_curriculum import load_curriculum_seed
from app.services.seed_demo import load_demo_seed, seed_demo_data

SEED_MK_JSON = BACKEND / "seeds" / "kurikulum_ti_2024_mata_kuliah.json"
SEED_CPL_JSON = BACKEND / "seeds" / "kurikulum_ti_2024_cpl.json"
SEED_MK_CPL_JSON = BACKEND / "seeds" / "kurikulum_ti_2024_mk_cpl.json"
SEED_DEMO_JSON = BACKEND / "seeds" / "demo_operasional_ti_2024.json"


def _seed_all(db, seed_config) -> dict[str, str]:
    return seed(
        db,
        seed_config,
        kurikulum_file=[SEED_MK_JSON, SEED_CPL_JSON, SEED_MK_CPL_JSON],
        demo_file=SEED_DEMO_JSON,
    )


def _auth_headers(db, settings, email: str) -> dict[str, str]:
    user = db.scalar(select(User).where(User.email == email))
    assert user is not None
    return {"Authorization": "Bearer " + create_access_token(user, settings)}


def test_demo_seed_json_valid_and_references_ti_2024():
    raw = SEED_DEMO_JSON.read_text(encoding="utf-8")
    assert '"password"' not in raw.lower()
    assert '"password_hash"' not in raw.lower()

    mk_payload = load_curriculum_seed(SEED_MK_JSON)
    mk_cpl_payload = load_curriculum_seed(SEED_MK_CPL_JSON)
    demo_payload = load_demo_seed(SEED_DEMO_JSON)

    assert len(demo_payload.dosen) == 3
    assert len(demo_payload.angkatan) == 2
    assert len(demo_payload.mahasiswa) == 9
    assert len(demo_payload.periode) == 2
    assert demo_payload.periode[0].status == "Ditutup"
    assert demo_payload.periode[1].status == "Dibuka"

    mk_codes = {item.kode_mk for item in mk_payload.mata_kuliah}
    allowed_cpls = {
        entry.kode_mk: {link.kode_cpl for link in entry.cpl} for entry in mk_cpl_payload.mk_cpl
    }
    for period in demo_payload.periode:
        for assign in period.penugasan:
            assert assign.kode_mk in mk_codes
        for design in period.rancangan:
            assert design.kode_mk in mk_codes
            for cpmk in design.cpmk:
                assert set(cpmk.cpl) <= allowed_cpls[design.kode_mk]


def test_seed_demo_idempotent_and_preserves_manual_grade_edits(db, seed_config):
    first = _seed_all(db, seed_config)
    db.commit()
    second = _seed_all(db, seed_config)
    db.commit()

    assert first == second

    kurikulum = db.get(Kurikulum, UUID(first["kurikulum_id"]))
    assert kurikulum is not None
    assert kurikulum.status == "Aktif"

    periods = list(
        db.scalars(
            select(PeriodeAkademik).order_by(PeriodeAkademik.tahun_mulai, PeriodeAkademik.id)
        )
    )
    assert len(periods) == 2
    assert periods[0].status == "Ditutup"
    assert periods[1].status == "Dibuka"

    def class_course_for(periode_id: UUID, kode_kelas: str, kode_mk: str) -> KelasMK:
        row = db.scalar(
            select(KelasMK)
            .join(KelasPeriode, KelasPeriode.id == KelasMK.kelas_periode_id)
            .join(KurikulumMK, KurikulumMK.id == KelasMK.kurikulum_mk_id)
            .join(MataKuliah, MataKuliah.id == KurikulumMK.mk_id)
            .where(
                KelasPeriode.periode_id == periode_id,
                KelasPeriode.kode_kelas == kode_kelas,
                MataKuliah.kode_mk == kode_mk,
            )
        )
        assert row is not None
        return row

    pbo_a = class_course_for(periods[1].id, "A", "TI-24301")
    pbo_b = class_course_for(periods[1].id, "B", "TI-24301")
    assert pbo_a.rancangan_id == pbo_b.rancangan_id

    rpl_a = class_course_for(periods[1].id, "A", "TI-24302")
    rpl_b = class_course_for(periods[1].id, "B", "TI-24302")
    assert rpl_a.rancangan_id != rpl_b.rancangan_id

    for email in ("mhs.cuti@demo.pnl.ac.id", "mhs.nonaktif@demo.pnl.ac.id"):
        student = db.scalar(select(User).where(User.email == email))
        assert student is not None
        cnt = db.scalar(
            select(func.count())
            .select_from(PesertaKelasMK)
            .join(KelasMK, KelasMK.id == PesertaKelasMK.kelas_mk_id)
            .join(KelasPeriode, KelasPeriode.id == KelasMK.kelas_periode_id)
            .where(
                PesertaKelasMK.mahasiswa_id == student.id,
                KelasPeriode.periode_id == periods[1].id,
            )
        )
        assert cnt == 0

    audit_actions = set(db.scalars(select(AuditLog.aksi)))
    assert {"activate", "close", "create"} <= audit_actions

    edited_grade = db.scalar(
        select(NilaiMahasiswa)
        .where(NilaiMahasiswa.kelas_mk_id == pbo_a.id)
        .order_by(NilaiMahasiswa.id)
        .limit(1)
    )
    assert edited_grade is not None
    edited_grade.nilai_mentah = Decimal("99.50")
    db.commit()

    rerun = seed_demo_data(
        db,
        load_demo_seed(SEED_DEMO_JSON),
        dosen_password=seed_config.seed_dosen_password,
        mahasiswa_password=seed_config.seed_mahasiswa_password,
    )
    db.commit()
    assert rerun["nilai_created"] == 0

    db.refresh(edited_grade)
    assert edited_grade.nilai_mentah == Decimal("99.50")


def test_seed_demo_rollback_on_missing_curriculum_prereq(db, seed_config):
    seed(db, seed_config)
    db.commit()

    demo_payload = load_demo_seed(SEED_DEMO_JSON)
    with pytest.raises(ValueError), db.begin():
        seed_demo_data(
            db,
            demo_payload,
            dosen_password=seed_config.seed_dosen_password,
            mahasiswa_password=seed_config.seed_mahasiswa_password,
        )

    assert db.scalar(select(func.count()).select_from(PeriodeAkademik)) == 0
    assert db.scalar(select(func.count()).select_from(User)) == 1


def test_seed_demo_end_to_end_apis_all_roles(db, seed_config, client, settings):
    seeded = _seed_all(db, seed_config)
    db.commit()

    periods = list(
        db.scalars(
            select(PeriodeAkademik).order_by(PeriodeAkademik.tahun_mulai, PeriodeAkademik.id)
        )
    )
    genap_id = str(periods[0].id)
    ganjil_id = str(periods[1].id)
    kurikulum_id = seeded["kurikulum_id"]

    # Admin API verification
    admin_headers = _auth_headers(db, settings, str(seed_config.seed_admin_email).lower())
    for pid in (genap_id, ganjil_id):
        rep = client.get(
            "/api/v1/laporan/prodi",
            params={"periode_id": pid, "kurikulum_id": kurikulum_id},
            headers=admin_headers,
        )
        assert rep.status_code == 200, rep.text
        assert rep.json()["rekap_cpl"]

    audit_resp = client.get("/api/v1/audit-log", params={"limit": 100}, headers=admin_headers)
    assert audit_resp.status_code == 200
    assert audit_resp.json()
    activate_logs = client.get(
        "/api/v1/audit-log", params={"aksi": "activate"}, headers=admin_headers
    )
    assert activate_logs.status_code == 200
    assert len(activate_logs.json()) == 1
    close_logs = client.get(
        "/api/v1/audit-log",
        params={"aksi": "close", "periode_id": genap_id},
        headers=admin_headers,
    )
    assert close_logs.status_code == 200
    assert len(close_logs.json()) == 1

    rpl_a = db.scalar(
        select(KelasMK)
        .join(KelasPeriode, KelasPeriode.id == KelasMK.kelas_periode_id)
        .join(KurikulumMK, KurikulumMK.id == KelasMK.kurikulum_mk_id)
        .join(MataKuliah, MataKuliah.id == KurikulumMK.mk_id)
        .where(
            KelasPeriode.periode_id == periods[1].id,
            KelasPeriode.kode_kelas == "A",
            MataKuliah.kode_mk == "TI-24302",
        )
    )
    rpl_b = db.scalar(
        select(KelasMK)
        .join(KelasPeriode, KelasPeriode.id == KelasMK.kelas_periode_id)
        .join(KurikulumMK, KurikulumMK.id == KelasMK.kurikulum_mk_id)
        .join(MataKuliah, MataKuliah.id == KurikulumMK.mk_id)
        .where(
            KelasPeriode.periode_id == periods[1].id,
            KelasPeriode.kode_kelas == "B",
            MataKuliah.kode_mk == "TI-24302",
        )
    )
    assert rpl_a is not None and rpl_b is not None
    admin_cross = client.get(
        "/api/v1/laporan/lintas-kelas",
        params={"periode_id": ganjil_id, "kelas_mk_ids": [str(rpl_a.id), str(rpl_b.id)]},
        headers=admin_headers,
    )
    assert admin_cross.status_code == 200

    # Dosen 1 (NIDN-DEMO-01) verification
    d1_headers = _auth_headers(db, settings, "dosen.rpl@demo.pnl.ac.id")
    d1_designs = client.get(
        "/api/v1/rancangan-penilaian",
        params={"periode_id": ganjil_id, "limit": 100},
        headers=d1_headers,
    )
    assert d1_designs.status_code == 200
    shared_pbo = [d for d in d1_designs.json() if len(d["kelas_pengguna"]) == 2]
    assert shared_pbo
    pbo_design = next(
        d
        for d in shared_pbo
        if any(k["label"] == "TI-2A" for k in d["kelas_pengguna"]) and d["sudah_ada_nilai"]
    )
    assert pbo_design["siap_dinilai"] is True
    assert pbo_design["struktur_terkunci"] is True

    pbo_classes = {k["label"]: k["kelas_mk_id"] for k in pbo_design["kelas_pengguna"]}
    pbo_a_id = pbo_classes["TI-2A"]
    pbo_b_id = pbo_classes["TI-2B"]
    # Identify TI-24301 specifically via /kelas-mk
    d1_classes = client.get(
        "/api/v1/kelas-mk", params={"periode_id": ganjil_id}, headers=d1_headers
    )
    assert d1_classes.status_code == 200
    ti2a_pbo_id = next(
        c["id"] for c in d1_classes.json() if c["kode_mk"] == "TI-24301" and c["kelas"] == "TI-2A"
    )
    ti2b_pbo_id = next(
        c["id"] for c in d1_classes.json() if c["kode_mk"] == "TI-24301" and c["kelas"] == "TI-2B"
    )
    assert pbo_a_id or pbo_b_id

    cap_pbo_a = client.get(f"/api/v1/kelas-mk/{ti2a_pbo_id}/capaian", headers=d1_headers)
    assert cap_pbo_a.status_code == 200
    mk_avg = next(item for item in cap_pbo_a.json()["rekap"] if item["jenis"] == "Mata kuliah")
    assert mk_avg["mahasiswa_lengkap"] == 2
    assert mk_avg["total_mahasiswa"] == 3

    d1_cross = client.get(
        "/api/v1/laporan/lintas-kelas",
        params={"periode_id": ganjil_id, "kelas_mk_ids": [ti2a_pbo_id, ti2b_pbo_id]},
        headers=d1_headers,
    )
    assert d1_cross.status_code == 200

    # Isolation check: NIDN-DEMO-01 cannot inspect NIDN-DEMO-02's TI-24302 class B
    forbidden_class = client.get(f"/api/v1/kelas-mk/{rpl_b.id}", headers=d1_headers)
    assert forbidden_class.status_code == 404

    # Dosen 2 (NIDN-DEMO-02) incomplete 70% draft check on TI-24502 (TI-3C)
    d2_headers = _auth_headers(db, settings, "dosen.jarkom@demo.pnl.ac.id")
    d2_classes = client.get(
        "/api/v1/kelas-mk", params={"periode_id": ganjil_id}, headers=d2_headers
    )
    assert d2_classes.status_code == 200
    ti3c_sec_id = next(
        c["id"] for c in d2_classes.json() if c["kode_mk"] == "TI-24502" and c["kelas"] == "TI-3C"
    )
    sec_design = client.get(
        f"/api/v1/kelas-mk/{ti3c_sec_id}/rancangan-penilaian", headers=d2_headers
    )
    assert sec_design.status_code == 200
    sec_json = sec_design.json()
    assert sec_json["siap_dinilai"] is False
    assert sec_json["struktur_terkunci"] is False
    assert Decimal(str(sec_json["total_bobot"])) == Decimal("70.00")

    # Mahasiswa a1: cumulative across Sem 2 + Sem 3 covers all 12 CPLs as Lengkap
    a1_headers = _auth_headers(db, settings, "mhs.a1@demo.pnl.ac.id")
    a1_cum = client.get(
        "/api/v1/capaian/saya",
        params={"periode_id": ganjil_id, "kumulatif": True},
        headers=a1_headers,
    )
    assert a1_cum.status_code == 200
    a1_cpls = [item for item in a1_cum.json()["hasil"] if item["jenis"] == "CPL"]
    assert [item["kode"] for item in a1_cpls] == [f"CPL-{i:02d}" for i in range(1, 13)]
    for item in a1_cpls:
        assert item["status"] == "Lengkap"
        assert item["capaian"] is not None

    # Mahasiswa a2: valid 0.00 score preserved
    a2_headers = _auth_headers(db, settings, "mhs.a2@demo.pnl.ac.id")
    a2_detail = client.get(f"/api/v1/mahasiswa/kelas-mk/{ti2a_pbo_id}/rincian", headers=a2_headers)
    assert a2_detail.status_code == 200
    kuis = next(i for i in a2_detail.json()["instrumen"] if i["nama_instrumen"] == "Kuis 1")
    assert kuis["nilai_mentah"] == "0.00"
    assert kuis["status"] == "Sudah diinput"

    # Mahasiswa a3: missing UAS score shown as Belum diinput
    a3_headers = _auth_headers(db, settings, "mhs.a3@demo.pnl.ac.id")
    a3_detail = client.get(f"/api/v1/mahasiswa/kelas-mk/{ti2a_pbo_id}/rincian", headers=a3_headers)
    assert a3_detail.status_code == 200
    uas = next(i for i in a3_detail.json()["instrumen"] if i["nama_instrumen"] == "UAS")
    assert uas["nilai_mentah"] is None
    assert uas["status"] == "Belum diinput"

    # Mahasiswa cuti: TI-1A (9 MK) in Genap, TI-K (0 MK) in Ganjil
    cuti_headers = _auth_headers(db, settings, "mhs.cuti@demo.pnl.ac.id")
    cuti_periods = client.get("/api/v1/mahasiswa/periode", headers=cuti_headers)
    assert cuti_periods.status_code == 200
    by_pid = {item["periode_id"]: item for item in cuti_periods.json()}
    assert by_pid[genap_id]["kelas"] == "TI-1A"
    assert by_pid[genap_id]["status_mahasiswa"] == "Aktif"
    assert by_pid[genap_id]["jumlah_kelas_mk"] == 9
    assert by_pid[ganjil_id]["kelas"] == "TI-K"
    assert by_pid[ganjil_id]["status_mahasiswa"] == "Cuti"
    assert by_pid[ganjil_id]["jumlah_kelas_mk"] == 0

    cuti_ganjil_classes = client.get(
        "/api/v1/kelas-mk", params={"periode_id": ganjil_id}, headers=cuti_headers
    )
    assert cuti_ganjil_classes.status_code == 200
    assert cuti_ganjil_classes.json() == []

    # Mahasiswa nonaktif: TI-K (Nonaktif, 0 MK) in Ganjil
    nonaktif_headers = _auth_headers(db, settings, "mhs.nonaktif@demo.pnl.ac.id")
    nonaktif_periods = client.get("/api/v1/mahasiswa/periode", headers=nonaktif_headers)
    assert nonaktif_periods.status_code == 200
    assert nonaktif_periods.json()[0]["kelas"] == "TI-K"
    assert nonaktif_periods.json()[0]["status_mahasiswa"] == "Nonaktif"
    assert nonaktif_periods.json()[0]["jumlah_kelas_mk"] == 0

    # Mahasiswa c1 (TI-3C, Angkatan 2024): draft Sem 5 courses report Belum siap dinilai
    c1_headers = _auth_headers(db, settings, "mhs.c1@demo.pnl.ac.id")
    c1_att = client.get(
        "/api/v1/capaian/saya", params={"periode_id": ganjil_id}, headers=c1_headers
    )
    assert c1_att.status_code == 200
    c1_cpls = [item for item in c1_att.json()["hasil"] if item["jenis"] == "CPL"]
    assert c1_cpls
    for item in c1_cpls:
        assert item["status"] == "Belum siap dinilai"
        assert item["capaian"] is None
