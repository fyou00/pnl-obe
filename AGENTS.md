# AGENTS.md - Panduan Konteks & Aturan Pengembangan Sistem OBE PNL

Dokumen ini adalah *single source of truth* dan panduan wajib bagi *AI Coding Agent* (Cline/Cursor/dll) sebelum menulis, mengubah, atau menghapus kode di repositori ini.

## 1. Gambaran Proyek & Tech Stack
* **Nama Proyek:** Aplikasi Pengukuran Capaian Pembelajaran (CPMK OBE) - Politeknik Negeri Lhokseumawe (PNL).
* **Frontend:** React.js (Vite/Next.js), TailwindCSS, Recharts/Chart.js (untuk Radar Chart).
* **Backend:** Python 3.11+, FastAPI, SQLAlchemy (ORM), Pydantic v2, Alembic (Migrations).
* **Database:** PostgreSQL 15+.
* **Auth & Security:** JWT (*JSON Web Token*), Bcrypt password hashing, RBAC (*Role-Based Access Control*).
* **Dokumen terkait:** `docs/DESIGN.md` (requirements, alur bisnis, blueprint UI/UX), `SCHEMA.md` (skema fisik & rumus kalkulasi OBE), `PLAN.md` (peta jalan & progres).

## 2. Aturan Bisnis & Hak Akses (RBAC)
Setiap pembuatan *endpoint* API maupun *route* halaman wajib mematuhi hierarki peran berikut:
1. **`Admin` (Kaprodi):** Akses penuh pada Master Data (`prodi`, `master_cpl`, `mata_kuliah`, `users`), pemetaan matriks `mk_cpl`, dan penetapan `pengampu_krs`. Tidak menginput nilai harian mahasiswa.
2. **`Dosen`:** Hanya bisa mengakses dan mengelola `cpmk`, `sub_cpmk`, `instrumen_penilaian`, dan `nilai_mahasiswa` untuk Mata Kuliah yang terikat padanya di tabel `pengampu_krs`. Dilarang mengubah `master_cpl`.
3. **`Mahasiswa`:** Akses murni *Read-Only*. Hanya dapat melihat nilai dan grafik capaian miliknya sendiri pada Mata Kuliah yang diambil di `pengampu_krs`.

## 3. Skema Database & Relasi (PostgreSQL)
Gunakan **UUID** sebagai Primary Key untuk seluruh entitas utama. Jangan mengubah aturan integritas relasi berikut:

* **`users`**: `id` (PK), `nim_nidn` (Unique), `nama`, `email` (Unique), `role` (`Admin` | `Dosen` | `Mahasiswa`), `password_hash`.
* **`prodi`**: `id` (PK), `nama_prodi`, `jenjang`.
* **`master_cpl`**: `id` (PK), `prodi_id` (FK $\rightarrow$ `prodi.id`, Nullable untuk CPL Nasional S/KU), `kode_cpl`, `kategori` (`S` | `KU` | `P` | `KK`), `deskripsi`.
* **`mata_kuliah`**: `id` (PK), `prodi_id` (FK $\rightarrow$ `prodi.id`), `kode_mk`, `nama_mk`, `sks`, `semester`, `deskripsi`.
* **`mk_cpl`** *(Junction M:N)*: `mk_id` (PK, FK $\rightarrow$ `mata_kuliah.id`), `cpl_id` (PK, FK $\rightarrow$ `master_cpl.id`), `urutan_rps`.
* **`pengampu_krs`** *(Junction M:N)*: `user_id` (PK, FK $\rightarrow$ `users.id`), `mk_id` (PK, FK $\rightarrow$ `mata_kuliah.id`), `status` (`Dosen Pengampu` | `Mahasiswa Mengambil`).
* **`cpmk`**: `id` (PK), `mk_id` (FK $\rightarrow$ `mata_kuliah.id`, `ON DELETE CASCADE`), `kode_cpmk`, `deskripsi`.
* **`sub_cpmk`**: `id` (PK), `cpmk_id` (FK $\rightarrow$ `cpmk.id`, `ON DELETE CASCADE`), `kode_sub`, `deskripsi`.
* **`instrumen_penilaian`**: `id` (PK), `sub_cpmk_id` (FK $\rightarrow$ `sub_cpmk.id`, `ON DELETE CASCADE`), `jenis_instrumen` (Tugas, Kuis, UTS, UAS), `bobot_persentase` (`NUMERIC(5,2)`).
* **`nilai_mahasiswa`**: `id` (PK), `instrumen_id` (FK $\rightarrow$ `instrumen_penilaian.id`), `mahasiswa_id` (FK $\rightarrow$ `users.id`), `nilai_mentah` (`NUMERIC(5,2)`, rentang $0\text{--}100$), `waktu_input`.

## 4. Logika Kalkulasi OBE (Core Business Logic)
* Penilaian bersifat *bottom-up*: Nilai diinput pada `instrumen_penilaian` $\rightarrow$ diagregasi ke `sub_cpmk` $\rightarrow$ diagregasi ke `cpmk` $\rightarrow$ dipetakan ke `master_cpl`.
* Seluruh perhitungan agregat persentase capaian harus dilakukan di **Backend Service Layer (FastAPI)** menggunakan tipe data presisi (`Decimal`/`float` terbulat 2 desimal), bukan dihitung di *client/frontend*.

## 5. Konvensi Penulisan Kode (Coding Standards)
* **Backend (Python/FastAPI):**
  * Gunakan `snake_case` untuk nama file, fungsi, variabel, dan kolom database.
  * Pisahkan logika ke dalam lapisan: `models/` (SQLAlchemy), `schemas/` (Pydantic), `crud/` atau `services/` (Business Logic), dan `api/v1/endpoints/` (Routes).
  * Gunakan *dependency injection* (`Depends`) untuk validasi token JWT dan pengecekan `role`.
* **Frontend (React.js):**
  * Gunakan `PascalCase` untuk nama komponen (misal: `RadarCapaianChart.jsx`, `MatriksPembebananTable.jsx`) dan `camelCase` untuk variabel/fungsi.
  * Jaga konsistensi palet warna sesuai desain Figma (gunakan variabel warna Tailwind yang sudah dikonfigurasi).

## 6. Guardrails (Larangan Keras)
* **JANGAN** membuat relasi langsung Many-to-Many tanpa melalui tabel perantara (`mk_cpl`, `cpmk_cpl`, dan `pengampu_krs`).
* **JANGAN** mengembalikan `password_hash` di dalam skema response Pydantic mana pun.
* **JANGAN** menaruh *hardcoded secret key* atau kredensial PostgreSQL di dalam kode; selalu gunakan file `.env`.
## 7. Pemetaan CPMK–CPL
Dosen mengelola `cpmk_cpl` (PK gabungan `cpmk_id`, `cpl_id`; CASCADE dari CPMK, RESTRICT dari CPL) hanya untuk MK yang diampu. CPL harus sudah dibebankan pada MK melalui `mk_cpl`. Aturan kelengkapan, integritas nilai dan rumus agregasi mengikuti SCHEMA.md §1.4–2.
