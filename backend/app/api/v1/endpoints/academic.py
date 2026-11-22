from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response

from app.api.dependencies import DB, require_roles
from app.models import Angkatan, User
from app.schemas.academic_admin import (
    AngkatanCreate,
    AngkatanPatch,
    AngkatanResponse,
    KelasCreate,
    KelasPatch,
    KelasResponse,
    MahasiswaLink,
    MahasiswaResponse,
    PeriodeCreate,
    PeriodePatch,
    PeriodeResponse,
    RosterCreate,
    RosterPatch,
    RosterResponse,
    Semester,
    StatusMahasiswa,
)
from app.services import academic as service
from app.services.curriculum import owned

Admin = Annotated[User, Depends(require_roles("Admin"))]
Offset = Annotated[int, Query(ge=0)]
Limit = Annotated[int, Query(ge=1, le=100)]
Tahun = Annotated[int | None, Query(ge=1900, le=9998)]
router = APIRouter(tags=["admin-akademik"])


@router.get("/angkatan", response_model=list[AngkatanResponse])
def list_angkatan(
    db: DB, user: Admin, offset: Offset = 0, limit: Limit = 50, tahun_masuk: Tahun = None
):
    return service.list_angkatan(db, user, offset, limit, tahun_masuk)


@router.post("/angkatan", response_model=AngkatanResponse, status_code=201)
def create_angkatan(db: DB, user: Admin, payload: AngkatanCreate):
    return service.create_angkatan(db, user, payload)


@router.get("/angkatan/{angkatan_id}", response_model=AngkatanResponse)
def get_angkatan(db: DB, user: Admin, angkatan_id: UUID):
    return owned(db, Angkatan, angkatan_id, user)


@router.patch("/angkatan/{angkatan_id}", response_model=AngkatanResponse)
def update_angkatan(db: DB, user: Admin, angkatan_id: UUID, payload: AngkatanPatch):
    return service.update_angkatan(db, user, angkatan_id, payload)


@router.delete("/angkatan/{angkatan_id}", status_code=204)
def delete_angkatan(db: DB, user: Admin, angkatan_id: UUID):
    service.delete_angkatan(db, user, angkatan_id)
    return Response(status_code=204)


@router.get("/angkatan/{angkatan_id}/mahasiswa", response_model=list[MahasiswaResponse])
def list_students(db: DB, user: Admin, angkatan_id: UUID, offset: Offset = 0, limit: Limit = 50):
    return service.list_students(db, user, angkatan_id, offset, limit)


@router.post("/angkatan/{angkatan_id}/mahasiswa", response_model=MahasiswaResponse, status_code=201)
def link_student(db: DB, user: Admin, angkatan_id: UUID, payload: MahasiswaLink):
    return service.link_student(db, user, angkatan_id, payload)


@router.get("/periode-akademik", response_model=list[PeriodeResponse])
def list_periods(
    db: DB,
    user: Admin,
    offset: Offset = 0,
    limit: Limit = 50,
    tahun_mulai: Tahun = None,
    semester: Semester | None = None,
):
    return service.list_periods(db, user, offset, limit, tahun_mulai, semester)


@router.post("/periode-akademik", response_model=PeriodeResponse, status_code=201)
def create_period(db: DB, user: Admin, payload: PeriodeCreate):
    return service.create_period(db, user, payload)


@router.get("/periode-akademik/{periode_id}", response_model=PeriodeResponse)
def get_period(db: DB, user: Admin, periode_id: UUID):
    return service.period(db, user, periode_id)


@router.patch("/periode-akademik/{periode_id}", response_model=PeriodeResponse)
def update_period(db: DB, user: Admin, periode_id: UUID, payload: PeriodePatch):
    return service.update_period(db, user, periode_id, payload)


@router.delete("/periode-akademik/{periode_id}", status_code=204)
def delete_period(db: DB, user: Admin, periode_id: UUID):
    service.delete_period(db, user, periode_id)
    return Response(status_code=204)


@router.get("/periode-akademik/{periode_id}/kelas", response_model=list[KelasResponse])
def list_classes(
    db: DB,
    user: Admin,
    periode_id: UUID,
    offset: Offset = 0,
    limit: Limit = 50,
    angkatan_id: UUID | None = None,
):
    return service.list_classes(db, user, periode_id, offset, limit, angkatan_id)


@router.post("/periode-akademik/{periode_id}/kelas", response_model=KelasResponse, status_code=201)
def create_class(db: DB, user: Admin, periode_id: UUID, payload: KelasCreate):
    return service.create_class(db, user, periode_id, payload)


@router.get("/periode-akademik/{periode_id}/kelas/{kelas_id}", response_model=KelasResponse)
def get_class(db: DB, user: Admin, periode_id: UUID, kelas_id: UUID):
    service.period(db, user, periode_id)
    return service.class_response(db, user, service.class_in_period(db, periode_id, kelas_id))


@router.patch("/periode-akademik/{periode_id}/kelas/{kelas_id}", response_model=KelasResponse)
def update_class(db: DB, user: Admin, periode_id: UUID, kelas_id: UUID, payload: KelasPatch):
    return service.update_class(db, user, periode_id, kelas_id, payload)


@router.delete("/periode-akademik/{periode_id}/kelas/{kelas_id}", status_code=204)
def delete_class(db: DB, user: Admin, periode_id: UUID, kelas_id: UUID):
    service.delete_class(db, user, periode_id, kelas_id)
    return Response(status_code=204)


@router.get("/periode-akademik/{periode_id}/mahasiswa", response_model=list[RosterResponse])
def list_roster(
    db: DB,
    user: Admin,
    periode_id: UUID,
    offset: Offset = 0,
    limit: Limit = 50,
    kelas_periode_id: UUID | None = None,
    status: StatusMahasiswa | None = None,
):
    return service.list_roster(db, user, periode_id, offset, limit, kelas_periode_id, status)


@router.post(
    "/periode-akademik/{periode_id}/mahasiswa", response_model=RosterResponse, status_code=201
)
def create_roster(db: DB, user: Admin, periode_id: UUID, payload: RosterCreate):
    return service.write_roster(db, user, periode_id, payload.mahasiswa_id, payload, create=True)


@router.get(
    "/periode-akademik/{periode_id}/mahasiswa/{mahasiswa_id}", response_model=RosterResponse
)
def get_roster(db: DB, user: Admin, periode_id: UUID, mahasiswa_id: UUID):
    service.period(db, user, periode_id)
    service.student(db, user, mahasiswa_id)
    return service.roster(db, periode_id, mahasiswa_id)


@router.patch(
    "/periode-akademik/{periode_id}/mahasiswa/{mahasiswa_id}", response_model=RosterResponse
)
def update_roster(db: DB, user: Admin, periode_id: UUID, mahasiswa_id: UUID, payload: RosterPatch):
    return service.write_roster(db, user, periode_id, mahasiswa_id, payload)


@router.delete("/periode-akademik/{periode_id}/mahasiswa/{mahasiswa_id}", status_code=204)
def delete_roster(db: DB, user: Admin, periode_id: UUID, mahasiswa_id: UUID):
    service.write_roster(db, user, periode_id, mahasiswa_id, None, remove=True)
    return Response(status_code=204)
