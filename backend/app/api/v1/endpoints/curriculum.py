"""Admin curriculum routes. Write transactions and invariants belong to services."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response

from app.api.dependencies import DB, CurrentUser, require_roles
from app.models import KurikulumMK, MasterCPL, MataKuliah, ProfilLulusan, User
from app.schemas.curriculum import (
    CPLCreate,
    CPLPatch,
    CPLResponse,
    KurikulumCreate,
    KurikulumPatch,
    KurikulumResponse,
    MatriksReplace,
    MKCreate,
    MKPatch,
    MKResponse,
    PaketCreate,
    PaketPatch,
    PaketResponse,
    Pembebanan,
    PlMatriksReplace,
    ProfilLulusanCplLink,
    ProfilLulusanCreate,
    ProfilLulusanOverviewResponse,
    ProfilLulusanPatch,
    ProfilLulusanResponse,
    StatusKurikulum,
)
from app.services import curriculum as service

Admin = Annotated[User, Depends(require_roles("Admin"))]
Offset = Annotated[int, Query(ge=0)]
Limit = Annotated[int, Query(ge=1, le=100)]
Search = Annotated[str | None, Query(max_length=100)]
router = APIRouter(tags=["admin-kurikulum"])


@router.get("/mata-kuliah", response_model=list[MKResponse])
def list_mk(db: DB, user: Admin, offset: Offset = 0, limit: Limit = 50, q: Search = None):
    return service.list_mk(db, user, offset, limit, q)


@router.post("/mata-kuliah", response_model=MKResponse, status_code=201)
def create_mk(db: DB, user: Admin, payload: MKCreate):
    return service.create_mk(db, user, payload)


@router.get("/mata-kuliah/{mk_id}", response_model=MKResponse)
def get_mk(db: DB, user: Admin, mk_id: UUID):
    return service.owned(db, MataKuliah, mk_id, user)


@router.patch("/mata-kuliah/{mk_id}", response_model=MKResponse)
def update_mk(db: DB, user: Admin, mk_id: UUID, payload: MKPatch):
    return service.update_mk(db, user, mk_id, payload)


@router.delete("/mata-kuliah/{mk_id}", status_code=204)
def delete_mk(db: DB, user: Admin, mk_id: UUID):
    service.delete_mk(db, user, mk_id)
    return Response(status_code=204)


@router.get("/kurikulum", response_model=list[KurikulumResponse])
def list_curricula(
    db: DB,
    user: Admin,
    offset: Offset = 0,
    limit: Limit = 50,
    q: Search = None,
    status: StatusKurikulum | None = None,
):
    return service.list_curricula(db, user, offset, limit, q, status)


@router.post("/kurikulum", response_model=KurikulumResponse, status_code=201)
def create_curriculum(db: DB, user: Admin, payload: KurikulumCreate):
    return service.create_curriculum(db, user, payload)


@router.get("/kurikulum/{kurikulum_id}", response_model=KurikulumResponse)
def get_curriculum(db: DB, user: Admin, kurikulum_id: UUID):
    return service.curriculum(db, user, kurikulum_id)


@router.patch("/kurikulum/{kurikulum_id}", response_model=KurikulumResponse)
def update_curriculum(db: DB, user: Admin, kurikulum_id: UUID, payload: KurikulumPatch):
    return service.update_curriculum(db, user, kurikulum_id, payload)


@router.delete("/kurikulum/{kurikulum_id}", status_code=204)
def delete_curriculum(db: DB, user: Admin, kurikulum_id: UUID):
    service.delete_curriculum(db, user, kurikulum_id)
    return Response(status_code=204)


@router.post("/kurikulum/{kurikulum_id}/aktifkan", response_model=KurikulumResponse)
def activate(db: DB, user: Admin, kurikulum_id: UUID):
    return service.transition(db, user, kurikulum_id, "Aktif")


@router.post("/kurikulum/{kurikulum_id}/arsipkan", response_model=KurikulumResponse)
def archive(db: DB, user: Admin, kurikulum_id: UUID):
    return service.transition(db, user, kurikulum_id, "Arsip")


@router.post("/kurikulum/{kurikulum_id}/salin", response_model=KurikulumResponse, status_code=201)
def clone(db: DB, user: Admin, kurikulum_id: UUID, payload: KurikulumCreate):
    return service.clone(db, user, kurikulum_id, payload)


@router.get("/kurikulum/{kurikulum_id}/mata-kuliah", response_model=list[PaketResponse])
def list_paket(
    db: DB,
    user: Admin,
    kurikulum_id: UUID,
    offset: Offset = 0,
    limit: Limit = 50,
    q: Search = None,
    semester: Annotated[int | None, Query(ge=1, le=8)] = None,
):
    return service.list_children(db, user, kurikulum_id, KurikulumMK, offset, limit, q, semester)


@router.post("/kurikulum/{kurikulum_id}/mata-kuliah", response_model=PaketResponse, status_code=201)
def create_paket(db: DB, user: Admin, kurikulum_id: UUID, payload: PaketCreate):
    return service.create_paket(db, user, kurikulum_id, payload)


@router.get("/kurikulum/{kurikulum_id}/mata-kuliah/{kurikulum_mk_id}", response_model=PaketResponse)
def get_paket(db: DB, user: Admin, kurikulum_id: UUID, kurikulum_mk_id: UUID):
    service.curriculum(db, user, kurikulum_id)
    return service.child(db, KurikulumMK, kurikulum_mk_id, kurikulum_id)


@router.patch(
    "/kurikulum/{kurikulum_id}/mata-kuliah/{kurikulum_mk_id}", response_model=PaketResponse
)
def update_paket(
    db: DB, user: Admin, kurikulum_id: UUID, kurikulum_mk_id: UUID, payload: PaketPatch
):
    return service.update_paket(db, user, kurikulum_id, kurikulum_mk_id, payload)


@router.delete("/kurikulum/{kurikulum_id}/mata-kuliah/{kurikulum_mk_id}", status_code=204)
def delete_paket(db: DB, user: Admin, kurikulum_id: UUID, kurikulum_mk_id: UUID):
    service.delete_paket(db, user, kurikulum_id, kurikulum_mk_id)
    return Response(status_code=204)


@router.get("/kurikulum/{kurikulum_id}/cpl", response_model=list[CPLResponse])
def list_cpl(
    db: DB, user: Admin, kurikulum_id: UUID, offset: Offset = 0, limit: Limit = 50, q: Search = None
):
    return service.list_children(db, user, kurikulum_id, MasterCPL, offset, limit, q)


@router.post("/kurikulum/{kurikulum_id}/cpl", response_model=CPLResponse, status_code=201)
def create_cpl(db: DB, user: Admin, kurikulum_id: UUID, payload: CPLCreate):
    return service.create_cpl(db, user, kurikulum_id, payload)


@router.get("/kurikulum/{kurikulum_id}/cpl/{cpl_id}", response_model=CPLResponse)
def get_cpl(db: DB, user: Admin, kurikulum_id: UUID, cpl_id: UUID):
    service.curriculum(db, user, kurikulum_id)
    return service.child(db, MasterCPL, cpl_id, kurikulum_id)


@router.patch("/kurikulum/{kurikulum_id}/cpl/{cpl_id}", response_model=CPLResponse)
def update_cpl(db: DB, user: Admin, kurikulum_id: UUID, cpl_id: UUID, payload: CPLPatch):
    return service.update_cpl(db, user, kurikulum_id, cpl_id, payload)


@router.delete("/kurikulum/{kurikulum_id}/cpl/{cpl_id}", status_code=204)
def delete_cpl(db: DB, user: Admin, kurikulum_id: UUID, cpl_id: UUID):
    service.delete_cpl(db, user, kurikulum_id, cpl_id)
    return Response(status_code=204)


@router.get(
    "/kurikulum/{kurikulum_id}/mata-kuliah/{kurikulum_mk_id}/cpl", response_model=list[Pembebanan]
)
def get_matrix(db: DB, user: Admin, kurikulum_id: UUID, kurikulum_mk_id: UUID):
    return service.get_matrix(db, user, kurikulum_id, kurikulum_mk_id)


@router.put(
    "/kurikulum/{kurikulum_id}/mata-kuliah/{kurikulum_mk_id}/cpl", response_model=list[Pembebanan]
)
def replace_matrix(
    db: DB, user: Admin, kurikulum_id: UUID, kurikulum_mk_id: UUID, payload: MatriksReplace
):
    return service.replace_matrix(db, user, kurikulum_id, kurikulum_mk_id, payload)


@router.get("/kurikulum/{kurikulum_id}/profil-lulusan", response_model=list[ProfilLulusanResponse])
def list_profil_lulusan(
    db: DB, user: Admin, kurikulum_id: UUID, offset: Offset = 0, limit: Limit = 50, q: Search = None
):
    return service.list_children(db, user, kurikulum_id, ProfilLulusan, offset, limit, q)


@router.post(
    "/kurikulum/{kurikulum_id}/profil-lulusan",
    response_model=ProfilLulusanResponse,
    status_code=201,
)
def create_profil_lulusan(db: DB, user: Admin, kurikulum_id: UUID, payload: ProfilLulusanCreate):
    return service.create_profil_lulusan(db, user, kurikulum_id, payload)


@router.get(
    "/kurikulum/{kurikulum_id}/profil-lulusan/{pl_id}", response_model=ProfilLulusanResponse
)
def get_profil_lulusan(db: DB, user: Admin, kurikulum_id: UUID, pl_id: UUID):
    service.curriculum(db, user, kurikulum_id)
    return service.child(db, ProfilLulusan, pl_id, kurikulum_id)


@router.patch(
    "/kurikulum/{kurikulum_id}/profil-lulusan/{pl_id}", response_model=ProfilLulusanResponse
)
def update_profil_lulusan(
    db: DB, user: Admin, kurikulum_id: UUID, pl_id: UUID, payload: ProfilLulusanPatch
):
    return service.update_profil_lulusan(db, user, kurikulum_id, pl_id, payload)


@router.delete("/kurikulum/{kurikulum_id}/profil-lulusan/{pl_id}", status_code=204)
def delete_profil_lulusan(db: DB, user: Admin, kurikulum_id: UUID, pl_id: UUID):
    service.delete_profil_lulusan(db, user, kurikulum_id, pl_id)
    return Response(status_code=204)


@router.get(
    "/kurikulum/{kurikulum_id}/profil-lulusan/{pl_id}/cpl",
    response_model=list[ProfilLulusanCplLink],
)
def get_pl_matrix(db: DB, user: Admin, kurikulum_id: UUID, pl_id: UUID):
    return service.get_pl_matrix(db, user, kurikulum_id, pl_id)


@router.put(
    "/kurikulum/{kurikulum_id}/profil-lulusan/{pl_id}/cpl",
    response_model=list[ProfilLulusanCplLink],
)
def replace_pl_matrix(
    db: DB, user: Admin, kurikulum_id: UUID, pl_id: UUID, payload: PlMatriksReplace
):
    return service.replace_pl_matrix(db, user, kurikulum_id, pl_id, payload)


@router.get("/profil-lulusan/ringkasan", response_model=ProfilLulusanOverviewResponse)
def profil_lulusan_ringkasan(db: DB, user: CurrentUser, kurikulum_id: UUID | None = None):
    return service.profil_lulusan_overview(db, user, kurikulum_id)
