"""Decimal OBE calculations over enrolled instruments; never substitute missing scores."""

from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import case, or_, select

from app.models import (
    CPMK,
    CPMKCPL,
    KelasMK,
    NilaiMahasiswa,
    PeriodeAkademik,
    PesertaKelasMK,
    SubCPMK,
)
from app.services import academic, assessment
from app.services.access import accessible_classes, require_class_access

ZERO = Decimal(0)
CENT = Decimal("0.01")


def rounded(value):
    return value.quantize(CENT, rounding=ROUND_HALF_UP) if value is not None else None


@dataclass
class Node:
    jenis: str
    id: UUID
    kode: str
    label: str
    kurikulum_id: UUID
    ready: bool
    weights: dict = field(default_factory=dict)

    def metadata(self):
        return dict(
            jenis=self.jenis,
            id=self.id,
            kode=self.kode,
            label=self.label,
            kurikulum_id=self.kurikulum_id,
        )


def nodes_for_class(db, user, context):
    course, _, _, mk, master, design, _ = context
    ready = assessment.summary(db, user, design).siap_dinilai
    nodes = {}

    def add(kind, row_id, code, label):
        node = Node(kind, row_id, code, label, mk.kurikulum_id, ready)
        nodes[(kind, row_id)] = node
        return node

    course_node = add("Mata kuliah", course.id, master.kode_mk, mk.nama_mk)
    cpmks = list(db.scalars(select(CPMK).where(CPMK.rancangan_id == design.id)))
    for c in cpmks:
        add("CPMK", c.id, c.kode_cpmk, c.deskripsi)
    subs = list(db.scalars(select(SubCPMK).where(SubCPMK.cpmk_id.in_([c.id for c in cpmks]))))
    for s in subs:
        add("Sub-CPMK", s.id, s.kode_sub, s.deskripsi)
    for cpl in assessment.allowed_cpl(db, design, user):
        add("CPL", cpl.id, cpl.kode_cpl, cpl.deskripsi)
    mappings = db.execute(
        select(CPMKCPL.cpmk_id, CPMKCPL.cpl_id).where(CPMKCPL.cpmk_id.in_([c.id for c in cpmks]))
    ).all()
    sub_parent = {s.id: s.cpmk_id for s in subs}
    for i in db.scalars(assessment.instrument_query(design.id)):
        cpmk_id = sub_parent[i.sub_cpmk_id]
        destinations = [course_node, nodes[("Sub-CPMK", i.sub_cpmk_id)], nodes[("CPMK", cpmk_id)]]
        destinations += [
            nodes[("CPL", cpl_id)]
            for parent, cpl_id in mappings
            if parent == cpmk_id and ("CPL", cpl_id) in nodes
        ]
        for node in destinations:
            # Instrument contributes once per CPL, independently of how many CPL it maps to.
            node.weights[(course.id, i.id)] = i.bobot_persentase
    return sorted(nodes.values(), key=lambda n: (n.jenis, n.kode, str(n.id)))


def evaluate(node, scores):
    complete = sum(key in scores for key in node.weights)
    if not node.ready:
        return None, "Belum siap dinilai", complete
    denominator = sum(node.weights.values(), ZERO)
    if not denominator or complete != len(node.weights):
        return None, "Belum lengkap", complete
    numerator = sum((scores[key] * weight for key, weight in node.weights.items()), ZERO)
    return numerator / denominator, "Lengkap", complete


def student_result(node, scores):
    value, status, complete = evaluate(node, scores)
    return dict(
        **node.metadata(),
        capaian=rounded(value),
        status=status,
        instrumen_lengkap=complete,
        total_instrumen=len(node.weights),
    )


def scores_for(db, class_ids, *, student_id=None):
    query = select(NilaiMahasiswa).where(NilaiMahasiswa.kelas_mk_id.in_(class_ids))
    if student_id is not None:
        query = query.where(NilaiMahasiswa.mahasiswa_id == student_id)
    result = {}
    for g in db.scalars(query):
        result.setdefault(g.mahasiswa_id, {})[(g.kelas_mk_id, g.instrumen_id)] = g.nilai_mentah
    return result


def class_outcomes(db, user, class_id):
    context = require_class_access(db, user, class_id)
    nodes = nodes_for_class(db, user, context)
    participants = list(
        db.scalars(
            select(PesertaKelasMK.mahasiswa_id)
            .where(PesertaKelasMK.kelas_mk_id == class_id)
            .order_by(PesertaKelasMK.mahasiswa_id)
        )
    )
    # A student's class view contains only that student's grades, never class averages/peers.
    if user.role == "Mahasiswa":
        participants = [user.id]
    scores = scores_for(db, [class_id], student_id=user.id if user.role == "Mahasiswa" else None)
    students = [
        dict(mahasiswa_id=s, hasil=[student_result(n, scores.get(s, {})) for n in nodes])
        for s in participants
    ]
    averages = []
    if user.role != "Mahasiswa":
        for node in nodes:
            # Average raw Decimal values; rounding student displays first would bias the mean.
            values = [evaluate(node, scores.get(s, {}))[0] for s in participants]
            values = [v for v in values if v is not None]
            mean = sum(values, ZERO) / len(values) if values else None
            status = (
                "Belum siap dinilai"
                if not node.ready
                else "Lengkap"
                if values and len(values) == len(participants)
                else "Belum lengkap"
            )
            averages.append(
                dict(
                    **node.metadata(),
                    capaian=rounded(mean),
                    status=status,
                    mahasiswa_lengkap=len(values),
                    total_mahasiswa=len(participants),
                )
            )
    return dict(kelas_mk_id=class_id, periode_id=context[2].id, peserta=students, rekap=averages)


def personal_outcomes(db, user, period_id, cumulative):
    if user.role != "Mahasiswa":
        raise HTTPException(403, "Capaian pribadi hanya untuk Mahasiswa yang login")
    period = academic.period(db, user, period_id)
    query = accessible_classes(user)
    if cumulative:
        semester_order = case((PeriodeAkademik.semester == "Ganjil", 0), else_=1)
        query = query.where(
            or_(
                PeriodeAkademik.tahun_mulai < period.tahun_mulai,
                (PeriodeAkademik.tahun_mulai == period.tahun_mulai)
                & (semester_order <= (0 if period.semester == "Ganjil" else 1)),
            )
        )
    else:
        query = query.where(PeriodeAkademik.id == period.id)
    contexts = db.execute(query.order_by(KelasMK.id)).all()
    merged = {}
    for context in contexts:
        for node in nodes_for_class(db, user, context):
            if node.jenis != "CPL":
                continue
            # UUID CPL is version-scoped: matching codes across curricula never merge.
            key = (node.kurikulum_id, node.id)
            if key not in merged:
                merged[key] = node
            else:
                merged[key].weights.update(node.weights)
                merged[key].ready = merged[key].ready and node.ready
    ids = [c[0].id for c in contexts]
    scores = scores_for(db, ids, student_id=user.id).get(user.id, {})
    return dict(
        mahasiswa_id=user.id,
        periode_id=period.id,
        tahun_akademik=period.tahun_akademik,
        semester=period.semester,
        kumulatif=cumulative,
        kelas_mk_ids=ids,
        hasil=[
            student_result(node, scores)
            for node in sorted(
                merged.values(), key=lambda n: (str(n.kurikulum_id), n.kode, str(n.id))
            )
        ],
    )
