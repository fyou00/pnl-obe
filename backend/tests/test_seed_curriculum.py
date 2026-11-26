from collections import Counter
from uuid import UUID

import pytest
from conftest import BACKEND
from pydantic import ValidationError
from sqlalchemy import delete, func, select

from app.core.security import create_access_token
from app.models import (
    MKCPL,
    PLCPL,
    Kurikulum,
    KurikulumMK,
    MasterCPL,
    MataKuliah,
    Prodi,
    ProfilLulusan,
    User,
)
from app.services.seed import seed
from app.services.seed_curriculum import (
    CourseSeedItem,
    CplSeedItem,
    CurriculumSeedFile,
    KurikulumSeed,
    MkCplSeedItem,
    MkCplSeedLink,
    ProdiSeed,
    load_curriculum_seed,
    seed_curriculum_data,
)

SEED_JSON = BACKEND / "seeds" / "kurikulum_ti_2024_mata_kuliah.json"
SEED_CPL_JSON = BACKEND / "seeds" / "kurikulum_ti_2024_cpl.json"
SEED_PL_JSON = BACKEND / "seeds" / "kurikulum_ti_2024_profil_lulusan.json"
SEED_MK_CPL_JSON = BACKEND / "seeds" / "kurikulum_ti_2024_mk_cpl.json"
SEED_DEMO_JSON = BACKEND / "seeds" / "demo_operasional_ti_2024.json"


def test_ti_2024_seed_json_valid_and_complete():
    payload = load_curriculum_seed(SEED_JSON)
    assert payload.prodi.kode_prodi == "TI"
    assert payload.kurikulum.kode_kurikulum == "TI-2024"
    assert len(payload.mata_kuliah) == 61
    assert sum(item.sks for item in payload.mata_kuliah) == 144

    sem_counts = Counter(item.semester for item in payload.mata_kuliah)
    sem_sks = Counter()
    for item in payload.mata_kuliah:
        sem_sks[item.semester] += item.sks

    assert dict(sem_counts) == {1: 10, 2: 9, 3: 10, 4: 10, 5: 10, 6: 9, 7: 1, 8: 2}
    assert dict(sem_sks) == {1: 20, 2: 18, 3: 20, 4: 20, 5: 20, 6: 18, 7: 20, 8: 8}

    by_code = {item.kode_mk: item for item in payload.mata_kuliah}
    assert by_code["TI-24406"].semester == 4
    assert by_code["TI-24406"].nama_mk == "Administrasi dan Manajemen Server"
    assert by_code["TIK-2402"].semester == 6
    assert by_code["TIK-2402"].nama_mk == "Metodologi Penelitian"

    artifacts = ("sepert ", "berbaga ", "mengidentifikas ", "dapa ", "memenuh ", "d bawah")
    for item in payload.mata_kuliah:
        assert item.deskripsi_singkat.endswith(".")
        assert item.learning_outcome is not None
        assert item.learning_outcome.endswith(".")
        for text in (item.deskripsi_singkat, item.learning_outcome):
            for artifact in artifacts:
                assert artifact not in text


def test_seed_curriculum_idempotent_and_preserves_manual_edits(db, seed_config):
    first = seed(db, seed_config, kurikulum_file=SEED_JSON)
    db.commit()
    second = seed(db, seed_config, kurikulum_file=SEED_JSON)
    db.commit()

    assert first == second
    assert db.scalar(select(func.count()).select_from(MataKuliah)) == 61
    assert db.scalar(select(func.count()).select_from(KurikulumMK)) == 61

    kurikulum = db.get(Kurikulum, UUID(first["kurikulum_id"]))
    assert kurikulum is not None
    assert kurikulum.status == "Draft"

    edited_mk = db.scalar(select(MataKuliah).where(MataKuliah.kode_mk == "TI-24101"))
    cleared_mk = db.scalar(select(MataKuliah).where(MataKuliah.kode_mk == "TI-24102"))
    assert edited_mk is not None and cleared_mk is not None
    edited_mk.deskripsi = "Deskripsi ubahan manual"
    cleared_mk.deskripsi = None
    db.commit()

    payload = load_curriculum_seed(SEED_JSON)
    summary = seed_curriculum_data(db, payload)
    db.commit()

    assert summary["mk_created"] == 0
    assert summary["mk_existing"] == 61
    assert summary["paket_created"] == 0
    assert summary["paket_existing"] == 61

    db.refresh(edited_mk)
    db.refresh(cleared_mk)
    assert edited_mk.deskripsi == "Deskripsi ubahan manual"
    assert cleared_mk.deskripsi is not None
    assert "Learning Outcome:" in cleared_mk.deskripsi


def test_seed_curriculum_rollback_on_conflict(db):
    prodi = Prodi(kode_prodi="TI", nama_prodi="Teknik Informatika", jenjang="D4")
    db.add(prodi)
    db.flush()
    db.add(MataKuliah(prodi_id=prodi.id, kode_mk="TI-24101", nama_mk="Nama Berbeda"))
    db.commit()

    payload = load_curriculum_seed(SEED_JSON)
    with pytest.raises(ValueError), db.begin():
        seed_curriculum_data(db, payload)

    assert db.scalar(select(func.count()).select_from(Kurikulum)) == 0
    assert db.scalar(select(func.count()).select_from(MataKuliah)) == 1


def test_seed_curriculum_respects_active_curriculum_immutability(db):
    payload = load_curriculum_seed(SEED_JSON)
    with db.begin():
        summary = seed_curriculum_data(db, payload)

    kurikulum = db.get(Kurikulum, UUID(summary["kurikulum_id"]))
    assert kurikulum is not None
    kurikulum.status = "Aktif"
    db.commit()

    with db.begin():
        rerun = seed_curriculum_data(db, payload)
    assert rerun["paket_created"] == 0
    assert rerun["paket_existing"] == 61

    extra_course = CourseSeedItem(
        no=62,
        kode_mk="TI-24999",
        nama_mk="Mata Kuliah Tambahan",
        semester=8,
        sks=2,
        jam_per_minggu=2,
        prasyarat=None,
        deskripsi_singkat="Deskripsi mata kuliah tambahan.",
        learning_outcome="Capaian pembelajaran tambahan.",
    )
    modified = payload.model_copy(update={"mata_kuliah": [*payload.mata_kuliah, extra_course]})
    with pytest.raises(ValueError), db.begin():
        seed_curriculum_data(db, modified)

    assert db.scalar(select(func.count()).select_from(MataKuliah)) == 61
    assert db.scalar(select(func.count()).select_from(KurikulumMK)) == 61

    removed = db.scalar(
        select(KurikulumMK)
        .join(MataKuliah, MataKuliah.id == KurikulumMK.mk_id)
        .where(KurikulumMK.kurikulum_id == kurikulum.id, MataKuliah.kode_mk == "TI-24802")
    )
    assert removed is not None
    db.execute(delete(KurikulumMK).where(KurikulumMK.id == removed.id))
    db.commit()

    with pytest.raises(ValueError), db.begin():
        seed_curriculum_data(db, payload)

    assert db.scalar(select(func.count()).select_from(KurikulumMK)) == 60


def test_seed_curriculum_accessible_via_admin_api(db, seed_config, client, settings):
    seeded = seed(db, seed_config, kurikulum_file=SEED_JSON)
    db.commit()

    admin = db.get(User, UUID(seeded["admin_id"]))
    assert admin is not None
    client.headers["Authorization"] = "Bearer " + create_access_token(admin, settings)

    mk_resp = client.get("/api/v1/mata-kuliah?limit=100")
    assert mk_resp.status_code == 200
    assert len(mk_resp.json()) == 61

    kur_resp = client.get("/api/v1/kurikulum")
    assert kur_resp.status_code == 200
    items = kur_resp.json()
    matched = [item for item in items if item["kode_kurikulum"] == "TI-2024"]
    assert len(matched) == 1
    assert matched[0]["status"] == "Draft"

    paket_resp = client.get(f"/api/v1/kurikulum/{matched[0]['id']}/mata-kuliah?limit=100")
    assert paket_resp.status_code == 200
    paket_items = paket_resp.json()
    assert len(paket_items) == 61
    assert sum(item["sks"] for item in paket_items) == 144
    for item in paket_items:
        assert item["deskripsi"]
        assert "Learning Outcome:" in item["deskripsi"]


def test_ti_2024_cpl_seed_json_valid_and_complete():
    payload = load_curriculum_seed(SEED_CPL_JSON)
    assert payload.prodi.kode_prodi == "TI"
    assert payload.kurikulum.kode_kurikulum == "TI-2024"
    assert payload.mata_kuliah == []
    assert len(payload.cpl) == 12
    assert [item.kode_cpl for item in payload.cpl] == [f"CPL-{i:02d}" for i in range(1, 13)]

    kat_counts = Counter(item.kategori for item in payload.cpl)
    assert dict(kat_counts) == {"S": 2, "KU": 2, "P": 1, "KK": 7}

    for item in payload.cpl:
        assert item.nasional is False
        assert item.unsur
        assert item.kategori in item.unsur
        assert item.deskripsi.startswith("[A] Mahasiswa Teknik Informatika [B]")
        assert item.deskripsi.endswith(".")

    by_code = {item.kode_cpl: item for item in payload.cpl}
    assert by_code["CPL-01"].unsur == ["S", "KU"]
    assert by_code["CPL-07"].unsur == ["S", "KU", "KK"]
    assert by_code["CPL-10"].unsur == ["P", "KU"]
    assert "tingkat efisiensi tinggi (P3)." in by_code["CPL-12"].deskripsi


def test_cpl_seed_validation_rules():
    with pytest.raises(ValidationError):
        CplSeedItem(kode_cpl="CPL-99", kategori="KK", nasional=True, deskripsi="Test.")
    with pytest.raises(ValidationError):
        CplSeedItem(kode_cpl="CPL-99", kategori="S", unsur=["P", "KK"], deskripsi="Test.")
    with pytest.raises(ValidationError):
        CurriculumSeedFile(
            prodi=ProdiSeed(kode_prodi="TI", nama_prodi="Teknik Informatika", jenjang="D4"),
            kurikulum=KurikulumSeed(kode_kurikulum="TI-2024", nama="Kurikulum TI 2024"),
            mata_kuliah=[],
            cpl=[],
        )


def test_seed_cpl_idempotent_with_mk_and_preserves_manual_edits(db, seed_config):
    first = seed(db, seed_config, kurikulum_file=[SEED_JSON, SEED_CPL_JSON])
    db.commit()
    second = seed(db, seed_config, kurikulum_file=[SEED_JSON, SEED_CPL_JSON])
    db.commit()

    assert first == second
    assert db.scalar(select(func.count()).select_from(Kurikulum)) == 1
    assert db.scalar(select(func.count()).select_from(MataKuliah)) == 61
    assert db.scalar(select(func.count()).select_from(KurikulumMK)) == 61
    assert db.scalar(select(func.count()).select_from(MasterCPL)) == 12

    kurikulum = db.get(Kurikulum, UUID(first["kurikulum_id"]))
    assert kurikulum is not None
    assert kurikulum.kode_kurikulum == "TI-2024"
    assert kurikulum.status == "Draft"

    prodi_id = UUID(first["prodi_id"])
    cpls = list(db.scalars(select(MasterCPL).where(MasterCPL.kurikulum_id == kurikulum.id)))
    assert len(cpls) == 12
    assert all(cpl.prodi_id == prodi_id for cpl in cpls)

    edited_cpl = db.scalar(
        select(MasterCPL).where(
            MasterCPL.kurikulum_id == kurikulum.id, MasterCPL.kode_cpl == "CPL-01"
        )
    )
    assert edited_cpl is not None
    edited_cpl.deskripsi = "Deskripsi CPL ubahan manual"
    db.commit()

    summary = seed_curriculum_data(db, load_curriculum_seed(SEED_CPL_JSON))
    db.commit()
    assert summary["cpl_created"] == 0
    assert summary["cpl_existing"] == 12

    db.refresh(edited_cpl)
    assert edited_cpl.deskripsi == "Deskripsi CPL ubahan manual"


def test_seed_cpl_rollback_on_conflict_and_active_immutability(db):
    cpl_payload = load_curriculum_seed(SEED_CPL_JSON)
    prodi = Prodi(
        kode_prodi=cpl_payload.prodi.kode_prodi,
        nama_prodi=cpl_payload.prodi.nama_prodi,
        jenjang=cpl_payload.prodi.jenjang,
    )
    db.add(prodi)
    db.flush()
    kurikulum = Kurikulum(
        prodi_id=prodi.id,
        kode_kurikulum=cpl_payload.kurikulum.kode_kurikulum,
        nama=cpl_payload.kurikulum.nama,
        status="Draft",
    )
    db.add(kurikulum)
    db.flush()
    conflict_cpl = MasterCPL(
        kurikulum_id=kurikulum.id,
        prodi_id=prodi.id,
        kode_cpl="CPL-01",
        kategori="KU",
        deskripsi="Konflik",
    )
    db.add(conflict_cpl)
    db.commit()

    with pytest.raises(ValueError), db.begin():
        seed_curriculum_data(db, cpl_payload)

    assert db.scalar(select(func.count()).select_from(MasterCPL)) == 1

    existing_cpl = db.get(MasterCPL, conflict_cpl.id)
    assert existing_cpl is not None
    existing_cpl.kategori = "S"
    db.commit()

    with db.begin():
        summary = seed_curriculum_data(db, cpl_payload)
    assert summary["cpl_created"] == 11
    assert summary["cpl_existing"] == 1
    assert db.scalar(select(func.count()).select_from(MasterCPL)) == 12

    kurikulum_row = db.get(Kurikulum, kurikulum.id)
    assert kurikulum_row is not None
    kurikulum_row.status = "Aktif"
    db.commit()

    with db.begin():
        rerun = seed_curriculum_data(db, cpl_payload)
    assert rerun["cpl_created"] == 0
    assert rerun["cpl_existing"] == 12

    extra_cpl = CplSeedItem(
        kode_cpl="CPL-13",
        kategori="KK",
        nasional=False,
        deskripsi="CPL tambahan.",
    )
    modified = cpl_payload.model_copy(update={"cpl": [*cpl_payload.cpl, extra_cpl]})
    with pytest.raises(ValueError), db.begin():
        seed_curriculum_data(db, modified)

    assert db.scalar(select(func.count()).select_from(MasterCPL)) == 12


def test_seed_cpl_accessible_via_admin_api(db, seed_config, client, settings):
    seeded = seed(db, seed_config, kurikulum_file=[SEED_JSON, SEED_CPL_JSON])
    db.commit()

    admin = db.get(User, UUID(seeded["admin_id"]))
    assert admin is not None
    client.headers["Authorization"] = "Bearer " + create_access_token(admin, settings)

    resp = client.get(f"/api/v1/kurikulum/{seeded['kurikulum_id']}/cpl?limit=100")
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 12
    assert [item["kode_cpl"] for item in items] == [f"CPL-{i:02d}" for i in range(1, 13)]
    for item in items:
        assert item["prodi_id"] == seeded["prodi_id"]
        assert item["deskripsi"]


def test_ti_2024_mk_cpl_seed_json_valid_and_complete():
    mk_payload = load_curriculum_seed(SEED_JSON)
    cpl_payload = load_curriculum_seed(SEED_CPL_JSON)
    mk_cpl_payload = load_curriculum_seed(SEED_MK_CPL_JSON)

    assert len(mk_cpl_payload.mk_cpl) == 61
    assert [entry.kode_mk for entry in mk_cpl_payload.mk_cpl] == [
        item.kode_mk for item in mk_payload.mata_kuliah
    ]

    expected_cpls = {item.kode_cpl for item in cpl_payload.cpl}
    referenced_cpls = {link.kode_cpl for entry in mk_cpl_payload.mk_cpl for link in entry.cpl}
    assert referenced_cpls == expected_cpls

    total_links = sum(len(entry.cpl) for entry in mk_cpl_payload.mk_cpl)
    assert total_links == 118

    for entry in mk_cpl_payload.mk_cpl:
        assert [link.urutan_rps for link in entry.cpl] == list(range(1, len(entry.cpl) + 1))


def test_mk_cpl_seed_validation_rules():
    with pytest.raises(ValidationError):
        MkCplSeedItem(kode_mk="TI-24101", cpl=[])
    with pytest.raises(ValidationError):
        MkCplSeedItem(
            kode_mk="TI-24101",
            cpl=[
                MkCplSeedLink(kode_cpl="CPL-02", urutan_rps=1),
                MkCplSeedLink(kode_cpl="CPL-02", urutan_rps=2),
            ],
        )
    with pytest.raises(ValidationError):
        MkCplSeedLink(kode_cpl="CPL-02", urutan_rps=0)
    with pytest.raises(ValidationError):
        CurriculumSeedFile(
            prodi=ProdiSeed(kode_prodi="TI", nama_prodi="Teknik Informatika", jenjang="D4"),
            kurikulum=KurikulumSeed(kode_kurikulum="TI-2024", nama="Kurikulum TI 2024"),
            mk_cpl=[
                MkCplSeedItem(
                    kode_mk="TI-24101", cpl=[MkCplSeedLink(kode_cpl="CPL-02", urutan_rps=1)]
                ),
                MkCplSeedItem(
                    kode_mk="TI-24101", cpl=[MkCplSeedLink(kode_cpl="CPL-04", urutan_rps=1)]
                ),
            ],
        )


def test_seed_mk_cpl_idempotent_and_preserves_manual_edits(db, seed_config):
    first = seed(db, seed_config, kurikulum_file=[SEED_JSON, SEED_CPL_JSON, SEED_MK_CPL_JSON])
    db.commit()
    second = seed(db, seed_config, kurikulum_file=[SEED_JSON, SEED_CPL_JSON, SEED_MK_CPL_JSON])
    db.commit()

    assert first == second
    assert db.scalar(select(func.count()).select_from(KurikulumMK)) == 61
    assert db.scalar(select(func.count()).select_from(MasterCPL)) == 12
    assert db.scalar(select(func.count()).select_from(MKCPL)) == 118

    kurikulum_id = UUID(first["kurikulum_id"])
    links = list(
        db.scalars(
            select(MKCPL)
            .join(KurikulumMK, KurikulumMK.id == MKCPL.kurikulum_mk_id)
            .where(KurikulumMK.kurikulum_id == kurikulum_id)
            .order_by(MKCPL.kurikulum_mk_id, MKCPL.cpl_id)
        )
    )
    edited_link = links[0]
    cleared_link = links[1]
    edited_link.urutan_rps = 99
    cleared_link.urutan_rps = None
    db.commit()

    summary = seed_curriculum_data(db, load_curriculum_seed(SEED_MK_CPL_JSON))
    db.commit()
    assert summary["mk_cpl_created"] == 0
    assert summary["mk_cpl_existing"] == 118

    db.refresh(edited_link)
    db.refresh(cleared_link)
    assert edited_link.urutan_rps == 99
    assert cleared_link.urutan_rps is not None


def test_seed_mk_cpl_rejects_missing_prereq_and_active_immutability(db):
    mk_cpl_payload = load_curriculum_seed(SEED_MK_CPL_JSON)
    with pytest.raises(ValueError), db.begin():
        seed_curriculum_data(db, mk_cpl_payload)

    assert db.scalar(select(func.count()).select_from(Kurikulum)) == 0
    assert db.scalar(select(func.count()).select_from(MKCPL)) == 0
    db.rollback()

    with db.begin():
        seed_curriculum_data(db, load_curriculum_seed(SEED_JSON))
        seed_curriculum_data(db, load_curriculum_seed(SEED_CPL_JSON))
        summary = seed_curriculum_data(db, mk_cpl_payload)

    kurikulum = db.get(Kurikulum, UUID(summary["kurikulum_id"]))
    assert kurikulum is not None
    kurikulum.status = "Aktif"
    db.commit()

    with db.begin():
        rerun = seed_curriculum_data(db, mk_cpl_payload)
    assert rerun["mk_cpl_created"] == 0
    assert rerun["mk_cpl_existing"] == 118

    updated_first = mk_cpl_payload.mk_cpl[0].model_copy(
        update={
            "cpl": [
                *mk_cpl_payload.mk_cpl[0].cpl,
                MkCplSeedLink(kode_cpl="CPL-12", urutan_rps=4),
            ]
        }
    )
    modified = mk_cpl_payload.model_copy(
        update={"mk_cpl": [updated_first, *mk_cpl_payload.mk_cpl[1:]]}
    )
    with pytest.raises(ValueError), db.begin():
        seed_curriculum_data(db, modified)

    assert db.scalar(select(func.count()).select_from(MKCPL)) == 118


def test_seed_full_ti_2024_can_be_activated_via_admin_api(db, seed_config, client, settings):
    seeded = seed(db, seed_config, kurikulum_file=[SEED_JSON, SEED_CPL_JSON, SEED_MK_CPL_JSON])
    db.commit()

    admin = db.get(User, UUID(seeded["admin_id"]))
    assert admin is not None
    client.headers["Authorization"] = "Bearer " + create_access_token(admin, settings)

    kurikulum_id = seeded["kurikulum_id"]
    masters_resp = client.get("/api/v1/mata-kuliah?limit=100")
    assert masters_resp.status_code == 200
    mk_id_by_code = {item["kode_mk"]: item["id"] for item in masters_resp.json()}

    paket_resp = client.get(f"/api/v1/kurikulum/{kurikulum_id}/mata-kuliah?limit=100")
    assert paket_resp.status_code == 200
    paket_items = paket_resp.json()
    assert len(paket_items) == 61
    paket_id_by_mk_id = {item["mk_id"]: item["id"] for item in paket_items}

    for kode_mk in ("TIK-2401", "TI-24508"):
        paket_id = paket_id_by_mk_id[mk_id_by_code[kode_mk]]
        matrix_resp = client.get(f"/api/v1/kurikulum/{kurikulum_id}/mata-kuliah/{paket_id}/cpl")
        assert matrix_resp.status_code == 200
        assert len(matrix_resp.json()) == 3

    activate_resp = client.post(f"/api/v1/kurikulum/{kurikulum_id}/aktifkan")
    assert activate_resp.status_code == 200, activate_resp.text
    assert activate_resp.json()["status"] == "Aktif"


def test_ti_2024_profil_lulusan_seed_json_valid_and_complete():
    payload = load_curriculum_seed(SEED_PL_JSON)
    assert payload.prodi.kode_prodi == "TI"
    assert payload.kurikulum.kode_kurikulum == "TI-2024"
    assert len(payload.profil_lulusan) == 4
    assert [item.kode_pl for item in payload.profil_lulusan] == [
        "PL-01",
        "PL-02",
        "PL-03",
        "PL-04",
    ]
    for item in payload.profil_lulusan:
        assert item.bidang_kerja
        assert item.deskripsi

    links_by_pl = {entry.kode_pl: entry.cpl for entry in payload.pl_cpl}
    assert set(links_by_pl) == {"PL-01", "PL-02", "PL-03", "PL-04"}
    assert {kode: len(cpls) for kode, cpls in links_by_pl.items()} == {
        "PL-01": 9,
        "PL-02": 8,
        "PL-03": 7,
        "PL-04": 6,
    }
    assert sum(len(cpls) for cpls in links_by_pl.values()) == 30
    all_linked_cpls = {cpl for cpls in links_by_pl.values() for cpl in cpls}
    assert all_linked_cpls == {f"CPL-{idx:02d}" for idx in range(1, 13)}


def test_seed_profil_lulusan_idempotent_and_preserves_manual_edits(db, seed_config):
    first = seed(db, seed_config, kurikulum_file=[SEED_CPL_JSON, SEED_PL_JSON])
    db.commit()
    second = seed(db, seed_config, kurikulum_file=[SEED_CPL_JSON, SEED_PL_JSON])
    db.commit()

    assert first == second
    assert db.scalar(select(func.count()).select_from(ProfilLulusan)) == 4
    assert db.scalar(select(func.count()).select_from(PLCPL)) == 30

    pls = list(db.scalars(select(ProfilLulusan).order_by(ProfilLulusan.kode_pl)))
    pls[0].deskripsi = "Deskripsi PL ubahan manual."
    pls[1].bidang_kerja = None
    db.commit()

    summary = seed_curriculum_data(db, load_curriculum_seed(SEED_PL_JSON))
    db.commit()
    assert summary["pl_created"] == 0
    assert summary["pl_existing"] == 4
    assert summary["pl_cpl_created"] == 0
    assert summary["pl_cpl_existing"] == 30

    db.refresh(pls[0])
    db.refresh(pls[1])
    assert pls[0].deskripsi == "Deskripsi PL ubahan manual."
    assert pls[1].bidang_kerja is not None


def test_seed_profil_lulusan_rejects_missing_cpl_and_active_immutability(db):
    pl_payload = load_curriculum_seed(SEED_PL_JSON)
    with pytest.raises(ValueError), db.begin():
        seed_curriculum_data(db, pl_payload)

    assert db.scalar(select(func.count()).select_from(Kurikulum)) == 0
    assert db.scalar(select(func.count()).select_from(ProfilLulusan)) == 0
    assert db.scalar(select(func.count()).select_from(PLCPL)) == 0
    db.rollback()

    with db.begin():
        seed_curriculum_data(db, load_curriculum_seed(SEED_CPL_JSON))
        summary = seed_curriculum_data(db, pl_payload)

    kurikulum = db.get(Kurikulum, UUID(summary["kurikulum_id"]))
    assert kurikulum is not None
    kurikulum.status = "Aktif"
    db.commit()

    with db.begin():
        rerun = seed_curriculum_data(db, pl_payload)
    assert rerun["pl_created"] == 0
    assert rerun["pl_existing"] == 4
    assert rerun["pl_cpl_created"] == 0
    assert rerun["pl_cpl_existing"] == 30

    modified = pl_payload.model_copy(
        update={
            "pl_cpl": [
                pl_payload.pl_cpl[0].model_copy(
                    update={"cpl": [*pl_payload.pl_cpl[0].cpl, "CPL-05"]}
                ),
                *pl_payload.pl_cpl[1:],
            ]
        }
    )
    with pytest.raises(ValueError), db.begin():
        seed_curriculum_data(db, modified)

    assert db.scalar(select(func.count()).select_from(PLCPL)) == 30


def test_seed_full_ti_2024_with_demo_and_pl_overview_all_roles(db, seed_config, client, settings):
    seeded = seed(
        db,
        seed_config,
        kurikulum_file=[SEED_JSON, SEED_CPL_JSON, SEED_PL_JSON, SEED_MK_CPL_JSON],
        demo_file=SEED_DEMO_JSON,
    )
    db.commit()

    admin = db.get(User, UUID(seeded["admin_id"]))
    dosen = db.scalar(select(User).where(User.email == "dosen.rpl@demo.pnl.ac.id"))
    mhs_active = db.scalar(select(User).where(User.email == "mhs.a1@demo.pnl.ac.id"))
    mhs_cuti = db.scalar(select(User).where(User.email == "mhs.cuti@demo.pnl.ac.id"))
    assert admin and dosen and mhs_active and mhs_cuti

    for actor in (admin, dosen, mhs_active, mhs_cuti):
        client.headers["Authorization"] = "Bearer " + create_access_token(actor, settings)
        resp = client.get("/api/v1/profil-lulusan/ringkasan")
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["kode_kurikulum"] == "TI-2024"
        assert data["status"] == "Aktif"
        assert len(data["cpl"]) == 12
        assert len(data["profil_lulusan"]) == 4
        assert sum(len(pl["cpl_ids"]) for pl in data["profil_lulusan"]) == 30
