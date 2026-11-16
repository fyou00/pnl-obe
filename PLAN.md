# PLAN.md - Peta Jalan & Pelacak Progres Pengembangan Sistem OBE PNL

**Instruksi untuk Agent:** Selalu periksa file ini sebelum memulai tugas baru. Tandai item dengan `[x]` segera setelah implementasi selesai dan terverifikasi.

---

## Fase 1: Analisis & Perancangan Sistem (Selesai)
* [x] Definisi kebutuhan fungsional, non-fungsional, dan aktor RBAC (Kaprodi, Dosen, Mahasiswa).
* [x] Pemodelan proses bisnis (BPMN & Activity Diagram untuk ketiga aktor).
* [x] Perancangan Use Case Diagram & Sequence Diagram (React $\leftrightarrow$ FastAPI $\leftrightarrow$ PostgreSQL).
* [x] Perancangan Class Diagram & Physical ERD (10 Tabel Relasional).

## Fase 2: Desain Antarmuka Pengguna (UI/UX Figma)
* [x] Menyusun Master Prompt UI & mengekstrak *color tone* eksisting.
* [ ] Generate & finalisasi 6 *screen* utama di Figma via `figma-console-mcp`:
  * [ ] Layout Utama (Sidebar, Topbar, Statistik Dashboard).
  * [ ] Halaman Kelola Master CPL (Kaprodi).
  * [ ] Halaman Matriks Pembebanan CPL-MK (Kaprodi).
  * [ ] Halaman Susun CPMK, Sub-CPMK & Instrumen (Dosen).
  * [ ] Halaman Input Nilai Mahasiswa / Spreadsheet Grid (Dosen).
  * [ ] Halaman Visualisasi Capaian Radar Chart (Dosen & Mahasiswa).

## Fase 3: Setup Backend & Database Layer (FastAPI + PostgreSQL)
* [ ] Inisialisasi struktur proyek FastAPI (`app/core`, `app/models`, `app/schemas`, `app/services`, `app/api/v1`).
* [ ] Konfigurasi koneksi PostgreSQL & environment variables (`.env`).
* [ ] Implementasi model SQLAlchemy sesuai `AGENTS.md` (10 tabel + UUID + `ON DELETE CASCADE`).
* [ ] Setup Alembic & jalankan migrasi awal database.
* [ ] Implementasi sistem Autentikasi JWT & *Middleware* RBAC (`Admin`, `Dosen`, `Mahasiswa`).
* [ ] Buat *seeder script* untuk data awal (1 akun Admin Kaprodi, sampel Prodi, Dosen, dan Mahasiswa).

## Fase 4: Pengembangan Endpoint API & Logika OBE
* [ ] **Modul Kaprodi:** CRUD `prodi`, `master_cpl`, `mata_kuliah`, dan *endpoint* pemetaan matriks `mk_cpl`.
* [ ] **Modul Akademik:** *Endpoint* penugasan Dosen & KRS Mahasiswa (`pengampu_krs`).
* [ ] **Modul Dosen (Perencanaan):** CRUD berjenjang untuk `cpmk`, `sub_cpmk`, dan `instrumen_penilaian` (termasuk validasi total bobot $100\%$).
* [ ] **Modul Dosen (Penilaian):** *Endpoint* *bulk insert/update* untuk `nilai_mahasiswa`.
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