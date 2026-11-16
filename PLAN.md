# PLAN.md - Peta Jalan & Pelacak Progres Pengembangan Sistem OBE PNL

**Instruksi untuk Agent:** Selalu periksa file ini sebelum memulai tugas baru. Tandai item dengan `[x]` segera setelah implementasi selesai dan terverifikasi.

---

## Fase 1: Analisis & Perancangan Sistem (Selesai)
* [x] Definisi kebutuhan fungsional, non-fungsional, dan aktor RBAC (Kaprodi, Dosen, Mahasiswa).
* [x] Pemodelan proses bisnis (BPMN & Activity Diagram untuk ketiga aktor).
* [x] Perancangan Use Case Diagram & Sequence Diagram (React $\leftrightarrow$ FastAPI $\leftrightarrow$ PostgreSQL).
* [x] Perancangan awal Class Diagram & Physical ERD (11 tabel; digantikan revisi akademik pra-migrasi 21 tabel).

## Fase 2: Desain Antarmuka Pengguna (UI/UX Figma)
* [x] Penyempurnaan dashboard desktop via Figcraft MCP: profil di bawah sidebar, pemilih konteks di samping judul, topbar dengan tampilan toggle dark mode serta jam/tanggal WIB, serta varian kosong, loading, data ilustrasi, dan penilaian belum lengkap. Jam/tanggal masih contoh statis pada desain. Desain mobile tidak termasuk lingkup proyek.
* [x] Menyusun Master Prompt UI & mengekstrak *color tone* eksisting.
* [ ] Generate & finalisasi 6 *screen* utama di Figma via `figma-console-mcp`:
  * [ ] Layout Utama (Sidebar, Topbar, Statistik Dashboard).
    * [x] Skeleton dashboard Admin, Dosen, dan Mahasiswa berpalet netral di `design/pnl-obe.figcraft` via Figcraft MCP; sidebar, topbar, statistik, dan panel per peran telah diperiksa melalui screenshot. Finalisasi desain belum selesai.
  * [ ] Halaman Kelola Master CPL (Kaprodi).
  * [ ] Halaman Matriks Pembebanan CPL-MK (Kaprodi).
  * [ ] Halaman Susun CPMK, Sub-CPMK & Instrumen (Dosen).
  * [ ] Halaman Input Nilai Mahasiswa / Spreadsheet Grid (Dosen).
  * [ ] Halaman Visualisasi Capaian Radar Chart (Dosen & Mahasiswa).

## Fase 3: Setup Backend & Database Layer (FastAPI + PostgreSQL)
* [x] Inisialisasi struktur proyek FastAPI (`app/core`, `app/models`, `app/schemas`, `app/services`, `app/api/v1`).
* [x] Konfigurasi koneksi PostgreSQL & environment variables (`.env`).
* [x] Implementasi 21 tabel SQLAlchemy sesuai SCHEMA.md terbaru (UUID, kurikulum berversi, periode/kelas, rancangan bersama, FK/UNIQUE/CHECK, RESTRICT riwayat).
* [x] Setup Alembic & jalankan migrasi awal database berdasarkan revisi akademik 21 tabel; verifikasi seluruh constraint sebelum migrasi.
* [x] Implementasi sistem Autentikasi JWT & *Middleware* RBAC (`Admin`, `Dosen`, `Mahasiswa`).
* [x] Buat *seeder script* untuk data awal (1 akun Admin Kaprodi, sampel Prodi, Dosen, dan Mahasiswa).

## Fase 4: Pengembangan Endpoint API & Logika OBE
* [ ] **Modul Kaprodi:** CRUD `prodi`, `master_cpl`, `mata_kuliah`, dan *endpoint* pemetaan matriks `mk_cpl`.
* [ ] **Modul Akademik:** angkatan/kurikulum, periode Ganjil/Genap, roster kelas A–E/K, status Aktif/Cuti/Nonaktif, paket massal dan penugasan satu dosen per kelas MK melalui rancangan bersama; tanpa pengulangan.
* [ ] **Modul Dosen (Perencanaan):** CRUD rancangan bersama per dosen/kurikulum MK/periode, `cpmk`, `sub_cpmk`, instrumen dan pemetaan CPL; salin draft antarperiode, bobot 100%, pembekuan struktur sejak nilai pertama.
* [ ] **Modul Dosen (Penilaian):** bulk upsert nilai berdasarkan instrumen + peserta kelas MK, atomik, validasi lintas rancangan/kelas/periode, dan audit perubahan.
* [ ] **Modul Penguncian:** penutupan/pembukaan kembali periode oleh Admin dengan alasan/audit dan lock transaksi; lindungi seluruh riwayat.
* [ ] **Modul Kalkulasi OBE:** *Service* perhitungan agregat persentase ketercapaian CPMK & CPL + format JSON siap pakai untuk *Radar Chart*.
* [ ] **Modul Pelaporan:** *Endpoint* ekspor rekap nilai & capaian OBE ke CSV/PDF.

## Fase 5: Pengembangan & Integrasi Frontend (React.js)
* [ ] Setup proyek React.js, TailwindCSS (sesuai *color tone* Figma), dan state management / HTTP client (Axios/TanStack Query).
* [ ] Implementasi integrasi Halaman Login & penyimpanan token JWT (Protected Routes per Role).
* [ ] Implementasi Halaman Kaprodi (Tabel Master CPL & Matriks Pembebanan interaktif).
* [ ] Implementasi Halaman Dosen (Accordion CPMK/Sub-CPMK & Spreadsheet Grid Input Nilai).
* [ ] Implementasi Komponen Visualisasi *Radar Chart* untuk Dosen dan Mahasiswa.

## Fase 6: Pengujian & Deployment
* [ ] Pengujian integrasi API (memastikan isolasi hak akses antar-role berjalan ketat).
* [ ] Validasi akurasi rumus kalkulasi agregat nilai OBE.
* [ ] Konfigurasi *production build* & *deployment* ke server internal PNL.
## Penyelarasan skema dan diagram
* [x] Tegaskan aturan KRS paket yang ditetapkan kampus di `AGENTS.md` §2.1 dan perjelas filter tampilan mahasiswa di `docs/DESIGN.md`.
* [x] Dokumentasikan pemetaan CPMK–CPL, integritas nilai, agregasi CPL, dan hak ekspor dosen.
* [ ] Implementasikan model/migrasi `cpmk_cpl`, validasi transaksi dan bulk upsert sesuai SCHEMA.md.
* [ ] Uji penolakan akses lintas MK, CPL di luar pembebanan, nilai ganda, bobot tidak lengkap, dan agregasi CPL lintas MK.

## Finalisasi akademik pra-migrasi (17 November 2026)
* [x] Konfirmasi lingkup awal Teknik Informatika, kesiapan perluasan prodi, periode Ganjil/Genap, kelas tingkat 1–4 huruf A–E, dan K untuk Cuti/Nonaktif.
* [x] Konfirmasi paket per angkatan/semester, kurikulum berversi, satu dosen per kelas MK, rancangan bersama per dosen/MK kurikulum/periode, tanpa pengulangan MK, dan penguncian periode.
* [x] Selaraskan AGENTS.md, SCHEMA.md (21 tabel, integritas, rumus, diagram dan skenario penerimaan), serta docs/DESIGN.md. Pemeriksaan konsistensi dokumentasi selesai; belum membuat backend/migrasi.
* [ ] Terapkan skenario penerimaan SCHEMA.md §4 pada model, layanan, API, dan uji concurrency saat backend dibangun.
* [ ] Sesuaikan artefak Figcraft dengan konteks periode/kelas/kurikulum dan label filter mahasiswa; tugas revisi skema ini tidak mengubah desain.

## Verifikasi fondasi backend (17 November 2026)
* [x] FastAPI factory, konfigurasi environment privat, SQLAlchemy session, endpoint health/readiness dan panduan menjalankan backend.
* [x] Migrasi awal 21 tabel: upgrade/downgrade/upgrade pada PostgreSQL disposable, kesesuaian metadata tanpa drift, serta CHECK/FK/UNIQUE/RESTRICT.
* [x] Seed idempoten prodi Teknik Informatika dan akun Admin; opsi demo Dosen/Mahasiswa/angkatan dengan password dari environment, tanpa kredensial bawaan.
* [x] JWT/Bcrypt, profil, logout dengan pencabutan token persisten, role/status akun dari database, dan endpoint baca kelas sesuai prodi/penugasan/kepesertaan.
* [x] Verifikasi fondasi: 23 tes lulus pada PostgreSQL asli, Ruff lint/format dan pip check lolos, alembic check tanpa drift, serta HTTP lokal health/readiness/login/logout tiga peran berhasil. Terdapat satu peringatan deprecation TestClient/httpx dari dependensi. Belum mencakup layanan tulis akademik, penilaian, atau kalkulasi OBE.
