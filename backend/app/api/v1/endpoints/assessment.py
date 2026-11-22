from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response

from app.api.dependencies import DB, require_roles
from app.models import User
from app.schemas.assessment import (
    CopyDesign,
    CPLIds,
    CPMKCreate,
    CPMKPatch,
    CPMKResponse,
    DesignDetail,
    DesignSummary,
    InstrumentCreate,
    InstrumentPatch,
    InstrumentResponse,
    SubCreate,
    SubPatch,
    SubResponse,
)
from app.services import assessment as service

Dosen = Annotated[User, Depends(require_roles("Dosen"))]
Offset = Annotated[int, Query(ge=0)]
Limit = Annotated[int, Query(ge=1, le=100)]
router = APIRouter(tags=["dosen-rancangan-penilaian"])
ROOT = "/rancangan-penilaian"
CPMK_PATH = ROOT + "/{rancangan_id}/cpmk"
SUB_PATH = CPMK_PATH + "/{cpmk_id}/sub-cpmk"
INSTRUMENT_PATH = SUB_PATH + "/{sub_id}/instrumen"


@router.get(ROOT, response_model=list[DesignSummary])
def list_designs(
    db: DB, user: Dosen, periode_id: UUID | None = None, offset: Offset = 0, limit: Limit = 50
):
    return service.list_designs(db, user, periode_id, offset, limit)


@router.get(ROOT + "/{rancangan_id}", response_model=DesignDetail)
def detail(db: DB, user: Dosen, rancangan_id: UUID):
    return service.detail(db, user, rancangan_id)


@router.get("/kelas-mk/{kelas_mk_id}/rancangan-penilaian", response_model=DesignDetail)
def class_design(db: DB, user: Dosen, kelas_mk_id: UUID):
    return service.class_design(db, user, kelas_mk_id)


@router.post(ROOT + "/{rancangan_id}/salin", response_model=DesignDetail)
def copy_design(db: DB, user: Dosen, rancangan_id: UUID, payload: CopyDesign):
    return service.copy_design(db, user, rancangan_id, payload)


@router.get(CPMK_PATH, response_model=list[CPMKResponse])
def list_cpmk(db: DB, user: Dosen, rancangan_id: UUID, offset: Offset = 0, limit: Limit = 50):
    return service.list_cpmk(db, user, rancangan_id, offset, limit)


@router.post(CPMK_PATH, response_model=CPMKResponse, status_code=201)
def create_cpmk(db: DB, user: Dosen, rancangan_id: UUID, payload: CPMKCreate):
    return service.create_cpmk(db, user, rancangan_id, payload)


@router.get(CPMK_PATH + "/{cpmk_id}", response_model=CPMKResponse)
def get_cpmk(db: DB, user: Dosen, rancangan_id: UUID, cpmk_id: UUID):
    return service.get_cpmk(db, user, rancangan_id, cpmk_id)


@router.patch(CPMK_PATH + "/{cpmk_id}", response_model=CPMKResponse)
def update_cpmk(db: DB, user: Dosen, rancangan_id: UUID, cpmk_id: UUID, payload: CPMKPatch):
    return service.update_cpmk(db, user, rancangan_id, cpmk_id, payload)


@router.delete(CPMK_PATH + "/{cpmk_id}", status_code=204)
def delete_cpmk(db: DB, user: Dosen, rancangan_id: UUID, cpmk_id: UUID):
    service.delete_cpmk(db, user, rancangan_id, cpmk_id)
    return Response(status_code=204)


@router.put(CPMK_PATH + "/{cpmk_id}/cpl", response_model=CPMKResponse)
def replace_cpl(db: DB, user: Dosen, rancangan_id: UUID, cpmk_id: UUID, payload: CPLIds):
    return service.replace_cpl(db, user, rancangan_id, cpmk_id, payload)


@router.get(SUB_PATH, response_model=list[SubResponse])
def list_sub(
    db: DB, user: Dosen, rancangan_id: UUID, cpmk_id: UUID, offset: Offset = 0, limit: Limit = 50
):
    return service.list_sub(db, user, rancangan_id, cpmk_id, offset, limit)


@router.post(SUB_PATH, response_model=SubResponse, status_code=201)
def create_sub(db: DB, user: Dosen, rancangan_id: UUID, cpmk_id: UUID, payload: SubCreate):
    return service.create_sub(db, user, rancangan_id, cpmk_id, payload)


@router.get(SUB_PATH + "/{sub_id}", response_model=SubResponse)
def get_sub(db: DB, user: Dosen, rancangan_id: UUID, cpmk_id: UUID, sub_id: UUID):
    return service.get_sub(db, user, rancangan_id, cpmk_id, sub_id)


@router.patch(SUB_PATH + "/{sub_id}", response_model=SubResponse)
def update_sub(
    db: DB, user: Dosen, rancangan_id: UUID, cpmk_id: UUID, sub_id: UUID, payload: SubPatch
):
    return service.update_sub(db, user, rancangan_id, cpmk_id, sub_id, payload)


@router.delete(SUB_PATH + "/{sub_id}", status_code=204)
def delete_sub(db: DB, user: Dosen, rancangan_id: UUID, cpmk_id: UUID, sub_id: UUID):
    service.delete_sub(db, user, rancangan_id, cpmk_id, sub_id)
    return Response(status_code=204)


@router.get(INSTRUMENT_PATH, response_model=list[InstrumentResponse])
def list_instrument(
    db: DB,
    user: Dosen,
    rancangan_id: UUID,
    cpmk_id: UUID,
    sub_id: UUID,
    offset: Offset = 0,
    limit: Limit = 50,
):
    return service.list_instrument(db, user, rancangan_id, cpmk_id, sub_id, offset, limit)


@router.post(INSTRUMENT_PATH, response_model=InstrumentResponse, status_code=201)
def create_instrument(
    db: DB, user: Dosen, rancangan_id: UUID, cpmk_id: UUID, sub_id: UUID, payload: InstrumentCreate
):
    return service.create_instrument(db, user, rancangan_id, cpmk_id, sub_id, payload)


@router.get(INSTRUMENT_PATH + "/{instrumen_id}", response_model=InstrumentResponse)
def get_instrument(
    db: DB, user: Dosen, rancangan_id: UUID, cpmk_id: UUID, sub_id: UUID, instrumen_id: UUID
):
    return service.get_instrument(db, user, rancangan_id, cpmk_id, sub_id, instrumen_id)


@router.patch(INSTRUMENT_PATH + "/{instrumen_id}", response_model=InstrumentResponse)
def update_instrument(
    db: DB,
    user: Dosen,
    rancangan_id: UUID,
    cpmk_id: UUID,
    sub_id: UUID,
    instrumen_id: UUID,
    payload: InstrumentPatch,
):
    return service.update_instrument(db, user, rancangan_id, cpmk_id, sub_id, instrumen_id, payload)


@router.delete(INSTRUMENT_PATH + "/{instrumen_id}", status_code=204)
def delete_instrument(
    db: DB, user: Dosen, rancangan_id: UUID, cpmk_id: UUID, sub_id: UUID, instrumen_id: UUID
):
    service.delete_instrument(db, user, rancangan_id, cpmk_id, sub_id, instrumen_id)
    return Response(status_code=204)
