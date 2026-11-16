# DESIGN.md - Dokumen Analisis & Perancangan Sistem Pengukuran Capaian Pembelajaran (OBE)

**Institusi:** Politeknik Negeri Lhokseumawe (PNL)
**Arsitektur Teknologi:** React.js (Frontend), FastAPI (Backend), PostgreSQL (Database)

Dokumen ini memuat *requirements*, alur proses bisnis, dan *blueprint* UI/UX. Aturan RBAC, skema tabel, dan konvensi kode **tidak** diulang di sini — rujuk dokumen sumbernya:

| Topik | Dokumen sumber |
| --- | --- |
| Aturan RBAC, skema database, konvensi kode, guardrails | `AGENTS.md` |
| Skema fisik PostgreSQL (tipe kolom, PK/FK) & rumus kalkulasi OBE | `SCHEMA.md` |
| Peta jalan & pelacak progres per fase | `PLAN.md` |

## Daftar Isi
1. [Gambaran Umum & Aktor Sistem](#1-gambaran-umum--aktor-sistem)
2. [Kebutuhan Sistem](#2-kebutuhan-sistem)
3. [Alur Proses Bisnis](#3-alur-proses-bisnis-activity-flow-sederhana)
4. [Arsitektur Data](#4-arsitektur-data)
5. [Rancangan Antarmuka (UI/UX Blueprint)](#5-rancangan-antarmuka-pengguna-uiux-blueprint)
6. [Artefak Desain](#6-rangkuman-artefak-desain)

---

## 1. Gambaran Umum & Aktor Sistem
Sistem mendigitalisasi proses perencanaan, pemetaan, penilaian, dan evaluasi berbasis *Outcome-Based Education* (OBE), dengan tiga aktor:

1. **Kaprodi (Admin):** lingkup makro kurikulum — Master CPL, Mata Kuliah, Matriks Pembebanan.
2. **Dosen Pengampu:** lingkup mikro perkuliahan — CPMK/Sub-CPMK, instrumen & bobot penilaian, input nilai mahasiswa.
3. **Mahasiswa:** pemantauan hasil studi pribadi — rincian nilai mentah dan visualisasi capaian OBE (*read-only*).

Batasan hak akses tiap aktor didefinisikan pada `AGENTS.md` §2.

---

## 2. Kebutuhan Sistem

### 2.1. Kebutuhan Fungsional
* **Autentikasi:** Login dan Logout sesuai hak akses masing-masing peran.
* **Manajemen Master Data (Kaprodi):** Program Studi, Master CPL (Sikap, Keterampilan Umum, Pengetahuan, Keterampilan Khusus), Mata Kuliah, serta data Dosen dan Mahasiswa.
* **Pemetaan Matriks OBE (Kaprodi):** Membebankan Master CPL ke Mata Kuliah tertentu.
* **Penyusunan Capaian (Dosen):** Merumuskan CPMK dari CPL yang dibebankan, lalu memecahnya menjadi Sub-CPMK.
* **Konfigurasi Penilaian (Dosen):** Menentukan instrumen (Tugas, Kuis, Praktikum, UTS, UAS) beserta bobot persentase yang tertaut ke Sub-CPMK.
* **Input Nilai (Dosen):** Input nilai mentah mahasiswa (0–100) per instrumen secara massal (*spreadsheet/grid view*).
* **Kalkulasi & Visualisasi Otomatis (Sistem):** Menghitung persentase ketercapaian CPL/CPMK dan menyajikannya sebagai *Radar Chart* maupun *Bar Chart*.
* **Pelaporan (Kaprodi & Dosen):** Laporan asesmen OBE dan ekspor capaian ke CSV/PDF.

### 2.2. Kebutuhan Non-Fungsional
* **Performa & Skalabilitas:** respons API standar maksimal $500\text{ ms}$; agregasi nilai satu kelas selesai di bawah $2\text{ detik}$; mendukung minimal $200$ pengguna bersamaan.
* **Keamanan:** JWT, *password hashing* Bcrypt, proteksi *SQL Injection* melalui ORM SQLAlchemy.
* **Usability:** antarmuka *responsive* (desktop & smartphone) dengan grafik interaktif.
* **Keandalan Data:** *Foreign Key Constraints* (`ON DELETE CASCADE / RESTRICT`) pada PostgreSQL dan *backup* harian otomatis.

---

## 3. Alur Proses Bisnis (Activity Flow Sederhana)

1. **Kaprodi (Admin):** input daftar Mata Kuliah dan Master CPL $\rightarrow$ tentukan Mata Kuliah penanggung CPL (Matriks Pembebanan) $\rightarrow$ sistem menyimpan aturan kurikulum.
2. **Dosen:** pilih Mata Kuliah yang diampu $\rightarrow$ sistem menampilkan CPL turunan dari Kaprodi $\rightarrow$ susun CPMK & Sub-CPMK $\rightarrow$ buat instrumen tugas/ujian beserta bobotnya $\rightarrow$ input nilai mahasiswa $\rightarrow$ sistem menghitung persentase capaian $\rightarrow$ lihat laporan dan grafik kelas.
3. **Mahasiswa:** tampilkan salah satu Mata Kuliah dalam paket yang telah ditetapkan kampus melalui Admin/Kaprodi $\rightarrow$ sistem mengolah nilai dan menggambar grafik $\rightarrow$ lihat rincian nilai tugas/ujian serta grafik capaian belajar pribadi. Pemilihan ini hanya filter tampilan, bukan pengisian KRS; aturan KRS paket mengikuti `AGENTS.md` §2.1.

---

## 4. Arsitektur Data
Basis data relasional PostgreSQL; relasi *Many-to-Many* dipecah melalui tabel perantara `mk_cpl` (`mata_kuliah` $\leftrightarrow$ `master_cpl`), `cpmk_cpl`, dan `pengampu_krs` (`users` $\leftrightarrow$ `mata_kuliah`).

Rincian 11 entitas (`users`, `prodi`, `master_cpl`, `mata_kuliah`, `mk_cpl`, `cpmk_cpl`, `pengampu_krs`, `cpmk`, `sub_cpmk`, `instrumen_penilaian`, `nilai_mahasiswa`) beserta tipe kolom dan integritas relasinya ada di `SCHEMA.md` §1.

---

## 5. Rancangan Antarmuka Pengguna (UI/UX Blueprint)
Gaya *Dashboard Panel* modern dengan palet warna eksisting (*single color tone*):

1. **Dashboard Utama:** *Sidebar* kiri, *Topbar* profil di atas, kartu ringkasan statistik (jumlah MK diampu, progres pengisian nilai).
2. **Kelola Master CPL (Kaprodi):** *Data Table* Kode CPL/Kategori/Deskripsi, tombol aksi Edit/Hapus, *modal form* tambah data.
3. **Matriks Pembebanan (Kaprodi):** *dropdown* Mata Kuliah + daftar CPL dengan *checkbox/toggle* penautan beban CPL.
4. **Susun CPMK & Sub-CPMK (Dosen):** tampilan berjenjang (*Accordion / Nested Cards*) CPMK beserta Sub-CPMK, tombol penambahan instrumen dan bobot persentase.
5. **Input Nilai (Dosen):** *Spreadsheet / Data Grid* — baris Mahasiswa, kolom Instrumen, pengisian skor $0\text{--}100$ secara cepat.
6. **Visualisasi Capaian (Dosen & Mahasiswa):** *Radar Chart* yang menampilkan capaian aktual CPL/CPMK dan status kelengkapan.

Pada dashboard Mahasiswa, gunakan label **“Tampilkan mata kuliah”** untuk dropdown filter. Pilihan hanya memuat mata kuliah yang telah ditetapkan kampus pada `pengampu_krs`; tidak menyediakan tindakan tambah, ambil, atau batalkan mata kuliah.

---

## 6. Rangkuman Artefak Desain
* **Use Case Diagram:** interaksi `Pengguna`, `Kaprodi`, `Dosen`, `Mahasiswa` terhadap fungsionalitas utama.
* **Sequence Diagram:** komunikasi 3 lapis Frontend (React.js) $\leftrightarrow$ Backend API (FastAPI) $\leftrightarrow$ Database (PostgreSQL) pada fase penyusunan capaian, input nilai, dan kalkulasi OBE.
* **Activity Diagram:** versi teknis dan versi naratif per peran (Kaprodi, Dosen, Mahasiswa).
* **Class Diagram & ERD:** struktur objek *backend* dan skema tabel fisik lengkap dengan PK/FK.

## 7. Pemetaan dan kelengkapan penilaian
Form CPMK menyediakan pilihan jamak CPL yang telah dibebankan pada MK. Simpan relasi dalam `cpmk_cpl`; dosen tidak mengubah Master CPL. Draft boleh belum dipetakan, tetapi input nilai dan laporan capaian memerlukan seluruh CPMK terpetakan dan total bobot MK 100%. Perubahan pemetaan MK–CPL yang masih dipakai CPMK ditolak. Nilai belum lengkap ditampilkan sebagai belum lengkap, bukan nol. Rumus mengikuti SCHEMA.md §2.
