"""Audit log queries, weighted curriculum-isolated reports, and CSV/PDF exports."""

from __future__ import annotations

import csv
import io
import re
from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Literal
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.models import (
    CPMK,
    CPMKCPL,
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
from app.services import academic, assessment, curriculum, outcomes
from app.services.access import accessible_classes, require_class_access
from app.services.pdf_builder import build_report_pdf

WIB = timezone(timedelta(hours=7))
SENSITIVE_KEYS = {"password_hash", "password", "token", "secret", "access_token", "refresh_token"}


def csv_safe(value: Any) -> str:
    """Neutralize spreadsheet formula injection while keeping blank cells and '-' intact."""
    if value is None:
        return ""
    text = str(value)
    if not text or text == "-":
        return text
    if text[0] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + text
    return text


def safe_filename(prefix: str, *parts: str, ext: str) -> str:
    tokens = [prefix, *(p for p in parts if p)]
    cleaned = [re.sub(r"[^A-Za-z0-9._-]+", "-", str(token)).strip("-") for token in tokens]
    stem = "-".join(t for t in cleaned if t) or "laporan"
    ext_clean = re.sub(r"[^A-Za-z0-9]+", "", ext)
    return f"{stem}.{ext_clean}"


def format_decimal(value: Decimal | None, *, missing: str = "") -> str:
    return format(value, ".2f") if value is not None else missing


def sanitize_audit_payload(data: Any) -> Any:
    if isinstance(data, dict):
        return {
            key: sanitize_audit_payload(val)
            for key, val in data.items()
            if str(key).lower() not in SENSITIVE_KEYS
        }
    if isinstance(data, list):
        return [sanitize_audit_payload(item) for item in data]
    return data


def wib_now_str() -> str:
    return datetime.now(UTC).astimezone(WIB).strftime("%Y-%m-%d %H:%M WIB")


def _class_label(prodi: Prodi, klass: KelasPeriode) -> str:
    tingkat = "" if klass.tingkat is None else str(klass.tingkat)
    return f"{prodi.kode_prodi}-{tingkat}{klass.kode_kelas}"


def _csv_bytes(rows: list[list[Any]]) -> bytes:
    buf = io.StringIO()
    writer = csv.writer(buf)
    for row in rows:
        writer.writerow([csv_safe(cell) for cell in row])
    return buf.getvalue().encode("utf-8-sig")


def weighted_averages(
    class_bundles: list[tuple[list[outcomes.Node], list[UUID], dict[UUID, dict]]],
) -> list[dict[str, Any]]:
    """Aggregate raw student Decimal outcomes weighted by participant count per outcome node."""
    buckets: dict[tuple[str, UUID], dict[str, Any]] = {}
    for nodes, participants, scores in class_bundles:
        for node in nodes:
            key = (node.jenis, node.id)
            bucket = buckets.get(key)
            if bucket is None:
                bucket = {
                    "meta": node.metadata(),
                    "values": [],
                    "total_mahasiswa": 0,
                    "any_ready": False,
                    "all_ready": True,
                }
                buckets[key] = bucket
            bucket["total_mahasiswa"] += len(participants)
            bucket["any_ready"] = bucket["any_ready"] or node.ready
            bucket["all_ready"] = bucket["all_ready"] and node.ready
            for student_id in participants:
                val, _, _ = outcomes.evaluate(node, scores.get(student_id, {}))
                if val is not None:
                    bucket["values"].append(val)

    results: list[dict[str, Any]] = []
    for bucket in buckets.values():
        values: list[Decimal] = bucket["values"]
        total = bucket["total_mahasiswa"]
        mean = sum(values, outcomes.ZERO) / len(values) if values else None
        if not bucket["any_ready"]:
            status = "Belum siap dinilai"
        elif bucket["all_ready"] and len(values) == total and total > 0:
            status = "Lengkap"
        else:
            status = "Belum lengkap"
        results.append(
            {
                **bucket["meta"],
                "capaian": outcomes.rounded(mean),
                "status": status,
                "mahasiswa_lengkap": len(values),
                "total_mahasiswa": total,
            }
        )
    return sorted(results, key=lambda item: (item["jenis"], item["kode"], str(item["id"])))


def list_audit_logs(
    db: Session,
    user: User,
    *,
    periode_id: UUID | None = None,
    aksi: str | None = None,
    entitas: str | None = None,
    q: str | None = None,
    offset: int = 0,
    limit: int = 50,
) -> list[dict[str, Any]]:
    if user.role != "Admin":
        raise HTTPException(403, "Jejak audit hanya dapat diakses oleh Admin")
    if periode_id is not None:
        academic.period(db, user, periode_id)

    query = (
        select(AuditLog, User.nama, User.role)
        .join(User, AuditLog.aktor_id == User.id)
        .where(User.prodi_id == user.prodi_id)
    )
    if periode_id is not None:
        query = query.where(AuditLog.periode_id == periode_id)
    if aksi is not None and aksi.strip():
        query = query.where(AuditLog.aksi == aksi.strip())
    if entitas is not None and entitas.strip():
        query = query.where(AuditLog.entitas == entitas.strip())
    if q is not None and q.strip():
        query = curriculum.search(
            query,
            [AuditLog.aksi, AuditLog.entitas, AuditLog.alasan, User.nama],
            q.strip(),
        )
    rows = db.execute(
        query.order_by(AuditLog.waktu.desc(), AuditLog.id.desc()).offset(offset).limit(limit)
    ).all()
    return [
        {
            "id": log.id,
            "aktor_id": log.aktor_id,
            "aktor_nama": actor_name,
            "aktor_role": actor_role,
            "periode_id": log.periode_id,
            "aksi": log.aksi,
            "entitas": log.entitas,
            "entitas_id": log.entitas_id,
            "alasan": log.alasan,
            "sebelum": sanitize_audit_payload(log.sebelum),
            "sesudah": sanitize_audit_payload(log.sesudah),
            "waktu": log.waktu,
        }
        for log, actor_name, actor_role in rows
    ]


def prodi_report(
    db: Session,
    user: User,
    *,
    periode_id: UUID,
    kurikulum_id: UUID,
    semester: int | None = None,
) -> dict[str, Any]:
    if user.role != "Admin":
        raise HTTPException(403, "Laporan prodi hanya dapat diakses oleh Admin")
    periode = academic.period(db, user, periode_id)
    kurikulum = curriculum.owned(db, Kurikulum, kurikulum_id, user)
    prodi = db.get(Prodi, user.prodi_id)
    assert prodi is not None

    query = (
        accessible_classes(user)
        .add_columns(User.nama)
        .join(User, RancanganPenilaian.dosen_id == User.id)
        .where(
            PeriodeAkademik.id == periode.id,
            KurikulumMK.kurikulum_id == kurikulum.id,
        )
    )
    if semester is not None:
        query = query.where(KurikulumMK.semester == semester)
    rows = db.execute(
        query.order_by(
            KurikulumMK.semester,
            MataKuliah.kode_mk,
            KelasPeriode.kode_kelas,
            KelasMK.id,
        )
    ).all()

    total_audit = (
        db.scalar(
            select(func.count())
            .select_from(AuditLog)
            .join(User, AuditLog.aktor_id == User.id)
            .where(User.prodi_id == user.prodi_id, AuditLog.periode_id == periode.id)
        )
        or 0
    )

    class_summaries: list[dict[str, Any]] = []
    cpl_bundles: list[tuple[list[outcomes.Node], list[UUID], dict[UUID, dict]]] = []
    total_peserta = 0
    total_peserta_lengkap = 0

    for course, klass, per, mk, master, design, row_prodi, dosen_nama in rows:
        context = (course, klass, per, mk, master, design, row_prodi)
        design_summary = assessment.summary(db, user, design)
        nodes = outcomes.nodes_for_class(db, user, context)
        participants = list(
            db.scalars(
                select(PesertaKelasMK.mahasiswa_id)
                .where(PesertaKelasMK.kelas_mk_id == course.id)
                .order_by(PesertaKelasMK.mahasiswa_id)
            )
        )
        scores = outcomes.scores_for(db, [course.id])
        class_rekap = weighted_averages([(nodes, participants, scores)])
        mk_row = next(r for r in class_rekap if r["jenis"] == "Mata kuliah")
        cpl_rows = [r for r in class_rekap if r["jenis"] == "CPL"]

        total_peserta += mk_row["total_mahasiswa"]
        total_peserta_lengkap += mk_row["mahasiswa_lengkap"]
        cpl_bundles.append(([n for n in nodes if n.jenis == "CPL"], participants, scores))

        class_summaries.append(
            {
                "kelas_mk_id": course.id,
                "kelas": _class_label(row_prodi, klass),
                "kode_mk": master.kode_mk,
                "nama_mk": mk.nama_mk,
                "sks": mk.sks,
                "semester": mk.semester,
                "dosen_id": design.dosen_id,
                "dosen_nama": dosen_nama,
                "rancangan_id": design.id,
                "siap_dinilai": design_summary.siap_dinilai,
                "total_bobot": design_summary.total_bobot,
                "total_mahasiswa": mk_row["total_mahasiswa"],
                "mahasiswa_lengkap": mk_row["mahasiswa_lengkap"],
                "status": mk_row["status"],
                "capaian_mk": mk_row["capaian"],
                "capaian_cpl": cpl_rows,
            }
        )

    return {
        "prodi_kode": prodi.kode_prodi,
        "prodi_nama": prodi.nama_prodi,
        "periode_id": periode.id,
        "tahun_akademik": periode.tahun_akademik,
        "semester": periode.semester,
        "status_periode": periode.status,
        "kurikulum_id": kurikulum.id,
        "kode_kurikulum": kurikulum.kode_kurikulum,
        "nama_kurikulum": kurikulum.nama,
        "semester_filter": semester,
        "total_kelas_mk": len(class_summaries),
        "total_peserta": total_peserta,
        "total_peserta_lengkap": total_peserta_lengkap,
        "total_audit_periode": int(total_audit),
        "rekap_cpl": weighted_averages(cpl_bundles),
        "kelas": class_summaries,
    }


def export_prodi_report(
    db: Session,
    user: User,
    *,
    periode_id: UUID,
    kurikulum_id: UUID,
    fmt: Literal["csv", "pdf"],
    semester: int | None = None,
) -> tuple[bytes, str, str]:
    report = prodi_report(
        db, user, periode_id=periode_id, kurikulum_id=kurikulum_id, semester=semester
    )
    sem_tag = f"sem{semester}" if semester is not None else "semua-sem"
    filename = safe_filename(
        "laporan-prodi",
        report["prodi_kode"],
        report["kode_kurikulum"],
        report["tahun_akademik"],
        report["semester"],
        sem_tag,
        ext=fmt,
    )
    if fmt == "csv":
        rows: list[list[Any]] = [
            [
                "LAPORAN PRODI OBE",
                report["prodi_nama"],
                report["kode_kurikulum"],
                f"{report['tahun_akademik']} {report['semester']}",
            ],
            [
                "Status Periode",
                report["status_periode"],
                "Audit Periode",
                report["total_audit_periode"],
            ],
            [],
            ["REKAP KELAS MK"],
            [
                "Kelas",
                "Kode MK",
                "Nama MK",
                "SKS",
                "Semester",
                "Dosen Pengampu",
                "Bobot (%)",
                "Lengkap",
                "Total Peserta",
                "Capaian MK (%)",
                "Status",
                "Capaian CPL",
            ],
        ]
        for cls in report["kelas"]:
            cpl_text = "; ".join(
                f"{c['kode']}: {format_decimal(c['capaian'], missing='-')}%"
                for c in cls["capaian_cpl"]
            )
            rows.append(
                [
                    cls["kelas"],
                    cls["kode_mk"],
                    cls["nama_mk"],
                    cls["sks"],
                    cls["semester"],
                    cls["dosen_nama"],
                    format(cls["total_bobot"], ".2f"),
                    cls["mahasiswa_lengkap"],
                    cls["total_mahasiswa"],
                    format_decimal(cls["capaian_mk"], missing=""),
                    cls["status"],
                    cpl_text,
                ]
            )
        rows.extend(
            [
                [],
                ["REKAP CPL PRODI"],
                [
                    "Kode CPL",
                    "Deskripsi",
                    "Capaian (%)",
                    "Mahasiswa Lengkap",
                    "Total Mahasiswa",
                    "Status",
                ],
            ]
        )
        for cpl in report["rekap_cpl"]:
            rows.append(
                [
                    cpl["kode"],
                    cpl["label"],
                    format_decimal(cpl["capaian"], missing=""),
                    cpl["mahasiswa_lengkap"],
                    cpl["total_mahasiswa"],
                    cpl["status"],
                ]
            )
        return _csv_bytes(rows), "text/csv; charset=utf-8", filename

    class_pdf_rows = [
        [
            cls["kelas"],
            f"{cls['kode_mk']} - {cls['nama_mk']}",
            f"Sem {cls['semester']} ({cls['sks']} SKS)",
            cls["dosen_nama"],
            f"{cls['mahasiswa_lengkap']}/{cls['total_mahasiswa']}",
            format_decimal(cls["capaian_mk"], missing="-"),
            cls["status"],
        ]
        for cls in report["kelas"]
    ]
    cpl_pdf_rows = [
        [
            cpl["kode"],
            cpl["label"],
            f"{cpl['mahasiswa_lengkap']}/{cpl['total_mahasiswa']}",
            format_decimal(cpl["capaian"], missing="-"),
            cpl["status"],
        ]
        for cpl in report["rekap_cpl"]
    ]
    pdf_bytes = build_report_pdf(
        title=f"Laporan Capaian OBE Prodi · {report['prodi_nama']}",
        subtitle=f"Kurikulum {report['kode_kurikulum']} · Periode {report['tahun_akademik']} {report['semester']}",
        meta_rows=[
            ("Program Studi", f"{report['prodi_kode']} - {report['prodi_nama']}"),
            ("Kurikulum (Terisolasi)", f"{report['kode_kurikulum']} - {report['nama_kurikulum']}"),
            (
                "Periode Akademik",
                f"{report['tahun_akademik']} {report['semester']} ({report['status_periode']})",
            ),
            ("Filter Semester", str(semester) if semester is not None else "Semua Semester (1-8)"),
            (
                "Kelas MK / Peserta",
                f"{report['total_kelas_mk']} kelas · {report['total_peserta_lengkap']}/{report['total_peserta']} lengkap",
            ),
            ("Total Audit Periode", str(report["total_audit_periode"])),
        ],
        sections=[
            {
                "title": "Rekap Capaian per Kelas MK",
                "subtitle": "Kelas TI-K dikecualikan otomatis; rancangan tanpa nilai lengkap mempertahankan status belum lengkap.",
                "headers": [
                    "Kelas",
                    "Mata Kuliah",
                    "Sem/SKS",
                    "Dosen Pengampu",
                    "Lengkap",
                    "Capaian (%)",
                    "Status",
                ],
                "widths": [1.0, 2.5, 1.0, 1.9, 0.9, 1.0, 1.4],
                "rows": class_pdf_rows,
                "empty_note": "Belum ada kelas MK pada filter periode dan kurikulum ini.",
            },
            {
                "title": "Rekap Capaian CPL Program Studi",
                "subtitle": f"Agregasi terbobot mahasiswa lengkap murni untuk versi kurikulum {report['kode_kurikulum']}.",
                "headers": ["Kode CPL", "Deskripsi CPL", "Lengkap", "Capaian (%)", "Status"],
                "widths": [1.0, 4.3, 1.0, 1.1, 1.4],
                "rows": cpl_pdf_rows,
                "empty_note": "Belum ada CPL terukur untuk kurikulum terpilih.",
            },
        ],
        landscape=True,
        footer_right=f"Dicetak: {wib_now_str()}",
    )
    return pdf_bytes, "application/pdf", filename


def cross_class_report(
    db: Session,
    user: User,
    *,
    periode_id: UUID,
    kelas_mk_ids: list[UUID],
) -> dict[str, Any]:
    if user.role not in ("Admin", "Dosen"):
        raise HTTPException(403, "Laporan lintas kelas hanya untuk Admin atau Dosen")
    if not kelas_mk_ids:
        raise HTTPException(422, "Pilih minimal satu kelas MK")
    if len(set(kelas_mk_ids)) != len(kelas_mk_ids):
        raise HTTPException(422, "Daftar kelas_mk_ids mengandung duplikat")

    periode = academic.period(db, user, periode_id)
    contexts = []
    for cid in kelas_mk_ids:
        row = require_class_access(db, user, cid)
        if row[2].id != periode.id:
            raise HTTPException(404, "Kelas mata kuliah tidak ditemukan pada periode terpilih")
        contexts.append(row)

    curricula_ids = {ctx[3].kurikulum_id for ctx in contexts}
    if len(curricula_ids) > 1:
        curriculum.conflict("Kelas lintas versi kurikulum tidak dapat digabung dalam satu laporan")

    kurikulum_id = next(iter(curricula_ids))
    kurikulum = db.get(Kurikulum, kurikulum_id)
    assert kurikulum is not None

    bundles: list[tuple[list[outcomes.Node], list[UUID], dict[UUID, dict]]] = []
    labels: list[str] = []
    for course, klass, _per, mk, _master, _design, row_prodi in contexts:
        context = (course, klass, _per, mk, _master, _design, row_prodi)
        nodes = outcomes.nodes_for_class(db, user, context)
        for node in nodes:
            if node.jenis == "Mata kuliah":
                # Merge multiple sections of the same curriculum course (e.g., TI-3A + TI-3B) cleanly.
                node.id = mk.id
        participants = list(
            db.scalars(
                select(PesertaKelasMK.mahasiswa_id)
                .where(PesertaKelasMK.kelas_mk_id == course.id)
                .order_by(PesertaKelasMK.mahasiswa_id)
            )
        )
        scores = outcomes.scores_for(db, [course.id])
        bundles.append((nodes, participants, scores))
        labels.append(f"{_class_label(row_prodi, klass)} ({_master.kode_mk})")

    return {
        "periode_id": periode.id,
        "tahun_akademik": periode.tahun_akademik,
        "semester": periode.semester,
        "kurikulum_id": kurikulum.id,
        "kode_kurikulum": kurikulum.kode_kurikulum,
        "kelas_mk_ids": list(kelas_mk_ids),
        "kelas_labels": labels,
        "rekap": weighted_averages(bundles),
    }


def export_cross_class_report(
    db: Session,
    user: User,
    *,
    periode_id: UUID,
    kelas_mk_ids: list[UUID],
    fmt: Literal["csv", "pdf"],
) -> tuple[bytes, str, str]:
    report = cross_class_report(db, user, periode_id=periode_id, kelas_mk_ids=kelas_mk_ids)
    filename = safe_filename(
        "laporan-lintas-kelas",
        report["kode_kurikulum"],
        report["tahun_akademik"],
        report["semester"],
        f"{len(kelas_mk_ids)}-kelas",
        ext=fmt,
    )
    if fmt == "csv":
        rows: list[list[Any]] = [
            [
                "LAPORAN LINTAS KELAS OBE",
                report["kode_kurikulum"],
                f"{report['tahun_akademik']} {report['semester']}",
                ", ".join(report["kelas_labels"]),
            ],
            [],
            [
                "Jenis",
                "Kode",
                "Label",
                "Capaian (%)",
                "Mahasiswa Lengkap",
                "Total Mahasiswa",
                "Status",
            ],
        ]
        for item in report["rekap"]:
            rows.append(
                [
                    item["jenis"],
                    item["kode"],
                    item["label"],
                    format_decimal(item["capaian"], missing=""),
                    item["mahasiswa_lengkap"],
                    item["total_mahasiswa"],
                    item["status"],
                ]
            )
        return _csv_bytes(rows), "text/csv; charset=utf-8", filename

    pdf_rows = [
        [
            item["jenis"],
            item["kode"],
            item["label"],
            f"{item['mahasiswa_lengkap']}/{item['total_mahasiswa']}",
            format_decimal(item["capaian"], missing="-"),
            item["status"],
        ]
        for item in report["rekap"]
    ]
    pdf_bytes = build_report_pdf(
        title="Laporan Agregasi Lintas Kelas OBE",
        subtitle=f"Kurikulum {report['kode_kurikulum']} · Periode {report['tahun_akademik']} {report['semester']}",
        meta_rows=[
            ("Periode Akademik", f"{report['tahun_akademik']} {report['semester']}"),
            ("Versi Kurikulum", report["kode_kurikulum"]),
            ("Daftar Kelas Terpilih", ", ".join(report["kelas_labels"])),
            ("Metode Agregasi", "Rata-rata terbobot jumlah mahasiswa lengkap (Decimal HALF_UP)"),
        ],
        sections=[
            {
                "title": "Rekap Gabungan Lintas Kelas",
                "subtitle": "Nilai kosong tidak dianggap 0; kelas lintas kurikulum ditolak sistem.",
                "headers": [
                    "Jenis",
                    "Kode",
                    "Deskripsi / Label",
                    "Lengkap",
                    "Capaian (%)",
                    "Status",
                ],
                "widths": [1.1, 1.0, 3.2, 0.9, 1.0, 1.3],
                "rows": pdf_rows,
            }
        ],
        landscape=False,
        footer_right=f"Dicetak: {wib_now_str()}",
    )
    return pdf_bytes, "application/pdf", filename


def export_class_report(
    db: Session,
    user: User,
    *,
    kelas_mk_id: UUID,
    fmt: Literal["csv", "pdf"],
) -> tuple[bytes, str, str]:
    if user.role not in ("Admin", "Dosen"):
        raise HTTPException(403, "Ekspor laporan kelas hanya untuk Admin atau Dosen pengampu")
    context = require_class_access(db, user, kelas_mk_id)
    course, klass, periode, mk, master, design, prodi = context
    label = _class_label(prodi, klass)
    dosen = db.get(User, design.dosen_id)
    dosen_nama = dosen.nama if dosen is not None else "-"
    design_summary = assessment.summary(db, user, design)

    instruments = db.execute(
        select(InstrumenPenilaian, SubCPMK.kode_sub, CPMK.kode_cpmk)
        .join(SubCPMK, InstrumenPenilaian.sub_cpmk_id == SubCPMK.id)
        .join(CPMK, SubCPMK.cpmk_id == CPMK.id)
        .where(CPMK.rancangan_id == design.id)
        .order_by(
            CPMK.kode_cpmk,
            SubCPMK.kode_sub,
            InstrumenPenilaian.nama_instrumen,
            InstrumenPenilaian.id,
        )
    ).all()
    students = list(
        db.scalars(
            select(User)
            .join(PesertaKelasMK, PesertaKelasMK.mahasiswa_id == User.id)
            .where(PesertaKelasMK.kelas_mk_id == course.id)
            .order_by(User.nim_nidn, User.id)
        )
    )
    scores = outcomes.scores_for(db, [course.id])
    class_res = outcomes.class_outcomes(db, user, course.id)
    peserta_map = {p["mahasiswa_id"]: p["hasil"] for p in class_res["peserta"]}

    rekap_rows = class_res["rekap"]
    cpmk_codes = sorted({r["kode"]: r["id"] for r in rekap_rows if r["jenis"] == "CPMK"}.items())
    cpl_codes = sorted({r["kode"]: r["id"] for r in rekap_rows if r["jenis"] == "CPL"}.items())

    filename = safe_filename(
        "laporan-kelas",
        master.kode_mk,
        label,
        periode.tahun_akademik,
        periode.semester,
        ext=fmt,
    )
    if fmt == "csv":
        inst_headers = [
            f"{cpmk_c}/{sub_c} - {inst.nama_instrumen} ({format(inst.bobot_persentase, '.2f')}%)"
            for inst, sub_c, cpmk_c in instruments
        ]
        headers = [
            "NIM",
            "Nama",
            *inst_headers,
            *(code for code, _ in cpmk_codes),
            *(code for code, _ in cpl_codes),
            "Capaian MK",
            "Status Kelengkapan",
        ]
        rows: list[list[Any]] = [
            [
                "LAPORAN NILAI & CAPAIAN KELAS MK",
                f"{master.kode_mk} - {mk.nama_mk}",
                label,
                f"{periode.tahun_akademik} {periode.semester}",
            ],
            [
                "Dosen Pengampu",
                dosen_nama,
                "Total Bobot (%)",
                format(design_summary.total_bobot, ".2f"),
                "Status Periode",
                periode.status,
            ],
            [],
            headers,
        ]
        for stu in students:
            stu_scores = scores.get(stu.id, {})
            hasil_map = {(h["jenis"], h["id"]): h for h in peserta_map.get(stu.id, [])}
            mk_item = next(
                (h for h in peserta_map.get(stu.id, []) if h["jenis"] == "Mata kuliah"), None
            )
            rows.append(
                [
                    stu.nim_nidn,
                    stu.nama,
                    *(
                        format_decimal(stu_scores.get((course.id, inst.id)), missing="")
                        for inst, _, _ in instruments
                    ),
                    *(
                        format_decimal(hasil_map[("CPMK", cid)]["capaian"], missing="")
                        for _, cid in cpmk_codes
                    ),
                    *(
                        format_decimal(hasil_map[("CPL", cid)]["capaian"], missing="")
                        for _, cid in cpl_codes
                    ),
                    format_decimal(mk_item["capaian"] if mk_item else None, missing=""),
                    mk_item["status"] if mk_item else "Belum siap dinilai",
                ]
            )
        rows.extend(
            [
                [],
                ["REKAP KELAS"],
                [
                    "Jenis",
                    "Kode",
                    "Label",
                    "Capaian (%)",
                    "Mahasiswa Lengkap",
                    "Total Mahasiswa",
                    "Status",
                ],
            ]
        )
        for r in rekap_rows:
            rows.append(
                [
                    r["jenis"],
                    r["kode"],
                    r["label"],
                    format_decimal(r["capaian"], missing=""),
                    r["mahasiswa_lengkap"],
                    r["total_mahasiswa"],
                    r["status"],
                ]
            )
        return _csv_bytes(rows), "text/csv; charset=utf-8", filename

    rekap_pdf_rows = [
        [
            r["jenis"],
            r["kode"],
            r["label"],
            f"{r['mahasiswa_lengkap']}/{r['total_mahasiswa']}",
            format_decimal(r["capaian"], missing="-"),
            r["status"],
        ]
        for r in rekap_rows
    ]
    student_summary_rows = []
    for stu in students:
        hasil_list = peserta_map.get(stu.id, [])
        hasil_map = {(h["jenis"], h["id"]): h for h in hasil_list}
        mk_item = next((h for h in hasil_list if h["jenis"] == "Mata kuliah"), None)
        cpmk_summary = (
            ", ".join(
                f"{code}: {format_decimal(hasil_map[('CPMK', cid)]['capaian'], missing='-')}"
                for code, cid in cpmk_codes
            )
            or "-"
        )
        cpl_summary = (
            ", ".join(
                f"{code}: {format_decimal(hasil_map[('CPL', cid)]['capaian'], missing='-')}"
                for code, cid in cpl_codes
            )
            or "-"
        )
        student_summary_rows.append(
            [
                stu.nim_nidn,
                stu.nama,
                cpmk_summary,
                cpl_summary,
                format_decimal(mk_item["capaian"] if mk_item else None, missing="-"),
                mk_item["status"] if mk_item else "Belum siap dinilai",
            ]
        )

    sections: list[dict[str, Any]] = [
        {
            "title": "Rekap Capaian Kelas MK",
            "subtitle": "Nilai kosong (-) tidak dihitung sebagai 0; rata-rata hanya mencakup mahasiswa dengan seluruh instrumen relevan terisi.",
            "headers": ["Jenis", "Kode", "Deskripsi", "Lengkap", "Capaian (%)", "Status"],
            "widths": [1.0, 0.9, 3.6, 0.9, 1.0, 1.3],
            "rows": rekap_pdf_rows,
        },
        {
            "title": "Rincian CPMK, CPL & Capaian MK per Mahasiswa",
            "headers": ["NIM", "Nama Mahasiswa", "CPMK", "CPL", "Capaian MK (%)", "Status"],
            "widths": [1.1, 1.8, 2.3, 2.0, 0.9, 1.2],
            "rows": student_summary_rows,
            "empty_note": "Belum ada mahasiswa peserta pada kelas MK ini.",
        },
    ]

    if instruments:
        chunk_size = 6
        for start in range(0, len(instruments), chunk_size):
            chunk = instruments[start : start + chunk_size]
            suffix = (
                "" if len(instruments) <= chunk_size else f" (Bagian {start // chunk_size + 1})"
            )
            inst_cols = [
                f"{inst.nama_instrumen} ({format(inst.bobot_persentase, '.0f')}%)"
                for inst, _, _ in chunk
            ]
            inst_rows = []
            for stu in students:
                stu_scores = scores.get(stu.id, {})
                inst_rows.append(
                    [
                        stu.nim_nidn,
                        stu.nama,
                        *(
                            format_decimal(stu_scores.get((course.id, inst.id)), missing="-")
                            for inst, _, _ in chunk
                        ),
                    ]
                )
            sections.append(
                {
                    "title": f"Rincian Nilai Instrumen per Mahasiswa{suffix}",
                    "headers": ["NIM", "Nama Mahasiswa", *inst_cols],
                    "widths": [1.1, 1.8, *([1.0] * len(chunk))],
                    "rows": inst_rows,
                    "empty_note": "Belum ada peserta pada kelas MK ini.",
                }
            )
    else:
        sections.append(
            {
                "title": "Rincian Nilai Instrumen per Mahasiswa",
                "headers": ["Instrumen"],
                "widths": [1.0],
                "rows": [],
                "empty_note": "Belum ada instrumen penilaian pada rancangan ini.",
            }
        )

    pdf_bytes = build_report_pdf(
        title=f"Laporan Nilai & Capaian Kelas · {master.kode_mk} {mk.nama_mk}",
        subtitle=f"{prodi.nama_prodi} · Kelas {label} · Periode {periode.tahun_akademik} {periode.semester}",
        meta_rows=[
            ("Mata Kuliah", f"{master.kode_mk} - {mk.nama_mk} ({mk.sks} SKS)"),
            (
                "Kelas / Periode",
                f"{label} · {periode.tahun_akademik} {periode.semester} ({periode.status})",
            ),
            ("Dosen Pengampu", dosen_nama),
            (
                "Kesiapan Rancangan",
                f"{'Siap dinilai' if design_summary.siap_dinilai else 'Belum siap dinilai'} ({format(design_summary.total_bobot, '.2f')}%)",
            ),
            ("Jumlah Peserta", f"{len(students)} mahasiswa"),
            ("Dicetak Pada", wib_now_str()),
        ],
        sections=sections,
        landscape=True,
        footer_right=f"Dicetak: {wib_now_str()}",
    )
    return pdf_bytes, "application/pdf", filename


def export_personal_report(
    db: Session,
    user: User,
    *,
    periode_id: UUID,
    kumulatif: bool,
    fmt: Literal["pdf", "csv"],
) -> tuple[bytes, str, str]:
    personal = outcomes.personal_outcomes(db, user, periode_id, kumulatif)
    prodi = db.get(Prodi, user.prodi_id)
    prodi_label = f"{prodi.kode_prodi} - {prodi.nama_prodi}" if prodi is not None else "-"
    roster_row = db.execute(
        select(MahasiswaPeriode, KelasPeriode)
        .join(KelasPeriode, MahasiswaPeriode.kelas_periode_id == KelasPeriode.id)
        .where(MahasiswaPeriode.mahasiswa_id == user.id, MahasiswaPeriode.periode_id == periode_id)
    ).first()
    if roster_row is not None and prodi is not None:
        mp, kp = roster_row
        roster_status = f"{_class_label(prodi, kp)} ({mp.status})"
    else:
        roster_status = "-"
    scope_tag = "kumulatif" if kumulatif else "periode"
    filename = safe_filename(
        "capaian-pribadi",
        user.nim_nidn,
        personal["tahun_akademik"],
        personal["semester"],
        scope_tag,
        ext=fmt,
    )

    class_rows: list[list[str]] = []
    if personal["kelas_mk_ids"]:
        contexts = db.execute(
            accessible_classes(user)
            .add_columns(User.nama)
            .join(User, RancanganPenilaian.dosen_id == User.id)
            .where(KelasMK.id.in_(personal["kelas_mk_ids"]))
            .order_by(
                PeriodeAkademik.tahun_mulai,
                PeriodeAkademik.semester,
                MataKuliah.kode_mk,
                KelasMK.id,
            )
        ).all()
        own_scores = outcomes.scores_for(db, personal["kelas_mk_ids"], student_id=user.id).get(
            user.id, {}
        )
        for course, klass, per, mk, master, design, row_prodi, dosen_nama in contexts:
            nodes = outcomes.nodes_for_class(
                db, user, (course, klass, per, mk, master, design, row_prodi)
            )
            mk_node = next(n for n in nodes if n.jenis == "Mata kuliah")
            mk_eval = outcomes.student_result(mk_node, own_scores)
            cpmk_str = (
                ", ".join(
                    f"{n.kode}: {format(r['capaian'], '.2f')}%"
                    if (r := outcomes.student_result(n, own_scores))["capaian"] is not None
                    else f"{n.kode}: -"
                    for n in nodes
                    if n.jenis == "CPMK"
                )
                or "-"
            )
            class_rows.append(
                [
                    f"{per.tahun_akademik} {per.semester}",
                    f"{master.kode_mk} - {mk.nama_mk}",
                    _class_label(row_prodi, klass),
                    dosen_nama,
                    cpmk_str,
                    f"{mk_eval['instrumen_lengkap']}/{mk_eval['total_instrumen']}",
                    format_decimal(mk_eval["capaian"], missing="" if fmt == "csv" else "-"),
                    mk_eval["status"],
                ]
            )

    if fmt == "csv":
        rows: list[list[Any]] = [
            ["LAPORAN CAPAIAN PRIBADI MAHASISWA", user.nim_nidn, user.nama, prodi_label],
            [
                "Periode",
                f"{personal['tahun_akademik']} {personal['semester']}",
                "Kelas / Status",
                roster_status,
                "Mode",
                "Kumulatif" if kumulatif else "Periode Terpilih",
            ],
            [],
            ["CAPAIAN CPL PRIBADI"],
            [
                "Kode CPL",
                "Deskripsi CPL",
                "Instrumen Lengkap",
                "Total Instrumen",
                "Capaian (%)",
                "Status",
            ],
        ]
        for h in personal["hasil"]:
            rows.append(
                [
                    h["kode"],
                    h["label"],
                    h["instrumen_lengkap"],
                    h["total_instrumen"],
                    format_decimal(h["capaian"], missing=""),
                    h["status"],
                ]
            )
        rows.extend(
            [
                [],
                ["RINCIAN PER MATA KULIAH"],
                [
                    "Periode",
                    "Mata Kuliah",
                    "Kelas",
                    "Dosen Pengampu",
                    "CPMK",
                    "Kelengkapan",
                    "Capaian MK (%)",
                    "Status",
                ],
            ]
        )
        rows.extend(class_rows)
        return _csv_bytes(rows), "text/csv; charset=utf-8", filename

    cpl_pdf_rows = [
        [
            h["kode"],
            h["label"],
            f"{h['instrumen_lengkap']}/{h['total_instrumen']}",
            format_decimal(h["capaian"], missing="-"),
            h["status"],
        ]
        for h in personal["hasil"]
    ]
    pdf_bytes = build_report_pdf(
        title=f"Laporan Capaian Pembelajaran Pribadi · {user.nama}",
        subtitle=f"{prodi_label} · NIM {user.nim_nidn} · Mode Read-Only",
        meta_rows=[
            ("NIM / Nama", f"{user.nim_nidn} · {user.nama}"),
            ("Program Studi", prodi_label),
            ("Periode Acuan", f"{personal['tahun_akademik']} {personal['semester']}"),
            ("Kelas / Status", roster_status),
            (
                "Cakupan Laporan",
                "Kumulatif hingga periode terpilih" if kumulatif else "Periode terpilih saja",
            ),
            (
                "Jumlah Kelas MK / Dicetak",
                f"{len(personal['kelas_mk_ids'])} kelas · {wib_now_str()}",
            ),
        ],
        sections=[
            {
                "title": "Rekap Capaian CPL Pribadi (Tanpa Garis Target)",
                "subtitle": "Nilai instrumen yang belum diisi (-) tidak pernah diubah menjadi 0.",
                "headers": ["Kode CPL", "Deskripsi CPL", "Instrumen", "Capaian (%)", "Status"],
                "widths": [1.0, 3.6, 1.0, 1.0, 1.3],
                "rows": cpl_pdf_rows,
                "empty_note": "Tidak ada paket mata kuliah atau CPL pada cakupan periode ini (mis. status Cuti/Nonaktif di TI-K).",
            },
            {
                "title": "Rincian Mata Kuliah & CPMK Pribadi",
                "headers": [
                    "Periode",
                    "Mata Kuliah",
                    "Kelas",
                    "Dosen",
                    "Rincian CPMK",
                    "Lengkap",
                    "Capaian",
                    "Status",
                ],
                "widths": [1.1, 1.8, 0.8, 1.2, 1.8, 0.8, 0.8, 1.1],
                "rows": class_rows,
                "empty_note": "Tidak ada mata kuliah terdaftar pada cakupan periode ini.",
            },
        ],
        landscape=True,
        footer_right=f"Dicetak: {wib_now_str()}",
    )
    return pdf_bytes, "application/pdf", filename


def list_student_periods(db: Session, user: User) -> list[dict[str, Any]]:
    if user.role != "Mahasiswa":
        raise HTTPException(403, "Daftar periode mahasiswa hanya untuk Mahasiswa")

    semester_rank = case((PeriodeAkademik.semester == "Genap", 1), else_=0)
    rows = db.execute(
        select(
            MahasiswaPeriode,
            PeriodeAkademik,
            KelasPeriode,
            Prodi,
            Angkatan,
            Kurikulum,
        )
        .join(PeriodeAkademik, MahasiswaPeriode.periode_id == PeriodeAkademik.id)
        .join(KelasPeriode, MahasiswaPeriode.kelas_periode_id == KelasPeriode.id)
        .join(Prodi, PeriodeAkademik.prodi_id == Prodi.id)
        .join(Mahasiswa, MahasiswaPeriode.mahasiswa_id == Mahasiswa.id)
        .join(Angkatan, Mahasiswa.angkatan_id == Angkatan.id)
        .join(Kurikulum, Angkatan.kurikulum_id == Kurikulum.id)
        .where(
            MahasiswaPeriode.mahasiswa_id == user.id,
            PeriodeAkademik.prodi_id == user.prodi_id,
        )
        .order_by(PeriodeAkademik.tahun_mulai.desc(), semester_rank.desc(), PeriodeAkademik.id)
    ).all()

    count_rows = db.execute(
        select(KelasPeriode.periode_id, func.count(PesertaKelasMK.kelas_mk_id))
        .join(KelasMK, PesertaKelasMK.kelas_mk_id == KelasMK.id)
        .join(KelasPeriode, KelasMK.kelas_periode_id == KelasPeriode.id)
        .join(PeriodeAkademik, KelasPeriode.periode_id == PeriodeAkademik.id)
        .where(
            PesertaKelasMK.mahasiswa_id == user.id,
            PeriodeAkademik.prodi_id == user.prodi_id,
        )
        .group_by(KelasPeriode.periode_id)
    ).all()
    course_counts = {pid: int(cnt) for pid, cnt in count_rows}

    return [
        {
            "periode_id": periode.id,
            "tahun_mulai": periode.tahun_mulai,
            "tahun_akademik": periode.tahun_akademik,
            "semester": periode.semester,
            "status_periode": periode.status,
            "kelas_periode_id": klass.id,
            "kode_kelas": klass.kode_kelas,
            "tingkat": klass.tingkat,
            "semester_studi": klass.semester_studi,
            "kelas": _class_label(prodi, klass),
            "status_mahasiswa": mp.status,
            "prodi_kode": prodi.kode_prodi,
            "prodi_nama": prodi.nama_prodi,
            "kurikulum_id": kurikulum.id,
            "kode_kurikulum": kurikulum.kode_kurikulum,
            "nama_kurikulum": kurikulum.nama,
            "tahun_masuk": angkatan.tahun_masuk,
            "jumlah_kelas_mk": course_counts.get(periode.id, 0),
        }
        for mp, periode, klass, prodi, angkatan, kurikulum in rows
    ]


def student_course_detail(db: Session, user: User, *, kelas_mk_id: UUID) -> dict[str, Any]:
    if user.role != "Mahasiswa":
        raise HTTPException(403, "Rincian nilai mata kuliah pribadi hanya untuk Mahasiswa")

    context = require_class_access(db, user, kelas_mk_id)
    course, klass, periode, mk, master, design, prodi = context
    dosen = db.get(User, design.dosen_id)
    dosen_nama = dosen.nama if dosen is not None else "-"
    design_summary = assessment.summary(db, user, design)

    instrument_rows = db.execute(
        select(InstrumenPenilaian, SubCPMK, CPMK)
        .join(SubCPMK, InstrumenPenilaian.sub_cpmk_id == SubCPMK.id)
        .join(CPMK, SubCPMK.cpmk_id == CPMK.id)
        .where(CPMK.rancangan_id == design.id)
        .order_by(
            CPMK.kode_cpmk,
            SubCPMK.kode_sub,
            InstrumenPenilaian.nama_instrumen,
            InstrumenPenilaian.id,
        )
    ).all()

    cpmk_ids = sorted({cpmk.id for _, _, cpmk in instrument_rows}, key=str)
    cpl_by_cpmk: dict[UUID, list[str]] = {}
    if cpmk_ids:
        cpl_rows = db.execute(
            select(CPMKCPL.cpmk_id, MasterCPL.kode_cpl)
            .join(MasterCPL, CPMKCPL.cpl_id == MasterCPL.id)
            .where(CPMKCPL.cpmk_id.in_(cpmk_ids))
            .order_by(MasterCPL.kode_cpl)
        ).all()
        for cpmk_id, kode_cpl in cpl_rows:
            codes = cpl_by_cpmk.setdefault(cpmk_id, [])
            if kode_cpl not in codes:
                codes.append(kode_cpl)

    grade_map = {
        row.instrumen_id: row
        for row in db.scalars(
            select(NilaiMahasiswa).where(
                NilaiMahasiswa.kelas_mk_id == course.id,
                NilaiMahasiswa.mahasiswa_id == user.id,
            )
        )
    }

    instruments_payload: list[dict[str, Any]] = []
    for inst, sub, cpmk in instrument_rows:
        grade = grade_map.get(inst.id)
        instruments_payload.append(
            {
                "instrumen_id": inst.id,
                "nama_instrumen": inst.nama_instrumen,
                "bobot_persentase": inst.bobot_persentase,
                "sub_cpmk_id": sub.id,
                "kode_sub": sub.kode_sub,
                "deskripsi_sub": sub.deskripsi,
                "cpmk_id": cpmk.id,
                "kode_cpmk": cpmk.kode_cpmk,
                "deskripsi_cpmk": cpmk.deskripsi,
                "cpl_kodes": cpl_by_cpmk.get(cpmk.id, []),
                "nilai_mentah": grade.nilai_mentah if grade is not None else None,
                "status": "Sudah diinput" if grade is not None else "Belum diinput",
                "waktu_input": grade.waktu_input if grade is not None else None,
            }
        )

    class_res = outcomes.class_outcomes(db, user, course.id)
    hasil = class_res["peserta"][0]["hasil"] if class_res["peserta"] else []

    return {
        "kelas_mk_id": course.id,
        "periode_id": periode.id,
        "tahun_akademik": periode.tahun_akademik,
        "semester": periode.semester,
        "status_periode": periode.status,
        "kelas": _class_label(prodi, klass),
        "kode_mk": master.kode_mk,
        "nama_mk": mk.nama_mk,
        "sks": mk.sks,
        "semester_mk": mk.semester,
        "dosen_nama": dosen_nama,
        "siap_dinilai": design_summary.siap_dinilai,
        "total_bobot": design_summary.total_bobot,
        "instrumen": instruments_payload,
        "hasil": hasil,
    }
