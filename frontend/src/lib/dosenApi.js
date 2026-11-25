import { apiDownload, apiRequest } from './apiClient.js';

export function listRancangan({ periode_id, offset = 0, limit = 100 } = {}) {
  return apiRequest('/api/v1/rancangan-penilaian', {
    params: { periode_id, offset, limit },
  });
}

export function getRancanganDetail(rancanganId) {
  return apiRequest(`/api/v1/rancangan-penilaian/${rancanganId}`);
}

export function getKelasRancangan(kelasMkId) {
  return apiRequest(`/api/v1/kelas-mk/${kelasMkId}/rancangan-penilaian`);
}

export function copyRancangan(rancanganId, sumberRancanganId) {
  return apiRequest(`/api/v1/rancangan-penilaian/${rancanganId}/salin`, {
    method: 'POST',
    body: { sumber_rancangan_id: sumberRancanganId },
  });
}

// --- CPMK & Pemetaan CPL ---
export function createCpmk(rancanganId, payload) {
  return apiRequest(`/api/v1/rancangan-penilaian/${rancanganId}/cpmk`, {
    method: 'POST',
    body: payload,
  });
}

export function updateCpmk(rancanganId, cpmkId, payload) {
  return apiRequest(
    `/api/v1/rancangan-penilaian/${rancanganId}/cpmk/${cpmkId}`,
    {
      method: 'PATCH',
      body: payload,
    },
  );
}

export function deleteCpmk(rancanganId, cpmkId) {
  return apiRequest(
    `/api/v1/rancangan-penilaian/${rancanganId}/cpmk/${cpmkId}`,
    {
      method: 'DELETE',
    },
  );
}

export function replaceCpmkCpl(rancanganId, cpmkId, cplIds) {
  return apiRequest(
    `/api/v1/rancangan-penilaian/${rancanganId}/cpmk/${cpmkId}/cpl`,
    {
      method: 'PUT',
      body: { cpl_ids: cplIds },
    },
  );
}

// --- Sub-CPMK ---
export function createSubCpmk(rancanganId, cpmkId, payload) {
  return apiRequest(
    `/api/v1/rancangan-penilaian/${rancanganId}/cpmk/${cpmkId}/sub-cpmk`,
    {
      method: 'POST',
      body: payload,
    },
  );
}

export function updateSubCpmk(rancanganId, cpmkId, subId, payload) {
  return apiRequest(
    `/api/v1/rancangan-penilaian/${rancanganId}/cpmk/${cpmkId}/sub-cpmk/${subId}`,
    {
      method: 'PATCH',
      body: payload,
    },
  );
}

export function deleteSubCpmk(rancanganId, cpmkId, subId) {
  return apiRequest(
    `/api/v1/rancangan-penilaian/${rancanganId}/cpmk/${cpmkId}/sub-cpmk/${subId}`,
    {
      method: 'DELETE',
    },
  );
}

// --- Instrumen Penilaian ---
function normalizeWeight(weight) {
  const num = Number(String(weight).replace(',', '.'));
  return num.toFixed(2);
}

export function createInstrumen(rancanganId, cpmkId, subId, payload) {
  return apiRequest(
    `/api/v1/rancangan-penilaian/${rancanganId}/cpmk/${cpmkId}/sub-cpmk/${subId}/instrumen`,
    {
      method: 'POST',
      body: {
        ...payload,
        bobot_persentase: normalizeWeight(payload.bobot_persentase),
      },
    },
  );
}

export function updateInstrumen(
  rancanganId,
  cpmkId,
  subId,
  instrumenId,
  payload,
) {
  const normalized = { ...payload };
  if (normalized.bobot_persentase !== undefined) {
    normalized.bobot_persentase = normalizeWeight(normalized.bobot_persentase);
  }
  return apiRequest(
    `/api/v1/rancangan-penilaian/${rancanganId}/cpmk/${cpmkId}/sub-cpmk/${subId}/instrumen/${instrumenId}`,
    {
      method: 'PATCH',
      body: normalized,
    },
  );
}

export function deleteInstrumen(rancanganId, cpmkId, subId, instrumenId) {
  return apiRequest(
    `/api/v1/rancangan-penilaian/${rancanganId}/cpmk/${cpmkId}/sub-cpmk/${subId}/instrumen/${instrumenId}`,
    {
      method: 'DELETE',
    },
  );
}

// --- Penilaian Bulk Atomik ---
export function saveKelasMkNilai(kelasMkId, items) {
  return apiRequest(`/api/v1/kelas-mk/${kelasMkId}/nilai`, {
    method: 'PUT',
    body: {
      items: items.map((item) => ({
        instrumen_id: item.instrumen_id,
        mahasiswa_id: item.mahasiswa_id,
        nilai_mentah: Number(String(item.nilai_mentah).replace(',', '.')).toFixed(
          2,
        ),
      })),
    },
  });
}

// --- Tahap 6: Ekspor Kelas & Laporan Lintas Kelas ---
export function exportKelasMkReport(kelasMkId, format = 'csv') {
  return apiDownload(`/api/v1/kelas-mk/${kelasMkId}/ekspor`, {
    params: { format },
    fallbackFilename: `laporan-kelas.${format}`,
  });
}

export function getCrossClassReport({ periode_id, kelas_mk_ids } = {}) {
  return apiRequest('/api/v1/laporan/lintas-kelas', {
    params: { periode_id, kelas_mk_ids },
  });
}

export function exportCrossClassReport({
  periode_id,
  kelas_mk_ids,
  format = 'pdf',
} = {}) {
  return apiDownload('/api/v1/laporan/lintas-kelas/ekspor', {
    params: { periode_id, kelas_mk_ids, format },
    fallbackFilename: `laporan-lintas-kelas.${format}`,
  });
}
