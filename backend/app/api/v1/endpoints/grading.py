from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from app.api.dependencies import DB, CurrentUser, require_roles
from app.models import User
from app.schemas.grading import (
    ClassAttainment,
    GradeBatch,
    GradeResponse,
    PeriodState,
    PersonalAttainment,
    ReopenPeriod,
)
from app.services import grading, outcomes

Admin = Annotated[User, Depends(require_roles("Admin"))]
Dosen = Annotated[User, Depends(require_roles("Dosen"))]
Mahasiswa = Annotated[User, Depends(require_roles("Mahasiswa"))]
router = APIRouter(tags=["nilai-dan-capaian"])


@router.get("/kelas-mk/{kelas_mk_id}/nilai", response_model=list[GradeResponse])
def read_grades(db: DB, user: CurrentUser, kelas_mk_id: UUID):
    return grading.list_grades(db, user, kelas_mk_id)


@router.put("/kelas-mk/{kelas_mk_id}/nilai", response_model=list[GradeResponse])
def write_grades(db: DB, user: Dosen, kelas_mk_id: UUID, payload: GradeBatch):
    return grading.save_grades(db, user, kelas_mk_id, payload)


@router.post("/periode-akademik/{periode_id}/tutup", response_model=PeriodState)
def close_period(db: DB, user: Admin, periode_id: UUID):
    return grading.transition_period(db, user, periode_id)


@router.post("/periode-akademik/{periode_id}/buka-kembali", response_model=PeriodState)
def reopen_period(db: DB, user: Admin, periode_id: UUID, payload: ReopenPeriod):
    return grading.transition_period(db, user, periode_id, reopen=True, reason=payload.alasan)


@router.get("/kelas-mk/{kelas_mk_id}/capaian", response_model=ClassAttainment)
def class_attainment(db: DB, user: CurrentUser, kelas_mk_id: UUID):
    return outcomes.class_outcomes(db, user, kelas_mk_id)


@router.get("/capaian/saya", response_model=PersonalAttainment)
def personal_attainment(db: DB, user: Mahasiswa, periode_id: UUID, kumulatif: bool = False):
    return outcomes.personal_outcomes(db, user, periode_id, kumulatif)
