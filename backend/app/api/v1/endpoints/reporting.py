"""Audit log, prodi/cross-class report, and CSV/PDF export endpoints."""

from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response

from app.api.dependencies import DB, require_roles
from app.models import User
from app.schemas.reporting import (
    AuditLogResponse,
    CrossClassReportResponse,
    ProdiReportResponse,
    StudentCourseDetailResponse,
    StudentPeriodResponse,
)
from app.services import reporting

Admin = Annotated[User, Depends(require_roles("Admin"))]
LecturerOrAdmin = Annotated[User, Depends(require_roles("Admin", "Dosen"))]
Mahasiswa = Annotated[User, Depends(require_roles("Mahasiswa"))]
Offset = Annotated[int, Query(ge=0)]
Limit = Annotated[int, Query(ge=1, le=100)]
Search = Annotated[str | None, Query(max_length=100)]
FilterTerm = Annotated[str | None, Query(max_length=50)]
SemesterFilter = Annotated[int | None, Query(ge=1, le=8)]
ExportFormat = Literal["csv", "pdf"]

router = APIRouter(tags=["laporan-dan-audit"])


def _attachment(data: bytes, media_type: str, filename: str) -> Response:
    return Response(
        content=data,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/audit-log", response_model=list[AuditLogResponse])
def audit_logs(
    db: DB,
    user: Admin,
    periode_id: UUID | None = None,
    aksi: FilterTerm = None,
    entitas: FilterTerm = None,
    q: Search = None,
    offset: Offset = 0,
    limit: Limit = 50,
):
    return reporting.list_audit_logs(
        db,
        user,
        periode_id=periode_id,
        aksi=aksi,
        entitas=entitas,
        q=q,
        offset=offset,
        limit=limit,
    )


@router.get("/laporan/prodi", response_model=ProdiReportResponse)
def read_prodi_report(
    db: DB,
    user: Admin,
    periode_id: UUID,
    kurikulum_id: UUID,
    semester: SemesterFilter = None,
):
    return reporting.prodi_report(
        db, user, periode_id=periode_id, kurikulum_id=kurikulum_id, semester=semester
    )


@router.get("/laporan/prodi/ekspor")
def export_prodi_report(
    db: DB,
    user: Admin,
    periode_id: UUID,
    kurikulum_id: UUID,
    format: ExportFormat = "csv",
    semester: SemesterFilter = None,
):
    data, media_type, filename = reporting.export_prodi_report(
        db,
        user,
        periode_id=periode_id,
        kurikulum_id=kurikulum_id,
        fmt=format,
        semester=semester,
    )
    return _attachment(data, media_type, filename)


@router.get("/laporan/lintas-kelas", response_model=CrossClassReportResponse)
def read_cross_class_report(
    db: DB,
    user: LecturerOrAdmin,
    periode_id: UUID,
    kelas_mk_ids: Annotated[list[UUID], Query(min_length=1, max_length=100)],
):
    return reporting.cross_class_report(db, user, periode_id=periode_id, kelas_mk_ids=kelas_mk_ids)


@router.get("/laporan/lintas-kelas/ekspor")
def export_cross_class_report(
    db: DB,
    user: LecturerOrAdmin,
    periode_id: UUID,
    kelas_mk_ids: Annotated[list[UUID], Query(min_length=1, max_length=100)],
    format: ExportFormat = "csv",
):
    data, media_type, filename = reporting.export_cross_class_report(
        db, user, periode_id=periode_id, kelas_mk_ids=kelas_mk_ids, fmt=format
    )
    return _attachment(data, media_type, filename)


@router.get("/kelas-mk/{kelas_mk_id}/ekspor")
def export_class_report(
    db: DB,
    user: LecturerOrAdmin,
    kelas_mk_id: UUID,
    format: ExportFormat = "csv",
):
    data, media_type, filename = reporting.export_class_report(
        db, user, kelas_mk_id=kelas_mk_id, fmt=format
    )
    return _attachment(data, media_type, filename)


@router.get("/capaian/saya/ekspor")
def export_personal_report(
    db: DB,
    user: Mahasiswa,
    periode_id: UUID,
    kumulatif: bool = False,
    format: ExportFormat = "pdf",
):
    data, media_type, filename = reporting.export_personal_report(
        db, user, periode_id=periode_id, kumulatif=kumulatif, fmt=format
    )
    return _attachment(data, media_type, filename)


@router.get("/mahasiswa/periode", response_model=list[StudentPeriodResponse])
def student_periods(db: DB, user: Mahasiswa):
    return reporting.list_student_periods(db, user)


@router.get(
    "/mahasiswa/kelas-mk/{kelas_mk_id}/rincian",
    response_model=StudentCourseDetailResponse,
)
def student_course_detail(db: DB, user: Mahasiswa, kelas_mk_id: UUID):
    return reporting.student_course_detail(db, user, kelas_mk_id=kelas_mk_id)
