import { apiDownload, apiRequest } from './apiClient.js';

export function listMahasiswaPeriode() {
  return apiRequest('/api/v1/mahasiswa/periode');
}

export function listMahasiswaKelasMk(periodeId, { offset = 0, limit = 100 } = {}) {
  return apiRequest('/api/v1/kelas-mk', {
    params: { periode_id: periodeId, offset, limit },
  });
}

export function getMahasiswaCapaianSaya(periodeId, { kumulatif = false } = {}) {
  return apiRequest('/api/v1/capaian/saya', {
    params: { periode_id: periodeId, kumulatif },
  });
}

export function getMahasiswaKelasRincian(kelasMkId) {
  return apiRequest(`/api/v1/mahasiswa/kelas-mk/${kelasMkId}/rincian`);
}

export function exportMahasiswaCapaianSaya(
  periodeId,
  { kumulatif = false, format = 'pdf' } = {},
) {
  return apiDownload('/api/v1/capaian/saya/ekspor', {
    params: { periode_id: periodeId, kumulatif, format },
    fallbackFilename: `capaian-pribadi.${format}`,
  });
}
