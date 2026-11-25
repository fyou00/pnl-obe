import csv
import io
from uuid import uuid4

from sqlalchemy import select

from app.core.security import create_access_token
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
    PeriodeAkademik,
    PesertaKelasMK,
    Prodi,
    RancanganPenilaian,
    SubCPMK,
    User,
)
from app.services.seed import SeedSettings, ensure_user


def _auth(dataset, settings, role="dosen"):
    return {"Authorization": "Bearer " + create_access_token(dataset[role], settings)}


def _grade_item(dataset, score="80", *, instrument=None, student=None):
    return dict(
        instrumen_id=str(instrument or dataset["instrument"].id),
        mahasiswa_id=str(student or dataset["mahasiswa"].id),
        nilai_mentah=score,
    )


def _save(client, dataset, settings, items=None, *, course=None, role="dosen"):
    return client.put(
        f"/api/v1/kelas-mk/{course or dataset['course_a'].id}/nilai",
        json={"items": items or [_grade_item(dataset)]},
        headers=_auth(dataset, settings, role),
    )


def _enroll_other(db, dataset, course=None):
    course = course or dataset["course_a"]
    db.add(
        MahasiswaPeriode(
            mahasiswa_id=dataset["other_student"].id,
            periode_id=dataset["period"].id,
            kelas_periode_id=course.kelas_periode_id,
            status="Aktif",
        )
    )
    db.add(
        PesertaKelasMK(
            kelas_mk_id=course.id, mahasiswa_id=dataset["other_student"].id, mk_id=dataset["mk"].id
        )
    )
    db.commit()


def _add_course(
    db,
    dataset,
    *,
    weight=100,
    period=None,
    curriculum=None,
    code=None,
    klass=None,
    student=None,
    semester=1,
):
    curriculum = curriculum or dataset["angkatan"].kurikulum_id
    period = period or dataset["period"]
    target_student = student or dataset["mahasiswa"]
    tag = code or f"MK-{uuid4().hex[:6]}"
    master = MataKuliah(prodi_id=dataset["prodi"].id, kode_mk=tag, nama_mk=tag)
    db.add(master)
    db.flush()
    mk = KurikulumMK(
        kurikulum_id=curriculum, mk_id=master.id, nama_mk=tag, sks=3, semester=semester
    )
    db.add(mk)
    db.flush()
    cpl = db.scalar(select(MasterCPL).where(MasterCPL.kurikulum_id == curriculum))
    if cpl is None:
        cpl = MasterCPL(
            kurikulum_id=curriculum,
            prodi_id=dataset["prodi"].id,
            kode_cpl="CPL-01",
            kategori="P",
            deskripsi="Separate version",
        )
        db.add(cpl)
        db.flush()
    db.add(MKCPL(kurikulum_mk_id=mk.id, cpl_id=cpl.id))
    design = RancanganPenilaian(
        periode_id=period.id, kurikulum_mk_id=mk.id, dosen_id=dataset["dosen"].id
    )
    db.add(design)
    db.flush()
    if klass is None:
        if period.id != dataset["period"].id:
            klass = KelasPeriode(
                periode_id=period.id,
                angkatan_id=dataset["angkatan"].id,
                kode_kelas="A",
                semester_studi=3,
            )
            db.add(klass)
            db.flush()
            db.add(
                MahasiswaPeriode(
                    mahasiswa_id=target_student.id,
                    periode_id=period.id,
                    kelas_periode_id=klass.id,
                    status="Aktif",
                )
            )
        else:
            klass = db.scalar(
                select(KelasPeriode).where(KelasPeriode.id == dataset["course_a"].kelas_periode_id)
            )
    course = KelasMK(kelas_periode_id=klass.id, kurikulum_mk_id=mk.id, rancangan_id=design.id)
    cpmk = CPMK(rancangan_id=design.id, kode_cpmk="CPMK-1", deskripsi="Course CPMK")
    db.add_all([course, cpmk])
    db.flush()
    db.add(CPMKCPL(cpmk_id=cpmk.id, cpl_id=cpl.id))
    sub = SubCPMK(cpmk_id=cpmk.id, kode_sub="SUB-1", deskripsi="Course Sub")
    db.add(sub)
    db.flush()
    instrument = InstrumenPenilaian(
        sub_cpmk_id=sub.id, nama_instrumen="Exam", jenis_instrumen="UAS", bobot_persentase=weight
    )
    db.add(instrument)
    db.add(PesertaKelasMK(kelas_mk_id=course.id, mahasiswa_id=target_student.id, mk_id=master.id))
    db.commit()
    return course, instrument


def _parse_csv(data: bytes) -> list[list[str]]:
    assert data.startswith(b"\xef\xbb\xbf")
    text = data.decode("utf-8-sig")
    return list(csv.reader(io.StringIO(text)))


def _assert_valid_pdf(data: bytes) -> bytes:
    assert data.startswith(b"%PDF-1.4\n")
    assert data.rstrip().endswith(b"%%EOF")
    marker = b"\nstartxref\n"
    idx = data.rfind(marker)
    assert idx != -1
    after = data[idx + len(marker) :].split(b"\n", 1)[0].strip()
    xref_pos = int(after)
    assert data[xref_pos : xref_pos + 5] == b"xref\n"
    xref_lines = data[xref_pos:].splitlines()
    header_parts = xref_lines[1].split()
    total_objs = int(header_parts[1])
    for obj_num in range(1, total_objs):
        entry = xref_lines[2 + obj_num]
        offset = int(entry[:10])
        assert entry[11:18] == b"00000 n"
        assert data[offset : offset + len(f"{obj_num} 0 obj".encode("latin1"))] == (
            f"{obj_num} 0 obj".encode("latin1")
        )
    return data


def _foreign_prodi_admin(db, seed_config: SeedSettings):
    prodi_b = Prodi(kode_prodi="TM", nama_prodi="Teknik Mesin", jenjang="D4")
    db.add(prodi_b)
    db.flush()
    admin_b = ensure_user(
        db,
        prodi_b,
        nama="Admin Mesin",
        nim_nidn="ADMIN-TM",
        email="admin-tm@example.com",
        password=seed_config.seed_admin_password,
        role="Admin",
    )
    period_b = PeriodeAkademik(prodi_id=prodi_b.id, tahun_mulai=2026, semester="Ganjil")
    kur_b = Kurikulum(prodi_id=prodi_b.id, kode_kurikulum="TM-2026", nama="Kurikulum TM")
    db.add_all([period_b, kur_b])
    db.commit()
    return prodi_b, admin_b, period_b, kur_b


def _add_student(
    db,
    dataset,
    seed_config: SeedSettings,
    *,
    kelas,
    status="Aktif",
    nama="Mhs",
    idx=1,
    angkatan=None,
):
    stu = ensure_user(
        db,
        dataset["prodi"],
        nama=nama,
        nim_nidn=f"20245730{idx:03d}",
        email=f"stu-{idx}-{kelas.kode_kelas.lower()}@example.com",
        password=seed_config.seed_mahasiswa_password,
        role="Mahasiswa",
    )
    db.add(Mahasiswa(id=stu.id, angkatan_id=angkatan or dataset["angkatan"].id))
    db.flush()
    db.add(
        MahasiswaPeriode(
            mahasiswa_id=stu.id,
            periode_id=dataset["period"].id,
            kelas_periode_id=kelas.id,
            status=status,
        )
    )
    db.flush()
    return stu


def test_audit_log_filtering_acl_and_sanitization(client, dataset, settings, db, seed_config):
    # Generate period audit entries and curriculum audit entries
    _save(client, dataset, settings, [_grade_item(dataset, "88.00")])
    close_url = f"/api/v1/periode-akademik/{dataset['period'].id}"
    assert (
        client.post(close_url + "/tutup", headers=_auth(dataset, settings, "admin")).status_code
        == 200
    )
    assert (
        client.post(
            close_url + "/buka-kembali",
            json={"alasan": "Koreksi 100%_nilai"},
            headers=_auth(dataset, settings, "admin"),
        ).status_code
        == 200
    )
    # Inject a defensive sensitive-key audit record to verify strip filter
    db.add(
        AuditLog(
            aktor_id=dataset["admin"].id,
            periode_id=dataset["period"].id,
            aksi="custom_test",
            entitas="users",
            entitas_id=dataset["admin"].id,
            sebelum={"password_hash": "leak", "nama": "Admin"},
            sesudah={"token": "secret-jwt", "role": "Admin"},
        )
    )
    db.commit()

    # Dosen & Mahasiswa forbidden
    for role in ["dosen", "mahasiswa"]:
        assert (
            client.get("/api/v1/audit-log", headers=_auth(dataset, settings, role)).status_code
            == 403
        )

    # Admin reads all logs newest-first
    resp = client.get(
        "/api/v1/audit-log",
        params={"periode_id": str(dataset["period"].id)},
        headers=_auth(dataset, settings, "admin"),
    )
    assert resp.status_code == 200, resp.text
    logs = resp.json()
    assert len(logs) >= 4
    times = [row["waktu"] for row in logs]
    assert times == sorted(times, reverse=True)
    reopen_row = next(row for row in logs if row["aksi"] == "reopen")
    assert reopen_row["alasan"] == "Koreksi 100%_nilai"
    assert reopen_row["aktor_nama"] == dataset["admin"].nama

    # No sensitive keys leaked
    serialized = resp.text
    assert "password_hash" not in serialized
    assert "secret-jwt" not in serialized

    # Exact aksi & entitas filters + literal wildcard %/_ search
    reopen_only = client.get(
        "/api/v1/audit-log",
        params={"aksi": "reopen", "entitas": "periode_akademik", "q": "100%_"},
        headers=_auth(dataset, settings, "admin"),
    )
    assert reopen_only.status_code == 200 and len(reopen_only.json()) == 1
    no_wildcard_match = client.get(
        "/api/v1/audit-log",
        params={"aksi": "reopen", "q": "Koreksi %"},
        headers=_auth(dataset, settings, "admin"),
    )
    assert no_wildcard_match.status_code == 200 and no_wildcard_match.json() == []

    # Pagination
    paged = client.get(
        "/api/v1/audit-log",
        params={"offset": 1, "limit": 2},
        headers=_auth(dataset, settings, "admin"),
    )
    assert paged.status_code == 200 and paged.json() == logs[1:3]

    # Foreign prodi isolation
    _prodi_b, admin_b, _period_b, _kur_b = _foreign_prodi_admin(db, seed_config)
    foreign_headers = {"Authorization": "Bearer " + create_access_token(admin_b, settings)}
    assert client.get("/api/v1/audit-log", headers=foreign_headers).json() == []
    assert (
        client.get(
            "/api/v1/audit-log",
            params={"periode_id": str(dataset["period"].id)},
            headers=foreign_headers,
        ).status_code
        == 404
    )


def test_class_export_csv_pdf_acl_zero_vs_null_and_closed_period(
    client, dataset, settings, db, seed_config
):
    # Enroll second student with missing score & test formula injection in student name
    _enroll_other(db, dataset, dataset["course_a"])
    other = db.get(User, dataset["other_student"].id)
    other.nama = "=SUM(A1)"
    db.commit()

    # Save explicit 0.00 for primary student, leave second student NULL
    assert _save(client, dataset, settings, [_grade_item(dataset, "0")]).status_code == 200

    # Student 403, outsider lecturer 404, foreign prodi admin 404
    url = f"/api/v1/kelas-mk/{dataset['course_a'].id}/ekspor"
    assert client.get(url, headers=_auth(dataset, settings, "mahasiswa")).status_code == 403
    assert client.get(url, headers=_auth(dataset, settings, "outsider")).status_code == 404
    _prodi_b, admin_b, _, _ = _foreign_prodi_admin(db, seed_config)
    assert (
        client.get(
            url, headers={"Authorization": "Bearer " + create_access_token(admin_b, settings)}
        ).status_code
        == 404
    )

    # Close period — exports MUST remain accessible for Admin and assigned Dosen
    assert (
        client.post(
            f"/api/v1/periode-akademik/{dataset['period'].id}/tutup",
            headers=_auth(dataset, settings, "admin"),
        ).status_code
        == 200
    )

    csv_resp = client.get(url, params={"format": "csv"}, headers=_auth(dataset, settings, "dosen"))
    assert csv_resp.status_code == 200
    assert "attachment;" in csv_resp.headers["content-disposition"]
    assert csv_resp.headers["content-disposition"].endswith('.csv"')
    rows = _parse_csv(csv_resp.content)
    header_idx = next(i for i, r in enumerate(rows) if r and r[0] == "NIM")
    student_rows = {
        r[0]: r
        for r in rows[header_idx + 1 :]
        if r and r[0] != "REKAP KELAS" and len(r) == len(rows[header_idx])
    }
    # Primary student: explicit 0.00 score, complete status
    mhs_row = student_rows[dataset["mahasiswa"].nim_nidn]
    assert mhs_row[2] == "0.00"
    assert mhs_row[-1] == "Lengkap"
    # Second student: missing score stays empty string, formula injection neutralized, status Belum lengkap
    other_row = student_rows[other.nim_nidn]
    assert other_row[1] == "'=SUM(A1)"
    assert other_row[2] == ""
    assert other_row[-1] == "Belum lengkap"

    # Admin PDF export on closed period
    pdf_resp = client.get(url, params={"format": "pdf"}, headers=_auth(dataset, settings, "admin"))
    assert pdf_resp.status_code == 200
    assert pdf_resp.headers["content-type"] == "application/pdf"
    pdf_bytes = _assert_valid_pdf(pdf_resp.content)
    assert b"0.00" in pdf_bytes
    assert dataset["mahasiswa"].nim_nidn.encode("latin1") in pdf_bytes

    # Draft unready design exports cleanly with Belum siap dinilai
    draft_course, _ = _add_course(db, dataset, weight=80, code="DRAFT80")
    draft_csv = client.get(
        f"/api/v1/kelas-mk/{draft_course.id}/ekspor",
        params={"format": "csv"},
        headers=_auth(dataset, settings, "dosen"),
    )
    assert draft_csv.status_code == 200
    assert "Belum siap dinilai" in draft_csv.content.decode("utf-8-sig")


def test_prodi_report_curriculum_isolation_semester_filter_and_tik_exclusion(
    client, dataset, settings, db, seed_config
):
    _save(client, dataset, settings, [_grade_item(dataset, "80.00")])

    # Add TI-K student (Cuti) + class K in the same period: MUST be excluded everywhere
    class_k = KelasPeriode(
        periode_id=dataset["period"].id,
        angkatan_id=dataset["angkatan"].id,
        kode_kelas="K",
        semester_studi=None,
    )
    db.add(class_k)
    db.flush()
    _add_student(
        db, dataset, seed_config, kelas=class_k, status="Cuti", nama="Mahasiswa Cuti", idx=99
    )

    # Create a second curriculum version + cohort in the SAME prodi & period with matching CPL-01 code
    kur_old = Kurikulum(
        prodi_id=dataset["prodi"].id,
        kode_kurikulum="TI-2020",
        nama="Kurikulum Lama",
        status="Arsip",
    )
    db.add(kur_old)
    db.flush()
    angkatan_old = Angkatan(prodi_id=dataset["prodi"].id, tahun_masuk=2024, kurikulum_id=kur_old.id)
    db.add(angkatan_old)
    db.flush()
    class_old = KelasPeriode(
        periode_id=dataset["period"].id,
        angkatan_id=angkatan_old.id,
        kode_kelas="A",
        semester_studi=3,
    )
    db.add(class_old)
    db.flush()
    stu_old = _add_student(
        db,
        dataset,
        seed_config,
        kelas=class_old,
        status="Aktif",
        nama="Mhs Kur Lama",
        idx=88,
        angkatan=angkatan_old.id,
    )
    course_old, inst_old = _add_course(
        db,
        dataset,
        curriculum=kur_old.id,
        code="OLD01",
        klass=class_old,
        student=stu_old,
        semester=3,
    )
    assert (
        _save(
            client,
            dataset,
            settings,
            [_grade_item(dataset, "50.00", instrument=inst_old.id, student=stu_old.id)],
            course=course_old.id,
        ).status_code
        == 200
    )

    # Dosen & Mahasiswa forbidden
    for role in ["dosen", "mahasiswa"]:
        assert (
            client.get(
                "/api/v1/laporan/prodi",
                params={
                    "periode_id": str(dataset["period"].id),
                    "kurikulum_id": str(dataset["angkatan"].kurikulum_id),
                },
                headers=_auth(dataset, settings, role),
            ).status_code
            == 403
        )

    # Curriculum 1 report: only sees 80.00 (excludes 50.00 from kur_old and excludes TI-K student)
    r1 = client.get(
        "/api/v1/laporan/prodi",
        params={
            "periode_id": str(dataset["period"].id),
            "kurikulum_id": str(dataset["angkatan"].kurikulum_id),
        },
        headers=_auth(dataset, settings, "admin"),
    )
    assert r1.status_code == 200, r1.text
    d1 = r1.json()
    assert d1["kurikulum_id"] == str(dataset["angkatan"].kurikulum_id)
    assert d1["total_kelas_mk"] == 2  # course_a + course_b
    assert d1["total_peserta"] == 1  # TI-K cuti excluded
    assert d1["total_peserta_lengkap"] == 1
    assert d1["total_audit_periode"] >= 2
    assert d1["rekap_cpl"][0]["capaian"] == "80.00"

    # Curriculum 2 report: strictly isolated to kur_old (50.00)
    r2 = client.get(
        "/api/v1/laporan/prodi",
        params={"periode_id": str(dataset["period"].id), "kurikulum_id": str(kur_old.id)},
        headers=_auth(dataset, settings, "admin"),
    )
    assert r2.status_code == 200
    d2 = r2.json()
    assert d2["total_kelas_mk"] == 1
    assert d2["rekap_cpl"][0]["capaian"] == "50.00"

    # Semester filter excludes semester 1 course when semester=3
    r_sem3 = client.get(
        "/api/v1/laporan/prodi",
        params={
            "periode_id": str(dataset["period"].id),
            "kurikulum_id": str(kur_old.id),
            "semester": 3,
        },
        headers=_auth(dataset, settings, "admin"),
    )
    assert r_sem3.status_code == 200 and r_sem3.json()["total_kelas_mk"] == 1
    r_sem5 = client.get(
        "/api/v1/laporan/prodi",
        params={
            "periode_id": str(dataset["period"].id),
            "kurikulum_id": str(kur_old.id),
            "semester": 5,
        },
        headers=_auth(dataset, settings, "admin"),
    )
    assert r_sem5.status_code == 200 and r_sem5.json()["total_kelas_mk"] == 0

    # Foreign prodi admin gets 404
    _prodi_b, admin_b, _, _ = _foreign_prodi_admin(db, seed_config)
    assert (
        client.get(
            "/api/v1/laporan/prodi",
            params={
                "periode_id": str(dataset["period"].id),
                "kurikulum_id": str(dataset["angkatan"].kurikulum_id),
            },
            headers={"Authorization": "Bearer " + create_access_token(admin_b, settings)},
        ).status_code
        == 404
    )

    # Exports CSV & PDF
    csv_r = client.get(
        "/api/v1/laporan/prodi/ekspor",
        params={
            "periode_id": str(dataset["period"].id),
            "kurikulum_id": str(dataset["angkatan"].kurikulum_id),
            "format": "csv",
        },
        headers=_auth(dataset, settings, "admin"),
    )
    assert csv_r.status_code == 200 and "REKAP CPL PRODI" in csv_r.content.decode("utf-8-sig")

    pdf_r = client.get(
        "/api/v1/laporan/prodi/ekspor",
        params={
            "periode_id": str(dataset["period"].id),
            "kurikulum_id": str(dataset["angkatan"].kurikulum_id),
            "format": "pdf",
        },
        headers=_auth(dataset, settings, "admin"),
    )
    assert pdf_r.status_code == 200
    assert b"80.00" in _assert_valid_pdf(pdf_r.content)


def test_cross_class_weighted_average_and_curriculum_guard(
    client, dataset, settings, db, seed_config
):
    # Class A: 1 complete student = 100.00
    assert _save(client, dataset, settings, [_grade_item(dataset, "100.00")]).status_code == 200

    # Class B: 3 complete students = 60.00 each -> weighted average MUST be (100 + 60 + 60 + 60)/4 = 70.00 (NOT 80.00!)
    klass_b = db.get(KelasPeriode, dataset["course_b"].kelas_periode_id)
    b_students = []
    for i in range(1, 4):
        stu = _add_student(db, dataset, seed_config, kelas=klass_b, nama=f"Mhs B{i}", idx=i + 10)
        db.add(
            PesertaKelasMK(
                kelas_mk_id=dataset["course_b"].id, mahasiswa_id=stu.id, mk_id=dataset["mk"].id
            )
        )
        b_students.append(stu)
    db.commit()
    assert (
        _save(
            client,
            dataset,
            settings,
            [_grade_item(dataset, "60.00", student=stu.id) for stu in b_students],
            course=dataset["course_b"].id,
        ).status_code
        == 200
    )

    params = [
        ("periode_id", str(dataset["period"].id)),
        ("kelas_mk_ids", str(dataset["course_a"].id)),
        ("kelas_mk_ids", str(dataset["course_b"].id)),
    ]
    res = client.get(
        "/api/v1/laporan/lintas-kelas", params=params, headers=_auth(dataset, settings, "dosen")
    )
    assert res.status_code == 200, res.text
    payload = res.json()
    for kind in ("Mata kuliah", "CPMK", "Sub-CPMK", "CPL"):
        item = next(r for r in payload["rekap"] if r["jenis"] == kind)
        assert item["capaian"] == "70.00"
        assert (item["mahasiswa_lengkap"], item["total_mahasiswa"]) == (4, 4)
        assert item["status"] == "Lengkap"

    # CSV & PDF cross-class export
    csv_r = client.get(
        "/api/v1/laporan/lintas-kelas/ekspor",
        params=[*params, ("format", "csv")],
        headers=_auth(dataset, settings, "dosen"),
    )
    assert csv_r.status_code == 200 and "70.00" in csv_r.content.decode("utf-8-sig")
    pdf_r = client.get(
        "/api/v1/laporan/lintas-kelas/ekspor",
        params=[*params, ("format", "pdf")],
        headers=_auth(dataset, settings, "admin"),
    )
    assert pdf_r.status_code == 200 and b"70.00" in _assert_valid_pdf(pdf_r.content)

    # Guards: Mahasiswa 403, outsider Dosen 404, duplicate 422, mixed curricula 409
    assert (
        client.get(
            "/api/v1/laporan/lintas-kelas",
            params=params,
            headers=_auth(dataset, settings, "mahasiswa"),
        ).status_code
        == 403
    )
    assert (
        client.get(
            "/api/v1/laporan/lintas-kelas",
            params=params,
            headers=_auth(dataset, settings, "outsider"),
        ).status_code
        == 404
    )
    dup = [
        ("periode_id", str(dataset["period"].id)),
        ("kelas_mk_ids", str(dataset["course_a"].id)),
        ("kelas_mk_ids", str(dataset["course_a"].id)),
    ]
    assert (
        client.get(
            "/api/v1/laporan/lintas-kelas", params=dup, headers=_auth(dataset, settings, "dosen")
        ).status_code
        == 422
    )

    kur2 = Kurikulum(prodi_id=dataset["prodi"].id, kode_kurikulum="TI-2020-X", nama="Other")
    db.add(kur2)
    db.flush()
    other_course, _ = _add_course(db, dataset, curriculum=kur2.id, code="CROSSVER")
    mixed = [
        ("periode_id", str(dataset["period"].id)),
        ("kelas_mk_ids", str(dataset["course_a"].id)),
        ("kelas_mk_ids", str(other_course.id)),
    ]
    assert (
        client.get(
            "/api/v1/laporan/lintas-kelas", params=mixed, headers=_auth(dataset, settings, "dosen")
        ).status_code
        == 409
    )


def test_personal_export_pdf_csv_privacy_cumulative_and_tik(
    client, dataset, settings, db, seed_config
):
    _enroll_other(db, dataset, dataset["course_a"])
    other = db.get(User, dataset["other_student"].id)
    assert (
        _save(
            client,
            dataset,
            settings,
            [
                _grade_item(dataset, "85.00"),
                _grade_item(dataset, "40.00", student=other.id),
            ],
        ).status_code
        == 200
    )

    # Admin & Dosen rejected on personal export
    for role in ["admin", "dosen"]:
        assert (
            client.get(
                "/api/v1/capaian/saya/ekspor",
                params={"periode_id": str(dataset["period"].id)},
                headers=_auth(dataset, settings, role),
            ).status_code
            == 403
        )

    # Add second period & cumulative grade check
    period2 = PeriodeAkademik(prodi_id=dataset["prodi"].id, tahun_mulai=2026, semester="Genap")
    db.add(period2)
    db.commit()
    course2, inst2 = _add_course(db, dataset, period=period2, code="P2MK")
    assert (
        _save(
            client,
            dataset,
            settings,
            [_grade_item(dataset, "95.00", instrument=inst2.id)],
            course=course2.id,
        ).status_code
        == 200
    )

    # Non-cumulative export for period 1 -> contains 85.00, NEVER peer student's 40.00 or NIM
    pdf1 = client.get(
        "/api/v1/capaian/saya/ekspor",
        params={"periode_id": str(dataset["period"].id), "kumulatif": False, "format": "pdf"},
        headers=_auth(dataset, settings, "mahasiswa"),
    )
    assert pdf1.status_code == 200
    pdf1_bytes = _assert_valid_pdf(pdf1.content)
    assert b"85.00" in pdf1_bytes
    assert other.nim_nidn.encode("latin1") not in pdf1_bytes
    assert other.nama.encode("latin1") not in pdf1_bytes

    # Cumulative export on period 2 -> averages 85.00 and 95.00 => 90.00
    csv_cum = client.get(
        "/api/v1/capaian/saya/ekspor",
        params={"periode_id": str(period2.id), "kumulatif": True, "format": "csv"},
        headers=_auth(dataset, settings, "mahasiswa"),
    )
    assert csv_cum.status_code == 200
    csv_text = csv_cum.content.decode("utf-8-sig")
    assert "90.00" in csv_text
    assert other.nim_nidn not in csv_text

    # TI-K student with 0 courses exports valid empty report without 0.00%
    class_k = KelasPeriode(
        periode_id=dataset["period"].id,
        angkatan_id=dataset["angkatan"].id,
        kode_kelas="K",
        semester_studi=None,
    )
    db.add(class_k)
    db.flush()
    stu_k = _add_student(
        db, dataset, seed_config, kelas=class_k, status="Cuti", nama="Student Cuti", idx=77
    )
    db.commit()
    tik_pdf = client.get(
        "/api/v1/capaian/saya/ekspor",
        params={"periode_id": str(dataset["period"].id), "format": "pdf"},
        headers={"Authorization": "Bearer " + create_access_token(stu_k, settings)},
    )
    assert tik_pdf.status_code == 200
    tik_bytes = _assert_valid_pdf(tik_pdf.content)
    assert b"TI-K" in tik_bytes and b"(0.00) Tj" not in tik_bytes
    tik_csv = client.get(
        "/api/v1/capaian/saya/ekspor",
        params={"periode_id": str(dataset["period"].id), "format": "csv"},
        headers={"Authorization": "Bearer " + create_access_token(stu_k, settings)},
    )
    assert tik_csv.status_code == 200
    tik_text = tik_csv.content.decode("utf-8-sig")
    assert "TI-K (Cuti)" in tik_text and "0.00" not in tik_text


def test_student_periods_and_course_detail_readonly_endpoints(client, dataset, settings, db):
    # Role guard: Admin & Dosen rejected on student-only endpoints
    for role in ["admin", "dosen"]:
        assert (
            client.get(
                "/api/v1/mahasiswa/periode", headers=_auth(dataset, settings, role)
            ).status_code
            == 403
        )
        assert (
            client.get(
                f"/api/v1/mahasiswa/kelas-mk/{dataset['course_a'].id}/rincian",
                headers=_auth(dataset, settings, role),
            ).status_code
            == 403
        )

    # Unenrolled class -> 404
    assert (
        client.get(
            f"/api/v1/mahasiswa/kelas-mk/{dataset['course_b'].id}/rincian",
            headers=_auth(dataset, settings, "mahasiswa"),
        ).status_code
        == 404
    )

    # Add newer period where the same student is placed on TI-K (Cuti, 0 courses)
    period_cuti = PeriodeAkademik(prodi_id=dataset["prodi"].id, tahun_mulai=2027, semester="Ganjil")
    db.add(period_cuti)
    db.flush()
    class_cuti = KelasPeriode(
        periode_id=period_cuti.id,
        angkatan_id=dataset["angkatan"].id,
        kode_kelas="K",
        semester_studi=None,
    )
    db.add(class_cuti)
    db.flush()
    db.add(
        MahasiswaPeriode(
            mahasiswa_id=dataset["mahasiswa"].id,
            periode_id=period_cuti.id,
            kelas_periode_id=class_cuti.id,
            status="Cuti",
        )
    )

    # Create a 2-instrument course: 50% Tugas (0.00 scored) + 50% UAS (unscored None)
    master = MataKuliah(prodi_id=dataset["prodi"].id, kode_mk="MK-DET", nama_mk="Basis Data")
    db.add(master)
    db.flush()
    mk = KurikulumMK(
        kurikulum_id=dataset["angkatan"].kurikulum_id,
        mk_id=master.id,
        nama_mk="Basis Data",
        sks=3,
        semester=1,
    )
    db.add(mk)
    db.flush()
    cpl = db.scalar(
        select(MasterCPL).where(MasterCPL.kurikulum_id == dataset["angkatan"].kurikulum_id)
    )
    assert cpl is not None
    db.add(MKCPL(kurikulum_mk_id=mk.id, cpl_id=cpl.id))
    design = RancanganPenilaian(
        periode_id=dataset["period"].id, kurikulum_mk_id=mk.id, dosen_id=dataset["dosen"].id
    )
    db.add(design)
    db.flush()
    course = KelasMK(
        kelas_periode_id=dataset["course_a"].kelas_periode_id,
        kurikulum_mk_id=mk.id,
        rancangan_id=design.id,
    )
    cpmk = CPMK(rancangan_id=design.id, kode_cpmk="CPMK-01", deskripsi="Rancangan relasional")
    db.add_all([course, cpmk])
    db.flush()
    db.add(CPMKCPL(cpmk_id=cpmk.id, cpl_id=cpl.id))
    sub = SubCPMK(cpmk_id=cpmk.id, kode_sub="SUB-01", deskripsi="Normalisasi")
    db.add(sub)
    db.flush()
    inst_zero = InstrumenPenilaian(
        sub_cpmk_id=sub.id, nama_instrumen="Kuis 1", jenis_instrumen="Kuis", bobot_persentase=50
    )
    inst_empty = InstrumenPenilaian(
        sub_cpmk_id=sub.id, nama_instrumen="UAS", jenis_instrumen="UAS", bobot_persentase=50
    )
    db.add_all([inst_zero, inst_empty])
    db.add(
        PesertaKelasMK(kelas_mk_id=course.id, mahasiswa_id=dataset["mahasiswa"].id, mk_id=master.id)
    )
    db.commit()

    # Save explicit 0.00 on inst_zero, leave inst_empty ungraded
    assert (
        _save(
            client,
            dataset,
            settings,
            [_grade_item(dataset, "0.00", instrument=inst_zero.id)],
            course=course.id,
        ).status_code
        == 200
    )

    periods_resp = client.get(
        "/api/v1/mahasiswa/periode", headers=_auth(dataset, settings, "mahasiswa")
    )
    assert periods_resp.status_code == 200
    periods = periods_resp.json()
    assert len(periods) == 2
    assert periods[0]["periode_id"] == str(period_cuti.id)
    assert periods[0]["kode_kelas"] == "K"
    assert periods[0]["kelas"] == "TI-K"
    assert periods[0]["status_mahasiswa"] == "Cuti"
    assert periods[0]["jumlah_kelas_mk"] == 0
    assert periods[1]["periode_id"] == str(dataset["period"].id)
    assert periods[1]["status_mahasiswa"] == "Aktif"
    assert periods[1]["jumlah_kelas_mk"] >= 2

    detail_resp = client.get(
        f"/api/v1/mahasiswa/kelas-mk/{course.id}/rincian",
        headers=_auth(dataset, settings, "mahasiswa"),
    )
    assert detail_resp.status_code == 200
    detail = detail_resp.json()
    assert detail["kode_mk"] == "MK-DET"
    assert detail["siap_dinilai"] is True
    by_name = {row["nama_instrumen"]: row for row in detail["instrumen"]}
    assert by_name["Kuis 1"]["nilai_mentah"] == "0.00"
    assert by_name["Kuis 1"]["status"] == "Sudah diinput"
    assert by_name["UAS"]["nilai_mentah"] is None
    assert by_name["UAS"]["status"] == "Belum diinput"
    assert by_name["Kuis 1"]["cpl_kodes"] == [cpl.kode_cpl]
    mk_att = next(item for item in detail["hasil"] if item["jenis"] == "Mata kuliah")
    assert mk_att["capaian"] is None
    assert mk_att["instrumen_lengkap"] == 1
    assert mk_att["total_instrumen"] == 2

    # Score remaining instrument 100.00 -> MK attainment becomes 50.00
    assert (
        _save(
            client,
            dataset,
            settings,
            [_grade_item(dataset, "100.00", instrument=inst_empty.id)],
            course=course.id,
        ).status_code
        == 200
    )
    detail2 = client.get(
        f"/api/v1/mahasiswa/kelas-mk/{course.id}/rincian",
        headers=_auth(dataset, settings, "mahasiswa"),
    ).json()
    mk_att2 = next(item for item in detail2["hasil"] if item["jenis"] == "Mata kuliah")
    assert mk_att2["capaian"] == "50.00"
    assert mk_att2["status"] == "Lengkap"
