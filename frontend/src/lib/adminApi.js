import { apiRequest } from './apiClient.js';

export function loginToken(email, password) {
  const formBody = new URLSearchParams();
  formBody.set('username', email.trim());
  formBody.set('password', password);
  return apiRequest('/api/v1/auth/token', {
    method: 'POST',
    formBody,
    skipAuth: true,
  });
}

export function getMe() {
  return apiRequest('/api/v1/auth/me');
}

export function logoutSession() {
  return apiRequest('/api/v1/auth/logout', { method: 'POST' });
}

// --- Master Mata Kuliah ---
export function listMataKuliah({ offset = 0, limit = 100, q } = {}) {
  return apiRequest('/api/v1/mata-kuliah', {
    params: { offset, limit, q },
  });
}

export function createMataKuliah(payload) {
  return apiRequest('/api/v1/mata-kuliah', {
    method: 'POST',
    body: payload,
  });
}

export function updateMataKuliah(mkId, payload) {
  return apiRequest(`/api/v1/mata-kuliah/${mkId}`, {
    method: 'PATCH',
    body: payload,
  });
}

export function deleteMataKuliah(mkId) {
  return apiRequest(`/api/v1/mata-kuliah/${mkId}`, {
    method: 'DELETE',
  });
}

// --- Kurikulum ---
export function listKurikulum({ offset = 0, limit = 100, q, status } = {}) {
  return apiRequest('/api/v1/kurikulum', {
    params: { offset, limit, q, status },
  });
}

export function createKurikulum(payload) {
  return apiRequest('/api/v1/kurikulum', {
    method: 'POST',
    body: payload,
  });
}

export function updateKurikulum(kurikulumId, payload) {
  return apiRequest(`/api/v1/kurikulum/${kurikulumId}`, {
    method: 'PATCH',
    body: payload,
  });
}

export function deleteKurikulum(kurikulumId) {
  return apiRequest(`/api/v1/kurikulum/${kurikulumId}`, {
    method: 'DELETE',
  });
}

export function activateKurikulum(kurikulumId) {
  return apiRequest(`/api/v1/kurikulum/${kurikulumId}/aktifkan`, {
    method: 'POST',
  });
}

export function archiveKurikulum(kurikulumId) {
  return apiRequest(`/api/v1/kurikulum/${kurikulumId}/arsipkan`, {
    method: 'POST',
  });
}

export function cloneKurikulum(kurikulumId, payload) {
  return apiRequest(`/api/v1/kurikulum/${kurikulumId}/salin`, {
    method: 'POST',
    body: payload,
  });
}

// --- Paket MK per Kurikulum ---
export function listPaketMk(
  kurikulumId,
  { offset = 0, limit = 100, q, semester } = {},
) {
  return apiRequest(`/api/v1/kurikulum/${kurikulumId}/mata-kuliah`, {
    params: { offset, limit, q, semester },
  });
}

export function createPaketMk(kurikulumId, payload) {
  return apiRequest(`/api/v1/kurikulum/${kurikulumId}/mata-kuliah`, {
    method: 'POST',
    body: {
      ...payload,
      sks: Number(payload.sks),
      semester: Number(payload.semester),
    },
  });
}

export function updatePaketMk(kurikulumId, kurikulumMkId, payload) {
  const normalized = { ...payload };
  if (normalized.sks !== undefined) normalized.sks = Number(normalized.sks);
  if (normalized.semester !== undefined) {
    normalized.semester = Number(normalized.semester);
  }
  return apiRequest(
    `/api/v1/kurikulum/${kurikulumId}/mata-kuliah/${kurikulumMkId}`,
    {
      method: 'PATCH',
      body: normalized,
    },
  );
}

export function deletePaketMk(kurikulumId, kurikulumMkId) {
  return apiRequest(
    `/api/v1/kurikulum/${kurikulumId}/mata-kuliah/${kurikulumMkId}`,
    {
      method: 'DELETE',
    },
  );
}

// --- Master CPL ---
export function listCpl(kurikulumId, { offset = 0, limit = 100, q } = {}) {
  return apiRequest(`/api/v1/kurikulum/${kurikulumId}/cpl`, {
    params: { offset, limit, q },
  });
}

export function createCpl(kurikulumId, payload) {
  return apiRequest(`/api/v1/kurikulum/${kurikulumId}/cpl`, {
    method: 'POST',
    body: payload,
  });
}

export function updateCpl(kurikulumId, cplId, payload) {
  return apiRequest(`/api/v1/kurikulum/${kurikulumId}/cpl/${cplId}`, {
    method: 'PATCH',
    body: payload,
  });
}

export function deleteCpl(kurikulumId, cplId) {
  return apiRequest(`/api/v1/kurikulum/${kurikulumId}/cpl/${cplId}`, {
    method: 'DELETE',
  });
}

// --- Matriks Pembebanan MK-CPL ---
export function getMatriksMk(kurikulumId, kurikulumMkId) {
  return apiRequest(
    `/api/v1/kurikulum/${kurikulumId}/mata-kuliah/${kurikulumMkId}/cpl`,
  );
}

export function replaceMatriksMk(kurikulumId, kurikulumMkId, items) {
  return apiRequest(
    `/api/v1/kurikulum/${kurikulumId}/mata-kuliah/${kurikulumMkId}/cpl`,
    {
      method: 'PUT',
      body: {
        items: items.map((item) => ({
          cpl_id: item.cpl_id,
          urutan_rps:
            item.urutan_rps === null ||
            item.urutan_rps === undefined ||
            item.urutan_rps === ''
              ? null
              : Number(item.urutan_rps),
        })),
      },
    },
  );
}

// --- Angkatan & Mahasiswa ---
export function listAngkatan({ offset = 0, limit = 100, tahun_masuk } = {}) {
  return apiRequest('/api/v1/angkatan', {
    params: { offset, limit, tahun_masuk },
  });
}

export function createAngkatan(payload) {
  return apiRequest('/api/v1/angkatan', {
    method: 'POST',
    body: {
      ...payload,
      tahun_masuk: Number(payload.tahun_masuk),
    },
  });
}

export function updateAngkatan(angkatanId, payload) {
  const normalized = { ...payload };
  if (normalized.tahun_masuk !== undefined) {
    normalized.tahun_masuk = Number(normalized.tahun_masuk);
  }
  return apiRequest(`/api/v1/angkatan/${angkatanId}`, {
    method: 'PATCH',
    body: normalized,
  });
}

export function deleteAngkatan(angkatanId) {
  return apiRequest(`/api/v1/angkatan/${angkatanId}`, {
    method: 'DELETE',
  });
}

export function listAngkatanMahasiswa(
  angkatanId,
  { offset = 0, limit = 100 } = {},
) {
  return apiRequest(`/api/v1/angkatan/${angkatanId}/mahasiswa`, {
    params: { offset, limit },
  });
}

export function linkAngkatanMahasiswa(angkatanId, userId) {
  return apiRequest(`/api/v1/angkatan/${angkatanId}/mahasiswa`, {
    method: 'POST',
    body: { user_id: userId },
  });
}

// --- Periode Akademik ---
export function listPeriode({
  offset = 0,
  limit = 100,
  tahun_mulai,
  semester,
} = {}) {
  return apiRequest('/api/v1/periode-akademik', {
    params: { offset, limit, tahun_mulai, semester },
  });
}

export function createPeriode(payload) {
  return apiRequest('/api/v1/periode-akademik', {
    method: 'POST',
    body: {
      ...payload,
      tahun_mulai: Number(payload.tahun_mulai),
    },
  });
}

export function updatePeriode(periodeId, payload) {
  const normalized = { ...payload };
  if (normalized.tahun_mulai !== undefined) {
    normalized.tahun_mulai = Number(normalized.tahun_mulai);
  }
  return apiRequest(`/api/v1/periode-akademik/${periodeId}`, {
    method: 'PATCH',
    body: normalized,
  });
}

export function deletePeriode(periodeId) {
  return apiRequest(`/api/v1/periode-akademik/${periodeId}`, {
    method: 'DELETE',
  });
}

// --- Kelas Periode ---
export function listKelasPeriode(
  periodeId,
  { offset = 0, limit = 100, angkatan_id } = {},
) {
  return apiRequest(`/api/v1/periode-akademik/${periodeId}/kelas`, {
    params: { offset, limit, angkatan_id },
  });
}

export function createKelasPeriode(periodeId, payload) {
  return apiRequest(`/api/v1/periode-akademik/${periodeId}/kelas`, {
    method: 'POST',
    body: {
      ...payload,
      semester_studi:
        payload.kode_kelas === 'K' ? null : Number(payload.semester_studi),
    },
  });
}

export function updateKelasPeriode(periodeId, kelasId, payload) {
  const normalized = { ...payload };
  if (normalized.kode_kelas === 'K') {
    normalized.semester_studi = null;
  } else if (
    normalized.semester_studi !== undefined &&
    normalized.semester_studi !== null
  ) {
    normalized.semester_studi = Number(normalized.semester_studi);
  }
  return apiRequest(`/api/v1/periode-akademik/${periodeId}/kelas/${kelasId}`, {
    method: 'PATCH',
    body: normalized,
  });
}

export function deleteKelasPeriode(periodeId, kelasId) {
  return apiRequest(`/api/v1/periode-akademik/${periodeId}/kelas/${kelasId}`, {
    method: 'DELETE',
  });
}

// --- Roster Mahasiswa per Periode ---
export function listRoster(
  periodeId,
  { offset = 0, limit = 100, kelas_periode_id, status } = {},
) {
  return apiRequest(`/api/v1/periode-akademik/${periodeId}/mahasiswa`, {
    params: { offset, limit, kelas_periode_id, status },
  });
}

export function createRoster(periodeId, payload) {
  return apiRequest(`/api/v1/periode-akademik/${periodeId}/mahasiswa`, {
    method: 'POST',
    body: payload,
  });
}

export function updateRoster(periodeId, mahasiswaId, payload) {
  return apiRequest(
    `/api/v1/periode-akademik/${periodeId}/mahasiswa/${mahasiswaId}`,
    {
      method: 'PATCH',
      body: payload,
    },
  );
}

export function deleteRoster(periodeId, mahasiswaId) {
  return apiRequest(
    `/api/v1/periode-akademik/${periodeId}/mahasiswa/${mahasiswaId}`,
    {
      method: 'DELETE',
    },
  );
}

// --- Paket & Pengampu ---
export function listDosen({ offset = 0, limit = 100, q, aktif = true } = {}) {
  return apiRequest('/api/v1/dosen', {
    params: { offset, limit, q, aktif },
  });
}

export function getPaketPreview(periodeId, angkatanId) {
  return apiRequest(
    `/api/v1/periode-akademik/${periodeId}/angkatan/${angkatanId}/paket`,
  );
}

export function applyPaket(periodeId, angkatanId, penugasan) {
  return apiRequest(
    `/api/v1/periode-akademik/${periodeId}/angkatan/${angkatanId}/paket/terapkan`,
    {
      method: 'POST',
      body: { penugasan },
    },
  );
}

export function changePengampu(kelasMkId, dosenId) {
  return apiRequest(`/api/v1/kelas-mk/${kelasMkId}/pengampu`, {
    method: 'PATCH',
    body: { dosen_id: dosenId },
  });
}

// --- Penguncian Periode (Admin) ---
export function closePeriode(periodeId) {
  return apiRequest(`/api/v1/periode-akademik/${periodeId}/tutup`, {
    method: 'POST',
  });
}

export function reopenPeriode(periodeId, alasan) {
  return apiRequest(`/api/v1/periode-akademik/${periodeId}/buka-kembali`, {
    method: 'POST',
    body: { alasan },
  });
}

// --- Kelas MK, Nilai, & Capaian ---
export function listKelasMk(periodeId, { offset = 0, limit = 100 } = {}) {
  return apiRequest('/api/v1/kelas-mk', {
    params: { periode_id: periodeId, offset, limit },
  });
}

export function getKelasMkDetail(kelasMkId) {
  return apiRequest(`/api/v1/kelas-mk/${kelasMkId}`);
}

export function getKelasMkPeserta(kelasMkId) {
  return apiRequest(`/api/v1/kelas-mk/${kelasMkId}/peserta`);
}

export function getKelasMkNilai(kelasMkId) {
  return apiRequest(`/api/v1/kelas-mk/${kelasMkId}/nilai`);
}

export function getKelasMkCapaian(kelasMkId) {
  return apiRequest(`/api/v1/kelas-mk/${kelasMkId}/capaian`);
}
