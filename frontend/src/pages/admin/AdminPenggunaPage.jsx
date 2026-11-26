import { useCallback, useEffect, useMemo, useState } from 'react';
import { LoadingSkeleton } from '../../components/states/SystemStates.jsx';
import { useAuth } from '../../context/AuthContext.jsx';
import {
  createPengguna,
  listAngkatan,
  listPengguna,
  resetPenggunaPassword,
  updatePengguna,
} from '../../lib/adminApi.js';

const ROLE_FILTER_OPTIONS = [
  { value: '', label: 'Semua' },
  { value: 'Dosen', label: 'Dosen' },
  { value: 'Mahasiswa', label: 'Mahasiswa' },
  { value: 'Admin', label: 'Admin' },
];

function utf8ByteLength(value) {
  return new TextEncoder().encode(value).length;
}

function RoleBadge({ role }) {
  if (role === 'Admin') {
    return (
      <span className="inline-flex items-center h-6 px-2.5 rounded-full bg-[#15333A] text-white text-[11.5px] font-semibold">
        Admin
      </span>
    );
  }
  if (role === 'Dosen') {
    return (
      <span className="inline-flex items-center h-6 px-2.5 rounded-full bg-[#E6F0EE] border border-[#D4E3E0] text-[#15333A] text-[11.5px] font-semibold">
        Dosen
      </span>
    );
  }
  return (
    <span className="inline-flex items-center h-6 px-2.5 rounded-full bg-[#FAF8F3] border border-[#E4DFD4] text-[#334B51] text-[11.5px] font-semibold">
      Mahasiswa
    </span>
  );
}

export default function AdminPenggunaPage() {
  const { user: currentAdmin } = useAuth();

  const [allUsers, setAllUsers] = useState([]);
  const [users, setUsers] = useState([]);
  const [cohorts, setCohorts] = useState([]);

  const [roleFilter, setRoleFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [searchQuery, setSearchQuery] = useState('');

  const [loading, setLoading] = useState(true);
  const [busyKey, setBusyKey] = useState('');
  const [error, setError] = useState('');
  const [feedback, setFeedback] = useState('');

  const [createForm, setCreateForm] = useState({
    role: 'Dosen',
    nim_nidn: '',
    nama: '',
    email: '',
    password: '',
    angkatan_id: '',
  });
  const [showCreatePassword, setShowCreatePassword] = useState(false);

  const [editingUser, setEditingUser] = useState(null);
  const [editForm, setEditForm] = useState({
    nim_nidn: '',
    nama: '',
    email: '',
    angkatan_id: '',
  });

  const [resetTarget, setResetTarget] = useState(null);
  const [resetForm, setResetForm] = useState({
    password_baru: '',
    alasan: '',
  });
  const [showResetPassword, setShowResetPassword] = useState(false);

  const loadMetadata = useCallback(async () => {
    try {
      const [allData, cohortData] = await Promise.all([
        listPengguna({ limit: 100 }),
        listAngkatan({ limit: 100 }),
      ]);
      setAllUsers(allData);
      setCohorts(cohortData);
    } catch (err) {
      setError(err.message || 'Gagal memuat daftar pengguna prodi.');
    }
  }, []);

  const loadFilteredUsers = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const data = await listPengguna({
        limit: 100,
        role: roleFilter || undefined,
        aktif:
          statusFilter === 'aktif'
            ? true
            : statusFilter === 'nonaktif'
              ? false
              : undefined,
        q: searchQuery.trim() || undefined,
      });
      setUsers(data);
    } catch (err) {
      setError(err.message || 'Gagal memuat daftar pengguna.');
    } finally {
      setLoading(false);
    }
  }, [roleFilter, searchQuery, statusFilter]);

  useEffect(() => {
    loadMetadata();
  }, [loadMetadata]);

  useEffect(() => {
    loadFilteredUsers();
  }, [loadFilteredUsers]);

  const stats = useMemo(() => {
    let dosenCount = 0;
    let mahasiswaCount = 0;
    let inactiveCount = 0;
    for (const item of allUsers) {
      if (item.role === 'Dosen') dosenCount += 1;
      if (item.role === 'Mahasiswa') mahasiswaCount += 1;
      if (!item.aktif) inactiveCount += 1;
    }
    return {
      total: allUsers.length,
      dosenCount,
      mahasiswaCount,
      inactiveCount,
    };
  }, [allUsers]);

  const handleCreate = async (e) => {
    e.preventDefault();
    setError('');
    setFeedback('');

    const pwBytes = utf8ByteLength(createForm.password);
    if (pwBytes < 12 || pwBytes > 72) {
      setError('Kata sandi awal harus terdiri dari 12–72 byte UTF-8.');
      return;
    }

    setBusyKey('create');
    try {
      const payload = {
        role: createForm.role,
        nim_nidn: createForm.nim_nidn.trim(),
        nama: createForm.nama.trim(),
        email: createForm.email.trim(),
        password: createForm.password,
        aktif: true,
        ...(createForm.role === 'Mahasiswa' && createForm.angkatan_id
          ? { angkatan_id: createForm.angkatan_id }
          : {}),
      };
      const created = await createPengguna(payload);
      setCreateForm({
        role: createForm.role,
        nim_nidn: '',
        nama: '',
        email: '',
        password: '',
        angkatan_id: '',
      });
      setShowCreatePassword(false);
      setFeedback(`Akun ${created.role} (${created.email}) berhasil dibuat.`);
      await Promise.all([loadMetadata(), loadFilteredUsers()]);
    } catch (err) {
      setError(err.message || 'Gagal membuat akun pengguna baru.');
    } finally {
      setBusyKey('');
    }
  };

  const openEdit = (target) => {
    setError('');
    setFeedback('');
    setEditingUser(target);
    setEditForm({
      nim_nidn: target.nim_nidn,
      nama: target.nama,
      email: target.email,
      angkatan_id: '',
    });
  };

  const handleUpdate = async (e) => {
    e.preventDefault();
    if (!editingUser) return;
    setError('');
    setFeedback('');
    setBusyKey(`edit-${editingUser.id}`);
    try {
      const payload = {
        nim_nidn: editForm.nim_nidn.trim(),
        nama: editForm.nama.trim(),
        email: editForm.email.trim(),
      };
      if (
        editingUser.role === 'Mahasiswa' &&
        !editingUser.angkatan_id &&
        editForm.angkatan_id
      ) {
        payload.angkatan_id = editForm.angkatan_id;
      }
      const updated = await updatePengguna(editingUser.id, payload);
      setEditingUser(null);
      setFeedback(`Data pengguna ${updated.nama} berhasil diperbarui.`);
      await Promise.all([loadMetadata(), loadFilteredUsers()]);
    } catch (err) {
      setError(err.message || 'Gagal memperbarui data pengguna.');
    } finally {
      setBusyKey('');
    }
  };

  const handleToggleActive = async (target) => {
    setError('');
    setFeedback('');
    setBusyKey(`toggle-${target.id}`);
    try {
      const updated = await updatePengguna(target.id, { aktif: !target.aktif });
      setFeedback(
        updated.aktif
          ? `Akun ${updated.nama} diaktifkan kembali.`
          : `Akun ${updated.nama} dinonaktifkan dan sesi aktifnya dicabut.`,
      );
      await Promise.all([loadMetadata(), loadFilteredUsers()]);
    } catch (err) {
      setError(err.message || 'Gagal mengubah status aktif pengguna.');
    } finally {
      setBusyKey('');
    }
  };

  const openResetModal = (target) => {
    setError('');
    setFeedback('');
    setResetTarget(target);
    setResetForm({ password_baru: '', alasan: '' });
    setShowResetPassword(false);
  };

  const handleResetPassword = async (e) => {
    e.preventDefault();
    if (!resetTarget) return;
    setError('');
    setFeedback('');

    const pwBytes = utf8ByteLength(resetForm.password_baru);
    if (pwBytes < 12 || pwBytes > 72) {
      setError('Kata sandi baru harus terdiri dari 12–72 byte UTF-8.');
      return;
    }

    setBusyKey(`reset-${resetTarget.id}`);
    try {
      await resetPenggunaPassword(resetTarget.id, {
        password_baru: resetForm.password_baru,
        alasan: resetForm.alasan.trim() || null,
      });
      const targetName = resetTarget.nama;
      setResetTarget(null);
      setResetForm({ password_baru: '', alasan: '' });
      setFeedback(
        `Kata sandi ${targetName} berhasil direset dan seluruh sesi lamanya dicabut.`,
      );
      await Promise.all([loadMetadata(), loadFilteredUsers()]);
    } catch (err) {
      setError(err.message || 'Gagal mereset kata sandi pengguna.');
    } finally {
      setBusyKey('');
    }
  };

  return (
    <div className="max-w-[1136px] flex flex-col gap-6">
      <div>
        <h1 className="text-[28px] font-semibold leading-[34px] text-[#15333A]">
          Manajemen Pengguna
        </h1>
        <p className="text-[14px] text-[#566B70] mt-2">
          Kelola akun Dosen dan Mahasiswa pada program studi Anda: pembuatan
          akun, pembaruan profil, penonaktifan akses, dan reset kata sandi.
        </p>
      </div>

      {error && (
        <div
          role="alert"
          className="rounded-[10px] bg-[#FEF3F2] border border-[#FECDCA] px-4 py-3 text-[13px] text-[#B42318]"
        >
          {error}
        </div>
      )}

      {feedback && (
        <div
          role="status"
          className="rounded-[10px] bg-[#E6F2EE] border border-[#C6DFD7] px-4 py-3 text-[13px] text-[#1A5C4D]"
        >
          {feedback}
        </div>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        <div className="min-h-[110px] p-5 rounded-[12px] bg-white border border-[#E4DFD4] flex flex-col justify-between">
          <span className="text-[12.5px] font-medium text-[#566B70]">
            Total Pengguna
          </span>
          <span className="text-[28px] font-semibold text-[#15333A] tabular-nums">
            {stats.total}
          </span>
          <span className="text-[11px] text-[#7A8C90]">
            Terdaftar pada program studi
          </span>
        </div>

        <div className="min-h-[110px] p-5 rounded-[12px] bg-white border border-[#E4DFD4] flex flex-col justify-between">
          <span className="text-[12.5px] font-medium text-[#566B70]">
            Dosen
          </span>
          <span className="text-[28px] font-semibold text-[#15333A] tabular-nums">
            {stats.dosenCount}
          </span>
          <span className="text-[11px] text-[#7A8C90]">
            Pengampu mata kuliah
          </span>
        </div>

        <div className="min-h-[110px] p-5 rounded-[12px] bg-white border border-[#E4DFD4] flex flex-col justify-between">
          <span className="text-[12.5px] font-medium text-[#566B70]">
            Mahasiswa
          </span>
          <span className="text-[28px] font-semibold text-[#15333A] tabular-nums">
            {stats.mahasiswaCount}
          </span>
          <span className="text-[11px] text-[#7A8C90]">
            Peserta pembelajaran OBE
          </span>
        </div>

        <div className="min-h-[110px] p-5 rounded-[12px] bg-white border border-[#E4DFD4] flex flex-col justify-between">
          <span className="text-[12.5px] font-medium text-[#566B70]">
            Akun Nonaktif
          </span>
          <span className="text-[28px] font-semibold text-[#B55824] tabular-nums">
            {stats.inactiveCount}
          </span>
          <span className="text-[11px] text-[#7A8C90]">
            Akses login dibekukan
          </span>
        </div>
      </div>

      <section className="bg-white border border-[#E4DFD4] rounded-[12px] p-6">
        <h2 className="text-[17px] font-semibold text-[#15333A]">
          Tambah Akun Pengguna
        </h2>
        <form onSubmit={handleCreate} className="mt-4 flex flex-col gap-4">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="flex flex-col gap-1.5">
              <label
                htmlFor="user-create-role"
                className="text-[12px] font-medium text-[#334B51]"
              >
                Peran
              </label>
              <select
                id="user-create-role"
                value={createForm.role}
                onChange={(e) =>
                  setCreateForm((prev) => ({
                    ...prev,
                    role: e.target.value,
                    angkatan_id:
                      e.target.value === 'Mahasiswa' ? prev.angkatan_id : '',
                  }))
                }
                className="h-[38px] px-3 rounded-[7px] bg-[#FAF8F3] border border-[#E4DFD4] text-[13px]"
              >
                <option value="Dosen">Dosen</option>
                <option value="Mahasiswa">Mahasiswa</option>
              </select>
            </div>

            <div className="flex flex-col gap-1.5">
              <label
                htmlFor="user-create-nim"
                className="text-[12px] font-medium text-[#334B51]"
              >
                NIM / NIDN
              </label>
              <input
                id="user-create-nim"
                type="text"
                required
                maxLength={20}
                value={createForm.nim_nidn}
                onChange={(e) =>
                  setCreateForm((prev) => ({
                    ...prev,
                    nim_nidn: e.target.value,
                  }))
                }
                placeholder="198901012018011001"
                className="h-[38px] px-3 rounded-[7px] bg-[#FAF8F3] border border-[#E4DFD4] text-[13px]"
              />
            </div>

            <div className="flex flex-col gap-1.5">
              <label
                htmlFor="user-create-nama"
                className="text-[12px] font-medium text-[#334B51]"
              >
                Nama Lengkap
              </label>
              <input
                id="user-create-nama"
                type="text"
                required
                maxLength={100}
                value={createForm.nama}
                onChange={(e) =>
                  setCreateForm((prev) => ({ ...prev, nama: e.target.value }))
                }
                placeholder="Nama lengkap & gelar"
                className="h-[38px] px-3 rounded-[7px] bg-[#FAF8F3] border border-[#E4DFD4] text-[13px]"
              />
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 items-end">
            <div className="flex flex-col gap-1.5">
              <label
                htmlFor="user-create-email"
                className="text-[12px] font-medium text-[#334B51]"
              >
                Email Institusi
              </label>
              <input
                id="user-create-email"
                type="email"
                required
                maxLength={100}
                value={createForm.email}
                onChange={(e) =>
                  setCreateForm((prev) => ({ ...prev, email: e.target.value }))
                }
                placeholder="nama@pnl.ac.id"
                className="h-[38px] px-3 rounded-[7px] bg-[#FAF8F3] border border-[#E4DFD4] text-[13px]"
              />
            </div>

            <div className="flex flex-col gap-1.5">
              <label
                htmlFor="user-create-password"
                className="text-[12px] font-medium text-[#334B51]"
              >
                Kata Sandi Awal (min. 12 karakter)
              </label>
              <div className="flex items-center gap-2">
                <input
                  id="user-create-password"
                  type={showCreatePassword ? 'text' : 'password'}
                  required
                  value={createForm.password}
                  onChange={(e) =>
                    setCreateForm((prev) => ({
                      ...prev,
                      password: e.target.value,
                    }))
                  }
                  placeholder="Minimal 12 karakter"
                  className="flex-1 min-w-0 h-[38px] px-3 rounded-[7px] bg-[#FAF8F3] border border-[#E4DFD4] text-[13px]"
                />
                <button
                  type="button"
                  onClick={() => setShowCreatePassword((v) => !v)}
                  className="h-[38px] px-2.5 rounded-[7px] border border-[#E4DFD4] text-[11.5px] font-medium text-[#566B70] hover:text-[#15333A] cursor-pointer shrink-0"
                >
                  {showCreatePassword ? 'Tutup' : 'Lihat'}
                </button>
              </div>
            </div>

            {createForm.role === 'Mahasiswa' ? (
              <div className="flex flex-col gap-1.5">
                <label
                  htmlFor="user-create-angkatan"
                  className="text-[12px] font-medium text-[#334B51]"
                >
                  Angkatan (Opsional)
                </label>
                <select
                  id="user-create-angkatan"
                  value={createForm.angkatan_id}
                  onChange={(e) =>
                    setCreateForm((prev) => ({
                      ...prev,
                      angkatan_id: e.target.value,
                    }))
                  }
                  className="h-[38px] px-3 rounded-[7px] bg-[#FAF8F3] border border-[#E4DFD4] text-[13px]"
                >
                  <option value="">— Belum ditetapkan —</option>
                  {cohorts.map((cohort) => (
                    <option key={cohort.id} value={cohort.id}>
                      Angkatan {cohort.tahun_masuk}
                    </option>
                  ))}
                </select>
              </div>
            ) : (
              <div className="hidden md:block" />
            )}
          </div>

          <div className="flex justify-end">
            <button
              type="submit"
              disabled={busyKey === 'create'}
              className="h-[38px] px-4 rounded-[8px] bg-[#15333A] hover:bg-[#193A40] text-white transition-colors text-[12.5px] font-semibold cursor-pointer disabled:opacity-60"
            >
              {busyKey === 'create' ? 'Menyimpan...' : '+ Buat Akun'}
            </button>
          </div>
        </form>
      </section>

      <section className="bg-white border border-[#E4DFD4] rounded-[12px] p-6 flex flex-col gap-4">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex flex-wrap items-center gap-2">
            {ROLE_FILTER_OPTIONS.map((opt) => (
              <button
                key={opt.value || 'all'}
                type="button"
                onClick={() => setRoleFilter(opt.value)}
                className={[
                  'h-[34px] px-3.5 rounded-[8px] text-[12.5px] font-semibold cursor-pointer transition-colors',
                  roleFilter === opt.value
                    ? 'bg-[#15333A] text-white'
                    : 'border border-[#E4DFD4] bg-white text-[#566B70] hover:text-[#15333A]',
                ].join(' ')}
              >
                {opt.label}
              </button>
            ))}
          </div>

          <div className="flex flex-wrap items-center gap-2.5">
            <select
              aria-label="Filter status akun"
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="h-[36px] px-3 rounded-[7px] bg-[#FAF8F3] border border-[#E4DFD4] text-[12.5px]"
            >
              <option value="">Semua status</option>
              <option value="aktif">Aktif</option>
              <option value="nonaktif">Nonaktif</option>
            </select>

            <input
              type="search"
              aria-label="Cari pengguna"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Cari nama, email, atau NIM/NIDN..."
              className="h-[36px] w-[250px] px-3 rounded-[7px] bg-[#FAF8F3] border border-[#E4DFD4] text-[12.5px]"
            />
          </div>
        </div>

        {loading ? (
          <LoadingSkeleton variant="table" />
        ) : users.length === 0 ? (
          <p className="py-6 text-[13px] text-[#566B70]">
            Tidak ada pengguna yang sesuai dengan filter saat ini.
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-[#E4DFD4] text-[11.5px] font-semibold text-[#566B70]">
                  <th className="py-3 pr-4">Pengguna</th>
                  <th className="py-3 pr-4 whitespace-nowrap">NIM / NIDN</th>
                  <th className="py-3 pr-4">Peran</th>
                  <th className="py-3 pr-4">Angkatan</th>
                  <th className="py-3 pr-4">Status</th>
                  <th className="py-3 text-right">Aksi</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#EFECE4] text-[13px]">
                {users.map((item) => {
                  const isSelf = item.id === currentAdmin?.id;
                  const isAdminAccount = item.role === 'Admin';
                  const rowBusy =
                    busyKey === `toggle-${item.id}` ||
                    busyKey === `edit-${item.id}` ||
                    busyKey === `reset-${item.id}`;

                  return (
                    <tr key={item.id} className="hover:bg-[#FAF8F3]/70">
                      <td className="py-3 pr-4">
                        <div className="font-semibold text-[#15333A]">
                          {item.nama}
                        </div>
                        <div className="text-[12px] text-[#566B70]">
                          {item.email}
                        </div>
                      </td>
                      <td className="py-3 pr-4 font-mono text-[12px] text-[#334B51] whitespace-nowrap">
                        {item.nim_nidn}
                      </td>
                      <td className="py-3 pr-4 whitespace-nowrap">
                        <RoleBadge role={item.role} />
                      </td>
                      <td className="py-3 pr-4 text-[#334B51] whitespace-nowrap">
                        {item.role === 'Mahasiswa'
                          ? item.tahun_masuk
                            ? `Angkatan ${item.tahun_masuk}`
                            : 'Belum ditetapkan'
                          : '—'}
                      </td>
                      <td className="py-3 pr-4 whitespace-nowrap">
                        <span
                          className={[
                            'inline-flex items-center h-6 px-2.5 rounded-full text-[11.5px] font-semibold',
                            item.aktif
                              ? 'bg-[#E6F2EE] border border-[#C6DFD7] text-[#1A5C4D]'
                              : 'bg-[#F7EAE1] border border-[#E8B899] text-[#B55824]',
                          ].join(' ')}
                        >
                          {item.aktif ? 'Aktif' : 'Nonaktif'}
                        </span>
                      </td>
                      <td className="py-3 text-right whitespace-nowrap">
                        {isAdminAccount ? (
                          <span className="inline-flex items-center h-7 px-2.5 rounded-[7px] bg-[#FAF8F3] border border-[#E4DFD4] text-[11.5px] font-medium text-[#566B70]">
                            {isSelf ? 'Akun Anda' : 'Terlindungi'}
                          </span>
                        ) : (
                          <div className="inline-flex items-center gap-2">
                            <button
                              type="button"
                              disabled={rowBusy}
                              onClick={() => openEdit(item)}
                              className="h-[30px] px-2.5 rounded-[7px] border border-[#E4DFD4] text-[12px] font-medium text-[#15333A] hover:bg-[#FAF8F3] cursor-pointer disabled:opacity-50"
                            >
                              Ubah
                            </button>
                            <button
                              type="button"
                              disabled={rowBusy}
                              onClick={() => openResetModal(item)}
                              className="h-[30px] px-2.5 rounded-[7px] border border-[#E4DFD4] text-[12px] font-medium text-[#15333A] hover:bg-[#FAF8F3] cursor-pointer disabled:opacity-50"
                            >
                              Reset Sandi
                            </button>
                            <button
                              type="button"
                              disabled={rowBusy}
                              onClick={() => handleToggleActive(item)}
                              className={[
                                'h-[30px] px-2.5 rounded-[7px] border text-[12px] font-medium cursor-pointer disabled:opacity-50',
                                item.aktif
                                  ? 'border-[#E4DFD4] text-[#B55824] hover:bg-[#F7EAE1]'
                                  : 'border-[#C6DFD7] text-[#1A5C4D] hover:bg-[#E6F2EE]',
                              ].join(' ')}
                            >
                              {item.aktif ? 'Nonaktifkan' : 'Aktifkan'}
                            </button>
                          </div>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {editingUser && (
        <div
          className="fixed inset-0 z-50 bg-[#15333A]/40 flex items-center justify-center p-4"
          onClick={() => setEditingUser(null)}
        >
          <div
            role="dialog"
            aria-modal="true"
            aria-labelledby="edit-user-title"
            onClick={(e) => e.stopPropagation()}
            className="w-full max-w-[480px] bg-white border border-[#E4DFD4] rounded-[14px] p-6 shadow-[0_16px_40px_rgba(21,51,58,0.14)] flex flex-col gap-4"
          >
            <h2
              id="edit-user-title"
              className="text-[19px] font-semibold text-[#15333A]"
            >
              Ubah Pengguna · {editingUser.role}
            </h2>

            <form onSubmit={handleUpdate} className="flex flex-col gap-3.5">
              <div className="flex flex-col gap-1.5">
                <label
                  htmlFor="edit-user-nim"
                  className="text-[12px] font-medium text-[#334B51]"
                >
                  NIM / NIDN
                </label>
                <input
                  id="edit-user-nim"
                  type="text"
                  required
                  maxLength={20}
                  value={editForm.nim_nidn}
                  onChange={(e) =>
                    setEditForm((prev) => ({
                      ...prev,
                      nim_nidn: e.target.value,
                    }))
                  }
                  className="h-[38px] px-3 rounded-[7px] bg-[#FAF8F3] border border-[#E4DFD4] text-[13px]"
                />
              </div>

              <div className="flex flex-col gap-1.5">
                <label
                  htmlFor="edit-user-nama"
                  className="text-[12px] font-medium text-[#334B51]"
                >
                  Nama Lengkap
                </label>
                <input
                  id="edit-user-nama"
                  type="text"
                  required
                  maxLength={100}
                  value={editForm.nama}
                  onChange={(e) =>
                    setEditForm((prev) => ({ ...prev, nama: e.target.value }))
                  }
                  className="h-[38px] px-3 rounded-[7px] bg-[#FAF8F3] border border-[#E4DFD4] text-[13px]"
                />
              </div>

              <div className="flex flex-col gap-1.5">
                <label
                  htmlFor="edit-user-email"
                  className="text-[12px] font-medium text-[#334B51]"
                >
                  Email Institusi
                </label>
                <input
                  id="edit-user-email"
                  type="email"
                  required
                  maxLength={100}
                  value={editForm.email}
                  onChange={(e) =>
                    setEditForm((prev) => ({ ...prev, email: e.target.value }))
                  }
                  className="h-[38px] px-3 rounded-[7px] bg-[#FAF8F3] border border-[#E4DFD4] text-[13px]"
                />
              </div>

              {editingUser.role === 'Mahasiswa' && (
                <div className="flex flex-col gap-1.5">
                  <label
                    htmlFor="edit-user-angkatan"
                    className="text-[12px] font-medium text-[#334B51]"
                  >
                    Angkatan
                  </label>
                  {editingUser.angkatan_id ? (
                    <input
                      id="edit-user-angkatan"
                      type="text"
                      disabled
                      value={`Angkatan ${editingUser.tahun_masuk} (terkunci)`}
                      className="h-[38px] px-3 rounded-[7px] bg-[#EFECE4] border border-[#E4DFD4] text-[13px] text-[#566B70]"
                    />
                  ) : (
                    <select
                      id="edit-user-angkatan"
                      value={editForm.angkatan_id}
                      onChange={(e) =>
                        setEditForm((prev) => ({
                          ...prev,
                          angkatan_id: e.target.value,
                        }))
                      }
                      className="h-[38px] px-3 rounded-[7px] bg-[#FAF8F3] border border-[#E4DFD4] text-[13px]"
                    >
                      <option value="">— Belum ditetapkan —</option>
                      {cohorts.map((cohort) => (
                        <option key={cohort.id} value={cohort.id}>
                          Angkatan {cohort.tahun_masuk}
                        </option>
                      ))}
                    </select>
                  )}
                </div>
              )}

              <div className="flex justify-end gap-2.5 pt-2">
                <button
                  type="button"
                  onClick={() => setEditingUser(null)}
                  className="h-[36px] px-3.5 rounded-[8px] border border-[#E4DFD4] text-[12.5px] font-medium cursor-pointer"
                >
                  Batal
                </button>
                <button
                  type="submit"
                  disabled={busyKey === `edit-${editingUser.id}`}
                  className="h-[36px] px-4 rounded-[8px] bg-[#15333A] hover:bg-[#193A40] text-white text-[12.5px] font-semibold cursor-pointer disabled:opacity-60"
                >
                  {busyKey === `edit-${editingUser.id}`
                    ? 'Menyimpan...'
                    : 'Simpan Perubahan'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {resetTarget && (
        <div
          className="fixed inset-0 z-50 bg-[#15333A]/40 flex items-center justify-center p-4"
          onClick={() => setResetTarget(null)}
        >
          <div
            role="dialog"
            aria-modal="true"
            aria-labelledby="reset-pw-title"
            onClick={(e) => e.stopPropagation()}
            className="w-full max-w-[460px] bg-white border border-[#E4DFD4] rounded-[14px] p-6 shadow-[0_16px_40px_rgba(21,51,58,0.14)] flex flex-col gap-4"
          >
            <div>
              <h2
                id="reset-pw-title"
                className="text-[19px] font-semibold text-[#15333A]"
              >
                Reset Kata Sandi
              </h2>
              <p className="text-[13px] text-[#566B70] mt-1">
                Target: <strong className="text-[#15333A]">{resetTarget.nama}</strong>{' '}
                ({resetTarget.email}). Seluruh sesi aktif pengguna ini akan
                dicabut.
              </p>
            </div>

            <form
              onSubmit={handleResetPassword}
              className="flex flex-col gap-3.5"
            >
              <div className="flex flex-col gap-1.5">
                <label
                  htmlFor="reset-pw-input"
                  className="text-[12px] font-medium text-[#334B51]"
                >
                  Kata sandi baru (minimal 12 karakter)
                </label>
                <input
                  id="reset-pw-input"
                  type={showResetPassword ? 'text' : 'password'}
                  required
                  value={resetForm.password_baru}
                  onChange={(e) =>
                    setResetForm((prev) => ({
                      ...prev,
                      password_baru: e.target.value,
                    }))
                  }
                  placeholder="Minimal 12 karakter"
                  className="h-[38px] px-3 rounded-[7px] bg-[#FAF8F3] border border-[#E4DFD4] text-[13px]"
                />
              </div>

              <div className="flex flex-col gap-1.5">
                <label
                  htmlFor="reset-pw-alasan"
                  className="text-[12px] font-medium text-[#334B51]"
                >
                  Alasan reset (opsional, tercatat di audit log)
                </label>
                <input
                  id="reset-pw-alasan"
                  type="text"
                  maxLength={500}
                  value={resetForm.alasan}
                  onChange={(e) =>
                    setResetForm((prev) => ({
                      ...prev,
                      alasan: e.target.value,
                    }))
                  }
                  placeholder="Misalnya: Pengguna lupa kata sandi"
                  className="h-[38px] px-3 rounded-[7px] bg-[#FAF8F3] border border-[#E4DFD4] text-[13px]"
                />
              </div>

              <label className="inline-flex items-center gap-2 text-[12.5px] text-[#566B70] cursor-pointer w-fit">
                <input
                  type="checkbox"
                  checked={showResetPassword}
                  onChange={(e) => setShowResetPassword(e.target.checked)}
                  className="accent-[#15333A]"
                />
                <span>Tampilkan kata sandi</span>
              </label>

              <div className="flex justify-end gap-2.5 pt-2">
                <button
                  type="button"
                  onClick={() => setResetTarget(null)}
                  className="h-[36px] px-3.5 rounded-[8px] border border-[#E4DFD4] text-[12.5px] font-medium cursor-pointer"
                >
                  Batal
                </button>
                <button
                  type="submit"
                  disabled={busyKey === `reset-${resetTarget.id}`}
                  className="h-[36px] px-4 rounded-[8px] bg-[#15333A] hover:bg-[#193A40] text-white text-[12.5px] font-semibold cursor-pointer disabled:opacity-60"
                >
                  {busyKey === `reset-${resetTarget.id}`
                    ? 'Memproses...'
                    : 'Simpan Reset Sandi'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
