# Dokumentasi Analisis & Perancangan Sistem Pengukuran Capaian Pembelajaran (OBE)
**Institusi:** Politeknik Negeri Lhokseumawe (PNL)  
**Arsitektur Teknologi:** React.js (Frontend), FastAPI (Backend), PostgreSQL (Database)

---

## 1. Gambaran Umum & Aktor Sistem
Sistem ini dirancang untuk mendigitalisasi proses perencanaan, pemetaan, penilaian, dan evaluasi berbasis *Outcome-Based Education* (OBE). Sistem menerapkan *Role-Based Access Control* (RBAC) dengan tiga aktor utama:

1. **Kaprodi (Admin):** Bertanggung jawab pada tingkat makro kurikulum (Master CPL, Profil Lulusan, Mata Kuliah, dan Matriks Pembebanan).
2. **Dosen Pengampu:** Bertanggung jawab pada tingkat mikro perkuliahan (Merumuskan CPMK/Sub-CPMK, menetapkan instrumen/bobot penilaian, dan menginput nilai mahasiswa).
3. **Mahasiswa:** Bertanggung jawab memantau hasil studi pribadi melalui rincian nilai mentah dan visualisasi capaian OBE (*read-only*).

---

## 2. Kebutuhan Sistem (Requirements)

### 2.1. Kebutuhan Fungsional (Functional Requirements)
* **Autentikasi:** Pengguna (Kaprodi, Dosen, Mahasiswa) dapat melakukan Login dan Logout sesuai hak akses masing-masing.
* **Manajemen Master Data (Kaprodi):** Mengelola data Program Studi, Master CPL (Sikap, Keterampilan Umum, Pengetahuan, Keterampilan Khusus), Mata Kuliah, serta data Dosen dan Mahasiswa.
* **Pemetaan Matriks OBE (Kaprodi):** Memetakan dan membebankan Master CPL ke dalam Mata Kuliah tertentu.
* **Penyusunan Capaian (Dosen):** Merumuskan CPMK berdasarkan CPL yang dibebankan pada mata kuliah, serta memecahnya menjadi Sub-CPMK.
* **Konfigurasi Penilaian (Dosen):** Menentukan instrumen penilaian (Tugas, Kuis, Praktikum, UTS, UAS) beserta bobot persentasenya yang ditautkan langsung ke Sub-CPMK.
* **Input Nilai (Dosen):** Memasukkan nilai mentah mahasiswa (0–100) per instrumen penilaian secara massal (*spreadsheet/grid view*).
* **Kalkulasi & Visualisasi Otomatis (Sistem):** Menghitung persentase ketercapaian CPL/CPMK secara otomatis dan menyajikannya dalam bentuk grafik jaring laba-laba (*Radar Chart*) maupun diagram batang (*Bar Chart*).
* **Pelaporan (Kaprodi & Dosen):** Membuat laporan asesmen OBE dan mengekspor data capaian ke format CSV/PDF.

### 2.2. Kebutuhan Non-Fungsional (Nonfunctional Requirements)
* **Performa & Skalabilitas:** Waktu respon API standar maksimal $500\text{ ms}$; kalkulasi agregasi nilai satu kelas selesai di bawah $2\text{ detik}$; mampu menangani minimal $200$ pengguna bersamaan (*concurrent users*).
* **Keamanan:** Autentikasi berbasis *JSON Web Token* (JWT), enkripsi kata sandi menggunakan algoritma *Bcrypt*, dan proteksi *SQL Injection* melalui ORM (SQLAlchemy).
* **Usability:** Antarmuka *responsive* (mendukung desktop dan *smartphone*) dengan penyajian data berbasis grafik interaktif.
* **Keandalan Data:** Penerapan *Foreign Key Constraints* (`ON DELETE CASCADE / RESTRICT`) pada PostgreSQL untuk menjaga integritas relasi data, serta pencadangan (*backup*) harian otomatis.

---

## 3. Alur Proses Bisnis (Activity Flow Sederhana)

1. **Alur Kaprodi (Admin):**
   * Membuka sistem $\rightarrow$ Menginput daftar Mata Kuliah dan target lulusan (Master CPL) $\rightarrow$ Menentukan Mata Kuliah mana yang menanggung CPL tertentu (Matriks Pembebanan) $\rightarrow$ Sistem menyimpan aturan kurikulum.
2. **Alur Dosen:**
   * Memilih Mata Kuliah yang diampu $\rightarrow$ Sistem menampilkan CPL turunan dari Kaprodi $\rightarrow$ Menyusun CPMK dan Sub-CPMK $\rightarrow$ Membuat daftar instrumen tugas/ujian beserta bobotnya $\rightarrow$ Menginput nilai mahasiswa $\rightarrow$ Sistem menghitung persentase capaian otomatis $\rightarrow$ Melihat laporan dan grafik kelas.
3. **Alur Mahasiswa:**
   * Membuka sistem $\rightarrow$ Memilih Mata Kuliah yang diambil $\rightarrow$ Sistem mengolah nilai dan menggambar grafik $\rightarrow$ Melihat rincian nilai tugas/ujian serta grafik ketercapaian target belajar pribadi.

---

## 4. Arsitektur Data & Relasi Database (ERD)
Karena menggunakan basis data relasional (PostgreSQL), relasi *Many-to-Many* (M:N) dipecah menggunakan tabel perantara (*Junction Table*).

### Daftar Entitas Utama:
1. **`users`**: Menyimpan akun pengguna (`id`, `nim_nidn`, `nama`, `email`, `role`, `password_hash`).
2. **`prodi`**: Menyimpan data program studi (`id`, `nama_prodi`, `jenjang`).
3. **`master_cpl`**: Menyimpan standar capaian lulusan (`id`, `prodi_id` [nullable untuk CPL Nasional], `kode_cpl`, `kategori`, `deskripsi`).
4. **`mata_kuliah`**: Menyimpan daftar mata kuliah (`id`, `prodi_id`, `kode_mk`, `nama_mk`, `sks`, `semester`, `deskripsi`).
5. **`mk_cpl` *(Junction Table)***: Memecah relasi M:N antara `mata_kuliah` dan `master_cpl` (`mk_id`, `cpl_id`, `urutan_rps`).
6. **`pengampu_krs` *(Junction Table)***: Memecah relasi M:N antara `users` dan `mata_kuliah` (`user_id`, `mk_id`, `status` [Dosen Pengampu / Mahasiswa Mengambil]).
7. **`cpmk`**: Capaian pembelajaran tingkat mata kuliah (`id`, `mk_id`, `kode_cpmk`, `deskripsi`).
8. **`sub_cpmk`**: Turunan spesifik dari CPMK (`id`, `cpmk_id`, `kode_sub`, `deskripsi`).
9. **`instrumen_penilaian`**: Komponen evaluasi per Sub-CPMK (`id`, `sub_cpmk_id`, `jenis_instrumen`, `bobot_persentase`).
10. **`nilai_mahasiswa`**: Penyimpanan skor aktual mahasiswa (`id`, `instrumen_id`, `mahasiswa_id`, `nilai_mentah`, `waktu_input`).

---

## 5. Rancangan Antarmuka Pengguna (UI/UX Blueprint)
Desain menggunakan gaya *Dashboard Panel* modern dengan konsistensi palet warna eksisting (*single color tone*):

1. **Dashboard Utama:** Navigasi *Sidebar* di kiri, *Topbar* profil di atas, serta kartu ringkasan statistik (jumlah MK diampu dan progres pengisian nilai).
2. **Halaman Kelola Master CPL (Kaprodi):** *Data Table* berisi Kode CPL, Kategori, Deskripsi, tombol aksi (Edit/Hapus), serta *modal form* untuk tambah data.
3. **Halaman Matriks Pembebanan (Kaprodi):** Pilihan *dropdown* Mata Kuliah yang diikuti daftar CPL dengan *checkbox/toggle* untuk menautkan beban CPL.
4. **Halaman Susun CPMK & Sub-CPMK (Dosen):** Tampilan berjenjang (*Accordion / Nested Cards*) yang menampilkan daftar CPMK beserta Sub-CPMK di dalamnya, dilengkapi tombol penambahan instrumen penilaian dan bobot persentase.
5. **Halaman Input Nilai (Dosen):** Tampilan *Spreadsheet / Data Grid* dengan baris berisi daftar Mahasiswa dan kolom berisi Instrumen Penilaian untuk pengisian skor $0\text{--}100$ secara cepat.
6. **Halaman Visualisasi Capaian (Dosen & Mahasiswa):** Menampilkan grafik *Radar Chart* (Jaring Laba-laba) yang membandingkan target CPL/CPMK dengan nilai aktual yang dicapai.

---

## 6. Rangkuman Artefak Desain yang Telah Dihasilkan
* **Use Case Diagram:** Memetakan interaksi `Pengguna`, `Kaprodi`, `Dosen`, dan `Mahasiswa` terhadap 11 fungsionalitas utama sistem.
* **Sequence Diagram:** Memvisualisasikan komunikasi 3 lapis antara *Frontend* (React.js), *Backend API* (FastAPI), dan *Database* (PostgreSQL) dalam fase penyusunan capaian, input nilai, hingga kalkulasi OBE.
* **Activity Diagram:** Tersedia dalam versi teknis maupun versi naratif sederhana yang dipisah untuk masing-masing peran (Kaprodi, Dosen, Mahasiswa).
* **Class Diagram & ERD:** Memodelkan struktur objek *backend* beserta skema tabel fisik lengkap dengan *Primary Key* (PK) dan *Foreign Key* (FK).