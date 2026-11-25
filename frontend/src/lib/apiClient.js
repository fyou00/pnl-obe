const TOKEN_KEY = 'pnl_obe_access_token';
const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '');

let unauthorizedHandler = null;

export class ApiError extends Error {
  constructor(message, status, detail = null) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.detail = detail;
  }
}

export function getToken() {
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

export function setToken(token) {
  try {
    localStorage.setItem(TOKEN_KEY, token);
  } catch {
    // Abaikan jika penyimpanan browser dibatasi.
  }
}

export function clearToken() {
  try {
    localStorage.removeItem(TOKEN_KEY);
  } catch {
    // Abaikan jika penyimpanan browser dibatasi.
  }
}

export function setUnauthorizedHandler(handler) {
  unauthorizedHandler = handler;
}

function buildUrl(path, params) {
  const base = `${API_BASE_URL}${path}`;
  if (!params) {
    return base;
  }
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (Array.isArray(value)) {
      for (const item of value) {
        if (item !== undefined && item !== null && item !== '') {
          search.append(key, String(item));
        }
      }
    } else if (value !== undefined && value !== null && value !== '') {
      search.set(key, String(value));
    }
  }
  const queryString = search.toString();
  return queryString ? `${base}?${queryString}` : base;
}

function parseErrorMessage(payload, status) {
  if (payload && typeof payload === 'object' && 'detail' in payload) {
    const { detail } = payload;
    if (typeof detail === 'string' && detail.trim()) {
      return detail;
    }
    if (Array.isArray(detail) && detail.length > 0) {
      return detail
        .map((item) => {
          if (typeof item === 'string') return item;
          if (item && typeof item.msg === 'string') {
            return item.msg.replace(/^Value error,\s*/i, '');
          }
          return 'Data tidak valid';
        })
        .join('; ');
    }
  }
  if (status === 401) return 'Email atau kata sandi salah, atau sesi telah berakhir.';
  if (status === 403) return 'Anda tidak memiliki hak akses untuk tindakan ini.';
  if (status === 404) return 'Data tidak ditemukan.';
  if (status === 503) return 'Layanan database sedang tidak tersedia.';
  return `Permintaan gagal (${status}).`;
}

function extractFilename(disposition, fallback) {
  if (!disposition) return fallback;
  const utfMatch = disposition.match(/filename\*=UTF-8''([^;]+)/i);
  if (utfMatch?.[1]) {
    try {
      return decodeURIComponent(utfMatch[1].trim());
    } catch {
      return utfMatch[1].trim();
    }
  }
  const plainMatch = disposition.match(/filename="?([^";]+)"?/i);
  if (plainMatch?.[1]) {
    return plainMatch[1].trim();
  }
  return fallback;
}

export async function apiRequest(
  path,
  { method = 'GET', body, formBody, params, skipAuth = false } = {},
) {
  const headers = {};
  const token = skipAuth ? null : getToken();
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  let requestBody;
  if (formBody instanceof URLSearchParams) {
    headers['Content-Type'] = 'application/x-www-form-urlencoded';
    requestBody = formBody.toString();
  } else if (body !== undefined) {
    headers['Content-Type'] = 'application/json';
    requestBody = JSON.stringify(body);
  }

  let response;
  try {
    response = await fetch(buildUrl(path, params), {
      method,
      headers,
      body: requestBody,
    });
  } catch {
    throw new ApiError(
      'Tidak dapat terhubung ke server API. Pastikan backend berjalan.',
      0,
    );
  }

  if (response.status === 204) {
    return null;
  }

  const contentType = response.headers.get('content-type') || '';
  const payload = contentType.includes('application/json')
    ? await response.json().catch(() => null)
    : await response.text().catch(() => null);

  if (!response.ok) {
    if (response.status === 401 && !skipAuth) {
      clearToken();
      if (unauthorizedHandler) {
        unauthorizedHandler();
      }
    }
    throw new ApiError(
      parseErrorMessage(payload, response.status),
      response.status,
      payload,
    );
  }

  return payload;
}

export async function apiDownload(
  path,
  { params, fallbackFilename = 'laporan' } = {},
) {
  const headers = {};
  const token = getToken();
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  let response;
  try {
    response = await fetch(buildUrl(path, params), {
      method: 'GET',
      headers,
    });
  } catch {
    throw new ApiError(
      'Tidak dapat terhubung ke server API. Pastikan backend berjalan.',
      0,
    );
  }

  if (!response.ok) {
    const contentType = response.headers.get('content-type') || '';
    const payload = contentType.includes('application/json')
      ? await response.json().catch(() => null)
      : await response.text().catch(() => null);
    if (response.status === 401) {
      clearToken();
      if (unauthorizedHandler) {
        unauthorizedHandler();
      }
    }
    throw new ApiError(
      parseErrorMessage(payload, response.status),
      response.status,
      payload,
    );
  }

  const blob = await response.blob();
  const filename = extractFilename(
    response.headers.get('content-disposition'),
    fallbackFilename,
  );
  const objectUrl = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = objectUrl;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  setTimeout(() => URL.revokeObjectURL(objectUrl), 1000);
  return { filename };
}
