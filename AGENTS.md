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
* Lingkup awal hanya **Teknik Informatika**. Tetap gunakan entitas `prodi` dan pembatasan prodi; jangan hardcode nama/id prodi pada logika aplikasi. Perluasan multi-prodi dilakukan kemudian.
* **Admin (Kaprodi):** mengelola master, versi kurikulum, angkatan, periode akademik, kelas, peserta paket, dan penugasan dosen pada prodinya. Membuka/menutup periode serta membuka kembali dengan alasan tercatat; tidak menginput nilai harian.
* **Dosen:** mengelola rancangan penilaian dan nilai hanya untuk `kelas_mk` yang ditugaskan kepadanya. Akses ditelusuri melalui `rancangan_penilaian.dosen_id`, bukan hubungan langsung pengguna–master MK. Dilarang mengubah Master CPL atau kurikulum.
* **Mahasiswa:** read-only atas nilai dan capaian pribadi dari `peserta_kelas_mk`. Tidak melihat nilai mahasiswa lain.

### 2.1. Sistem KRS Paket dan Kelas
* MK paket ditetapkan kampus melalui Admin/Kaprodi berdasarkan versi kurikulum angkatan dan semester studi. Admin menerapkan paket ke kelas secara massal, lalu menetapkan satu dosen per kelas MK.
* Mahasiswa **tidak memilih, menambah, atau membatalkan MK secara mandiri**. Dropdown **“Tampilkan mata kuliah”** hanya filter atas kelas MK yang telah ditetapkan, bukan pengisian KRS.
* Periode = tahun akademik (contoh `2026/2027`) + `Ganjil`/`Genap`; tidak ada semester pendek.
* Kelas reguler A–E; angka pada TI-1A s.d. TI-4E menunjukkan tingkat tahun: semester 1–2 = tingkat 1, 3–4 = 2, 5–6 = 3, 7–8 = 4. Simpan semester studi 1–8; tingkat/label diturunkan, bukan umur angkatan otomatis.
* Mahasiswa cuti/nonaktif ditempatkan pada kelas **K**, dengan status `Cuti` atau `Nonaktif` tersimpan terpisah. K tidak menerima paket MK. Anggota dan kelas dicatat per periode agar riwayat tidak tertimpa; huruf kelas reguler biasanya tetap.
* **Tidak mendukung pengulangan MK.** Jangan membuat alur remedial/pengambilan ulang; riwayat peserta dan nilai tetap dipertahankan.

### 2.2. Rancangan Bersama dan Riwayat
* Satu kelas MK memiliki tepat satu dosen. Tidak ada tim dosen. Dosen dapat mengampu banyak kelas/MK.
* Dosen + MK dalam kurikulum yang sama + periode yang sama memakai **satu `rancangan_penilaian` bersama** untuk seluruh kelas terkait: CPMK, pemetaan CPL, Sub-CPMK, instrumen, dan bobot. Dosen berbeda boleh memiliki rancangan berbeda. Peserta, nilai, dan rekap kelas tetap terpisah.
* Kurikulum yang berbeda merupakan konteks terpisah; jangan menyatukan CPL atau penilaian lintas versi kurikulum secara otomatis.
* Periode berikutnya boleh menyalin rancangan sebagai draft baru tanpa nilai/peserta. Perubahan tidak boleh merambat ke periode lama.
* Kurikulum aktif bersifat tetap; revisi isi memakai versi baru. Setelah ada nilai, struktur rancangan dan penugasan kelas terkait dibekukan; nilai masih dapat dilengkapi selama periode terbuka.
* Penutupan periode mengunci paket, peserta, penugasan, rancangan, dan nilai. Hanya Admin dapat membuka kembali dengan alasan dan audit; pembukaan kembali tidak menghapus riwayat dan tidak membebaskan perubahan struktur yang sudah memiliki nilai.

## 3. Skema Database & Relasi (PostgreSQL)
* Entitas utama memakai UUID; junction memakai PK gabungan bila ditetapkan dalam `SCHEMA.md`. Skema fisik dan diagram terbaru adalah **SCHEMA.md §1 dan §3**, bukan skema awal 11 tabel.
* Master MK dipisahkan dari `kurikulum_mk` (nama/SKS/semester per versi), `kelas_mk` (pelaksanaan per kelas/periode), dan `rancangan_penilaian` (rancangan bersama per dosen/MK kurikulum/periode).
* `pengampu_krs(user_id, mk_id)` **digantikan** oleh penugasan dosen melalui rancangan pada `kelas_mk` dan junction `peserta_kelas_mk`. Jangan mengimplementasikan tabel lama.
* CPMK milik `rancangan_penilaian`; instrumen ditelusuri melalui Sub-CPMK/CPMK. Nilai milik pasangan instrumen dan peserta kelas MK, dengan validasi kesamaan rancangan.
* Master dan riwayat akademik yang telah dipakai dilindungi `RESTRICT`. `CASCADE` hanya untuk anak rancangan draft yang aman dihapus dan junction sebagaimana SCHEMA.md; jangan menghapus nilai historis melalui penghapusan pengguna/kelas/periode.

## 4. Logika Kalkulasi OBE (Core Business Logic)
* Penilaian bersifat *bottom-up*: Nilai diinput pada `instrumen_penilaian` $\rightarrow$ diagregasi ke `sub_cpmk` $\rightarrow$ diagregasi ke `cpmk` $\rightarrow$ dipetakan ke `master_cpl`.
* Seluruh perhitungan agregat persentase capaian harus dilakukan di **Backend Service Layer (FastAPI)** menggunakan `Decimal` dengan pembulatan dua desimal hanya pada hasil akhir, bukan dihitung di *client/frontend*.

## 5. Konvensi Penulisan Kode (Coding Standards)
* **Backend (Python/FastAPI):**
  * Gunakan `snake_case` untuk nama file, fungsi, variabel, dan kolom database.
  * Pisahkan logika ke dalam lapisan: `models/` (SQLAlchemy), `schemas/` (Pydantic), `crud/` atau `services/` (Business Logic), dan `api/v1/endpoints/` (Routes).
  * Gunakan *dependency injection* (`Depends`) untuk validasi token JWT dan pengecekan `role`.
* **Frontend (React.js):**
  * Gunakan `PascalCase` untuk nama komponen (misal: `RadarCapaianChart.jsx`, `MatriksPembebananTable.jsx`) dan `camelCase` untuk variabel/fungsi.
  * Jaga konsistensi palet warna sesuai desain Figma (gunakan variabel warna Tailwind yang sudah dikonfigurasi).

## 6. Guardrails (Larangan Keras)
* **JANGAN** membuat relasi langsung Many-to-Many tanpa melalui tabel perantara (`mk_cpl`, `cpmk_cpl`, dan `peserta_kelas_mk`).
* **JANGAN** mengembalikan `password_hash` di dalam skema response Pydantic mana pun.
* **JANGAN** menaruh *hardcoded secret key* atau kredensial PostgreSQL di dalam kode; selalu gunakan file `.env`.
## 7. Pemetaan CPMK–CPL
Dosen mengelola `cpmk_cpl` hanya pada rancangan miliknya yang terikat kelas MK penugasannya. CPL harus dibebankan melalui `mk_cpl` pada `kurikulum_mk` rancangan tersebut dan berasal dari versi kurikulum yang sama. Kelengkapan, penguncian, integritas nilai, dan rumus agregasi mengikuti SCHEMA.md §1.7–2.

## 8. Menjalankan dan Memverifikasi Backend
* Fondasi backend berada di `backend/`; baca `backend/README.md` untuk environment, PostgreSQL lokal/Docker, migrasi, seed, dan perintah server.
* Dari `backend/` dengan virtualenv aktif, jalankan `ruff check .`, `ruff format --check .`, dan `pytest -q` setelah mengubah backend. Tes integrasi wajib PostgreSQL asli, bukan SQLite; pasang extra `.[local-postgres]` atau isi `TEST_DATABASE_URL` untuk server development dengan hak membuat database disposable.
* Aplikasi tidak membuat tabel atau menjalankan seed saat startup. Migrasi adalah sumber perubahan skema; jangan menggunakan `metadata.create_all` pada startup atau fixture untuk menggantikan pengujian migrasi.
* Jangan commit `.env`, token, password, atau direktori data lokal. Seed tidak boleh mereset password pengguna yang sudah ada. Logout mencabut seluruh JWT pengguna melalui `users.token_version`.
