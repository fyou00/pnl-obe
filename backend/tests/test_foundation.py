import pytest
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from conftest import alembic_config
from fastapi.testclient import TestClient
from sqlalchemy import delete, func, inspect, select, text
from sqlalchemy.exc import IntegrityError

from alembic import command
from app.main import create_app
from app.models import (
    Base,
    InstrumenPenilaian,
    KelasMK,
    KelasPeriode,
    NilaiMahasiswa,
    PesertaKelasMK,
    RancanganPenilaian,
    User,
)
from app.services.seed import seed


def test_migration_roundtrip_and_metadata(engine):
    with engine.begin() as connection:
        assert set(inspect(connection).get_table_names()) == set(Base.metadata.tables) | {
            "alembic_version"
        }
        assert len(Base.metadata.tables) == 23
        assert compare_metadata(MigrationContext.configure(connection), Base.metadata) == []
        command.downgrade(alembic_config(connection), "base")
        assert inspect(connection).get_table_names() == ["alembic_version"]
        command.upgrade(alembic_config(connection), "head")
        assert compare_metadata(MigrationContext.configure(connection), Base.metadata) == []
        assert int(connection.scalar(text("SHOW server_version_num"))) >= 150000


def test_health_and_readiness(client):
    assert client.get("/health").json() == {"status": "ok"}
    assert client.get("/ready").json() == {"status": "ready"}


def test_readiness_rejects_missing_migrations(settings):
    with TestClient(create_app(settings)) as client:
        assert client.get("/health").status_code == 200
        response = client.get("/ready")
        assert response.status_code == 503
        assert "password" not in response.text.lower()


def test_seed_idempotent_and_password_preserved(db, seed_config):
    first = seed(db, seed_config, demo=True)
    db.commit()
    password_hash = db.get(User, first["admin_id"]).password_hash
    second = seed(db, seed_config, demo=True)
    db.commit()
    assert first == second
    assert db.scalar(select(func.count()).select_from(User)) == 3
    assert db.get(User, first["admin_id"]).password_hash == password_hash


def test_seed_failure_rolls_back_entire_batch(db, seed_config):
    config = seed_config.model_copy(update={"seed_mahasiswa_nim_nidn": None})
    with pytest.raises(ValueError), db.begin():
        seed(db, config, demo=True)
    assert db.scalar(select(func.count()).select_from(User)) == 0


def test_shared_design_and_no_repeated_enrollment(db, dataset):
    a, b = dataset["course_a"], dataset["course_b"]
    assert a.rancangan_id == b.rancangan_id
    with pytest.raises(IntegrityError), db.begin_nested():
        db.add(
            RancanganPenilaian(
                periode_id=dataset["period"].id,
                kurikulum_mk_id=dataset["kurikulum_mk"].id,
                dosen_id=dataset["dosen"].id,
            )
        )
        db.flush()
    with pytest.raises(IntegrityError), db.begin_nested():
        db.add(
            PesertaKelasMK(
                kelas_mk_id=b.id, mahasiswa_id=dataset["mahasiswa"].id, mk_id=dataset["mk"].id
            )
        )
        db.flush()
    with pytest.raises(IntegrityError), db.begin_nested():
        db.add(
            KelasMK(
                kelas_periode_id=a.kelas_periode_id,
                kurikulum_mk_id=a.kurikulum_mk_id,
                rancangan_id=a.rancangan_id,
            )
        )
        db.flush()


@pytest.mark.parametrize("value", [-1, 101])
def test_grade_range_rejected(db, dataset, value):
    with pytest.raises(IntegrityError), db.begin_nested():
        db.add(
            NilaiMahasiswa(
                instrumen_id=dataset["instrument"].id,
                kelas_mk_id=dataset["course_a"].id,
                mahasiswa_id=dataset["mahasiswa"].id,
                nilai_mentah=value,
                diubah_oleh=dataset["dosen"].id,
            )
        )
        db.flush()


def test_grade_requires_participant_and_history_is_restricted(db, dataset):
    with pytest.raises(IntegrityError), db.begin_nested():
        db.add(
            NilaiMahasiswa(
                instrumen_id=dataset["instrument"].id,
                kelas_mk_id=dataset["course_b"].id,
                mahasiswa_id=dataset["mahasiswa"].id,
                nilai_mentah=80,
                diubah_oleh=dataset["dosen"].id,
            )
        )
        db.flush()
    grade = NilaiMahasiswa(
        instrumen_id=dataset["instrument"].id,
        kelas_mk_id=dataset["course_a"].id,
        mahasiswa_id=dataset["mahasiswa"].id,
        nilai_mentah=0,
        diubah_oleh=dataset["dosen"].id,
    )
    db.add(grade)
    db.commit()
    assert grade.nilai_mentah == 0
    with pytest.raises(IntegrityError), db.begin_nested():
        db.execute(delete(InstrumenPenilaian).where(InstrumenPenilaian.id == grade.instrumen_id))
    with pytest.raises(IntegrityError), db.begin_nested():
        db.execute(delete(PesertaKelasMK).where(PesertaKelasMK.kelas_mk_id == grade.kelas_mk_id))
    with pytest.raises(IntegrityError), db.begin_nested():
        db.execute(delete(User).where(User.id == dataset["mahasiswa"].id))


@pytest.mark.parametrize("code,semester", [("K", 1), ("A", None), ("A", 9)])
def test_class_k_and_semester_constraints(db, dataset, code, semester):
    with pytest.raises(IntegrityError), db.begin_nested():
        db.add(
            KelasPeriode(
                periode_id=dataset["period"].id,
                angkatan_id=dataset["angkatan"].id,
                kode_kelas=code,
                semester_studi=semester,
            )
        )
        db.flush()
