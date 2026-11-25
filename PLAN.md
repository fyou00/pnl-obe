# PLAN.md - Peta Jalan & Pelacak Progres Pengembangan Sistem OBE PNL

**Instruksi untuk Agent:** Selalu periksa file ini sebelum memulai tugas baru. Tandai item dengan `[x]` segera setelah implementasi selesai dan terverifikasi.

---

## Fase 1: Analisis & Perancangan Sistem (Selesai)
* [x] Definisi kebutuhan fungsional, non-fungsional, dan aktor RBAC (Kaprodi, Dosen, Mahasiswa).
* [x] Pemodelan proses bisnis (BPMN & Activity Diagram untuk ketiga aktor).
* [x] Perancangan Use Case Diagram & Sequence Diagram (React $\leftrightarrow$ FastAPI $\leftrightarrow$ PostgreSQL).
* [x] Perancangan awal Class Diagram & Physical ERD (11 tabel; digantikan revisi akademik pra-migrasi 21 tabel).

## Fase 2: Desain Antarmuka Pengguna (UI/UX Figma)
* [x] Penyempurnaan dashboard desktop via Figcraft MCP: profil di bawah sidebar, pemilih konteks di samping judul, topbar Light Theme dengan jam/tanggal WIB (toggle dark mode dihapus), serta papan varian kosong (TI-K), terkunci periode, loading skeleton, auth/error guards (403/401), data ilustrasi, penilaian belum lengkap, dan spesifikasi motion ikon duotone fill + scale ringan. Jam/tanggal masih contoh statis pada desain. Desain mobile tidak termasuk lingkup proyek.
* [x] Menyusun Master Prompt UI & mengekstrak *color tone* eksisting.
* [x] Generate & finalisasi 6 *screen* utama dan layar ekstensi di `design/pnl-obe.figcraft` (Halaman `01`–`08`, 15 layar desktop + 3 papan *system states* & *motion spec*, Light Theme Only):
  * [x] Layout Utama (Sidebar 9 item Admin / Dosen / Mahasiswa, Topbar Light, Statistik Dashboard, Auth Login, Angkatan & Roster, Paket & Penugasan, serta Laporan & Audit Log).
    * [x] Skeleton dashboard Admin, Dosen, dan Mahasiswa berpalet netral di `design/pnl-obe.figcraft` via Figcraft MCP; seluruh 15 layar desktop dan papan *system states* & *motion* terorganisasi pada Halaman `06` (`01`–`08` Auth & Admin), Halaman `07` (`09`–`15` Dosen & Mahasiswa), dan Halaman `08` (`01`–`03` *System States* & *Motion*), dan telah diperiksa melalui screenshot.
  * [x] Halaman Kelola Master CPL & Versi Kurikulum (Kaprodi).
  * [x] Halaman Matriks Pembebanan CPL-MK (Kaprodi).
  * [x] Halaman Susun CPMK, Sub-CPMK & Instrumen (Dosen).
    * [x] Dua kondisi rancangan tersedia di Figcraft dan terhubung dari Dashboard Dosen: draft Jaringan TI-3C (bobot 80%, satu CPMK belum terpetakan) dan rancangan Basis Data terkunci untuk TI-3A/TI-3B (bobot 100%). Navigasi ke kedua frame dan kembali ke dashboard sudah diperiksa; kontrol pengisian masih berupa desain statis.
  * [x] Halaman Input Nilai Mahasiswa / Spreadsheet Grid (Dosen).
    * [x] Satu layar input nilai Basis Data TI-3A dengan 30 peserta ilustratif dan empat instrumen. Spesifikasi validasi inline untuk implementasi frontend ada di docs/DESIGN.md §5.
  * [x] Halaman Visualisasi Capaian Radar Chart & Rekap Laporan Kelas (Dosen & Mahasiswa, tanpa garis target CPL).
    * [x] Satu layar rincian nilai Mahasiswa dan satu layar Rekap & Laporan Kelas Dosen menampilkan instrumen terinput vs `—` (NULL) serta angka `0` valid beserta capaian per CPMK dan CPL aktual.

## Fase 3: Setup Backend & Database Layer (FastAPI + PostgreSQL)
* [x] Inisialisasi struktur proyek FastAPI (`app/core`, `app/models`, `app/schemas`, `app/services`, `app/api/v1`).
* [x] Konfigurasi koneksi PostgreSQL & environment variables (`.env`).
* [x] Implementasi 21 tabel SQLAlchemy sesuai SCHEMA.md terbaru (UUID, kurikulum berversi, periode/kelas, rancangan bersama, FK/UNIQUE/CHECK, RESTRICT riwayat).
* [x] Setup Alembic & jalankan migrasi awal database berdasarkan revisi akademik 21 tabel; verifikasi seluruh constraint sebelum migrasi.
* [x] Implementasi sistem Autentikasi JWT & *Middleware* RBAC (`Admin`, `Dosen`, `Mahasiswa`).
* [x] Buat *seeder script* untuk data awal (1 akun Admin Kaprodi, sampel Prodi, Dosen, dan Mahasiswa).

## Fase 4: Pengembangan Endpoint API & Logika OBE
* [ ] **Modul Kaprodi:** CRUD `prodi`, `master_cpl`, `mata_kuliah`, dan *endpoint* pemetaan matriks `mk_cpl`.
  * [x] Master MK, versi kurikulum dan snapshot MK paket, CPL per versi, matriks pembebanan, aktivasi/arsip/salin, audit dan RBAC Admin per prodi.
  * [ ] CRUD prodi (di luar lingkup modul master/kurikulum ini).
* [x] **Modul Akademik:** angkatan/kurikulum, periode Ganjil/Genap, roster kelas A–E/K, status Aktif/Cuti/Nonaktif, paket massal dan penugasan satu dosen per kelas MK melalui rancangan bersama; tanpa pengulangan.
  * [x] Tahap 2: angkatan, periode, kelas A–E/K, profil angkatan dari akun Mahasiswa yang sudah ada, roster/status per periode, audit, validasi prodi/semester dan perlindungan riwayat.
  * [x] Tahap 3: pratinjau dan penerapan paket MK massal atomik/idempoten, satu dosen per kelas MK, rancangan bersama dan koreksi pengampu sebelum nilai.
* [x] **Modul Dosen (Perencanaan):** CRUD rancangan bersama per dosen/kurikulum MK/periode, `cpmk`, `sub_cpmk`, instrumen dan pemetaan CPL; salin draft antarperiode, bobot 100%, pembekuan struktur sejak nilai pertama.
* [x] **Modul Dosen (Penilaian):** bulk upsert nilai berdasarkan instrumen + peserta kelas MK, atomik, validasi lintas rancangan/kelas/periode, dan audit perubahan.
* [x] **Modul Penguncian:** penutupan/pembukaan kembali periode oleh Admin dengan alasan/audit dan lock transaksi; lindungi seluruh riwayat.
* [x] **Modul Kalkulasi OBE:** *Service* perhitungan agregat persentase ketercapaian CPMK & CPL + format JSON siap pakai untuk *Radar Chart*.
* [x] **Modul Pelaporan:** *Endpoint* audit log, laporan prodi/lintas kelas, serta ekspor rekap nilai & capaian OBE ke CSV/PDF.

## Fase 5: Pengembangan & Integrasi Frontend (React.js)
* [ ] Setup proyek React.js, TailwindCSS (sesuai *color tone* Figma), dan state management / HTTP client (Axios/TanStack Query).
* [ ] Implementasi integrasi Halaman Login & penyimpanan token JWT (Protected Routes per Role).
* [ ] Implementasi Halaman Kaprodi (Tabel Master CPL & Matriks Pembebanan interaktif).
* [ ] Implementasi Halaman Dosen (Accordion CPMK/Sub-CPMK & Spreadsheet Grid Input Nilai).
* [ ] Implementasi Komponen Visualisasi *Radar Chart* untuk Dosen dan Mahasiswa.

## Fase 6: Pengujian & Deployment
* [ ] Pengujian integrasi API (memastikan isolasi hak akses antar-role berjalan ketat).
* [x] Validasi akurasi rumus kalkulasi agregat nilai OBE.
* [ ] Konfigurasi *production build* & *deployment* ke server internal PNL.
## Penyelarasan skema dan diagram
* [x] Tegaskan aturan KRS paket yang ditetapkan kampus di `AGENTS.md` §2.1 dan perjelas filter tampilan mahasiswa di `docs/DESIGN.md`.
* [x] Dokumentasikan pemetaan CPMK–CPL, integritas nilai, agregasi CPL, dan hak ekspor dosen.
* [x] Implementasikan model/migrasi `cpmk_cpl`, validasi transaksi dan bulk upsert sesuai SCHEMA.md.
* [x] Uji penolakan akses lintas MK, CPL di luar pembebanan, nilai ganda, bobot tidak lengkap, dan agregasi CPL lintas MK.

## Finalisasi akademik pra-migrasi (17 November 2026)
* [x] Konfirmasi lingkup awal Teknik Informatika, kesiapan perluasan prodi, periode Ganjil/Genap, kelas tingkat 1–4 huruf A–E, dan K untuk Cuti/Nonaktif.
* [x] Konfirmasi paket per angkatan/semester, kurikulum berversi, satu dosen per kelas MK, rancangan bersama per dosen/MK kurikulum/periode, tanpa pengulangan MK, dan penguncian periode.
* [x] Selaraskan AGENTS.md, SCHEMA.md (21 tabel, integritas, rumus, diagram dan skenario penerimaan), serta docs/DESIGN.md. Pemeriksaan konsistensi dokumentasi selesai; belum membuat backend/migrasi.
* [ ] Terapkan skenario penerimaan SCHEMA.md §4 pada model, layanan, API, dan uji concurrency saat backend dibangun.
* [x] Sesuaikan artefak Figcraft dengan konteks periode/kelas/kurikulum dan label filter mahasiswa; artefak final 15 layar desktop dan 3 papan states/motion pada halaman `06`–`08` telah diselaraskan (isolasi kurikulum, pengecualian paket TI-K tanpa teks "Kelas K" di sidebar, sidebar Admin 9 item konsisten, Light Theme Only).

## Verifikasi fondasi backend (17 November 2026)
* [x] FastAPI factory, konfigurasi environment privat, SQLAlchemy session, endpoint health/readiness dan panduan menjalankan backend.
* [x] Migrasi awal 21 tabel: upgrade/downgrade/upgrade pada PostgreSQL disposable, kesesuaian metadata tanpa drift, serta CHECK/FK/UNIQUE/RESTRICT.
* [x] Seed idempoten prodi Teknik Informatika dan akun Admin; opsi demo Dosen/Mahasiswa/angkatan dengan password dari environment, tanpa kredensial bawaan.
* [x] JWT/Bcrypt, profil, logout dengan pencabutan token persisten, role/status akun dari database, dan endpoint baca kelas sesuai prodi/penugasan/kepesertaan.
* [x] Verifikasi fondasi: 23 tes lulus pada PostgreSQL asli, Ruff lint/format dan pip check lolos, alembic check tanpa drift, serta HTTP lokal health/readiness/login/logout tiga peran berhasil. Terdapat satu peringatan deprecation TestClient/httpx dari dependensi. Belum mencakup layanan tulis akademik, penilaian, atau kalkulasi OBE.

## Modul Master dan Kurikulum (22 November 2026)
* [x] API Admin untuk CRUD master MK, versi kurikulum Draft, snapshot MK paket dan CPL; daftar/detail/pencarian/paginasi dengan validasi input dan prodi dari akun.
* [x] Penggantian matriks atomik, pembatasan CPL nasional S/KU dan versi/prodi yang sama, serta penolakan penghapusan pembebanan yang masih dipakai CPMK.
* [x] Aktivasi/arsip dengan parent row lock, salin versi sebagai Draft dengan UUID baru tanpa kelas/rancangan/nilai, audit atomik dan perlindungan snapshot historis.
* [x] Verifikasi: 35 tes PostgreSQL lulus (termasuk CRUD, duplikasi/rollback, ACL lintas role/prodi, proteksi riwayat, salin, dan konkurensi aktivasi/edit), Ruff lint/format lolos, serta alembic check tanpa drift; tanpa migrasi skema baru.

## Modul Angkatan dan Kelas (22 November 2026)
* [x] CRUD angkatan/periode/kelas dan penempatan mahasiswa per periode, dengan JWT/RBAC Admin serta paginasi/filter prodi yang konsisten.
* [x] Kurikulum Aktif untuk angkatan baru, paritas Ganjil/Genap, semester studi seragam per angkatan/periode, label dinamis tingkat 1–4, dan K khusus Cuti/Nonaktif.
* [x] Sinkronisasi kepesertaan saat koreksi roster sebelum nilai; penolakan pengulangan MK, perubahan setelah nilai, identitas yang sudah digunakan, dan periode tertutup; audit atomik dan lock angkatan/periode.
* [x] Verifikasi 47 tes PostgreSQL lulus (12 tes baru termasuk rollback dan race periode ditutup), Ruff lint/format lolos dan Alembic check tanpa drift. Tidak mengubah frontend atau menambah migrasi.

## Modul Paket MK dan Pengampu (22 November 2026)
* [x] Endpoint Admin untuk pilihan Dosen, pratinjau paket angkatan/periode, penerapan seluruh pasangan kelas reguler–MK semester, dan koreksi dosen per kelas MK.
* [x] Validasi kurikulum, prodi, roster Aktif dan dosen aktif; kelas K dikecualikan, tanpa KRS mandiri atau pengulangan MK.
* [x] Rancangan bersama per dosen/MK kurikulum/periode, audit atomik, penerapan ulang tanpa duplikasi/reset nilai, serta penolakan pergantian dosen setelah ada nilai.
* [x] Verifikasi 58 tes PostgreSQL lulus (11 tes baru termasuk rollback dan penerapan bersamaan), Ruff lint/format bersih, dan Alembic check tanpa drift; tanpa migrasi baru atau perubahan frontend.

## Modul Dosen: Rancangan Penilaian (22 November 2026)
* [x] Daftar/detail rancangan milik Dosen dengan label periode, kelas pengguna, CPL tersedia, tree CPMK/Sub-CPMK/instrumen, serta status kesiapan dan alasan penguncian dari backend.
* [x] CRUD CPMK/Sub-CPMK/instrumen dan pemetaan CPL atomik; CPL harus dibebankan pada MK kurikulum yang sama, bobot memakai Decimal dengan total maksimum 100.00% dan draft belum lengkap tetap diperbolehkan.
* [x] Perlindungan seluruh struktur bersama setelah nilai pertama (termasuk 0) atau periode ditutup; penguncian periode lalu rancangan dan pemeriksaan ulang penugasan setelah menunggu lock.
* [x] Salin sumber milik Dosen pada periode lain/kurikulum MK sama ke target kosong hasil penugasan Admin, dengan UUID anak baru, tanpa peserta/nilai dan tanpa menimpa sumber.
* [x] Verifikasi 73 tes PostgreSQL lulus (15 tes baru termasuk presisi, ACL, rollback, salin dan konkurensi), serta verifikasi ulang respons daftar periode opsional/salin/akses; Ruff lint/format bersih dan Alembic check tanpa drift. Tanpa migrasi baru atau perubahan frontend.

## Tahap 5: Nilai dan Capaian (22 November 2026)
* [x] Bulk upsert nilai Dosen atomik/idempoten per instrumen + peserta kelas MK, Decimal 0–100, validasi rancangan/roster/akun/angkatan/kurikulum/prodi, serta audit skor sebelum/sesudah.
* [x] Admin menutup/membuka kembali periode dengan alasan wajib dan audit atomik; lock periode lalu rancangan menyerialkan input nilai, koreksi penugasan dan pembekuan struktur sejak nilai pertama.
* [x] Nilai dan capaian pribadi Mahasiswa dari identitas JWT, rincian Sub-CPMK/CPMK/CPL/MK dan rekap kelas hanya bagi Admin/Dosen terkait; kelas pengguna rancangan bersama tetap terpisah.
* [x] CPL pribadi lintas MK per periode atau kumulatif hingga periode pilihan, tanpa bobot SKS tambahan atau penggabungan lintas versi; Decimal dibulatkan HALF_UP hanya pada hasil akhir, nilai hilang tetap null dan rekap memakai mahasiswa lengkap beserta jumlah lengkap/total.
* [x] Verifikasi 94 tes PostgreSQL lulus (21 tes baru: presisi, kelengkapan, privasi, rollback audit, upsert, penguncian/penugasan bersamaan dan agregasi lintas MK/periode/versi), Ruff lint/format bersih dan Alembic check tanpa drift. Tanpa migrasi baru atau perubahan frontend. Ekspor CSV/PDF dan rekap lintas beberapa kelas belum termasuk tahap ini.

## Tahap 6: Audit Log & Pelaporan CSV/PDF (25 November 2026)
* [x] Endpoint Admin `GET /api/v1/audit-log` (isolasi prodi, filter `periode_id`/`aksi`/`entitas`, pencarian literal `q`, paginasi, urut terbaru lebih dulu, dan sanitasi field sensitif).
* [x] Endpoint Admin `GET /api/v1/laporan/prodi` dan `/laporan/prodi/ekspor` (`csv`/`pdf`) dengan isolasi versi kurikulum eksplisit, filter `semester`, pengecualian kelas TI-K, dan agregasi CPL terbobot peserta lengkap.
* [x] Endpoint Admin/Dosen `GET /api/v1/laporan/lintas-kelas` dan `/laporan/lintas-kelas/ekspor` dengan rata-rata terbobot `Decimal` (tanpa rata-rata kelas tak berbobot) dan penolakan lintas versi kurikulum (`409`).
* [x] Endpoint ekspor kelas `GET /api/v1/kelas-mk/{kelas_mk_id}/ekspor` (Admin/Dosen) serta ekspor pribadi Mahasiswa `GET /api/v1/capaian/saya/ekspor` (`csv`/`pdf`, periodik/kumulatif, bebas kebocoran nilai mahasiswa lain, dan dukungan state TI-K) menggunakan pembangun PDF 1.4 stdlib tanpa dependensi eksternal tambahan.
* [x] Verifikasi: 99 tes PostgreSQL lulus (`pytest -q`, mencakup 5 skenario baru pada `tests/test_reporting.py`), `ruff check .` dan `ruff format --check .` bersih pada seluruh 61 file backend; header CORS `Content-Disposition` diekspos dan frontend belum diubah.
