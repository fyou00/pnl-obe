# SCHEMA.md - Arsitektur Data, Relasi Database, dan Logika Kalkulasi OBE

Dokumen ini berfungsi sebagai *single source of truth* teknis mengenai struktur basis data PostgreSQL, pemodelan sistem, dan rumus agregasi nilai *Outcome-Based Education* (OBE) pada proyek Politeknik Negeri Lhokseumawe (PNL).

---

## 1. Spesifikasi Tabel Database (PostgreSQL Physical Schema)

Seluruh tabel menggunakan **`UUID`** sebagai *Primary Key* (`id`) untuk keamanan dan kemudahan skalabilitas terdistribusi.

### 1.1. Tabel Master & Autentikasi
* **`users`**
  * `id` (`UUID`, PK): Identitas unik pengguna.
  * `nim_nidn` (`VARCHAR(20)`, UNIQUE, NOT NULL): Nomor induk mahasiswa atau dosen.
  * `nama` (`VARCHAR(100)`, NOT NULL): Nama lengkap pengguna.
  * `email` (`VARCHAR(100)`, UNIQUE, NOT NULL): Email institusi untuk login.
  * `role` (`VARCHAR(20)`, NOT NULL): Hak akses (`Admin`, `Dosen`, `Mahasiswa`).
  * `password_hash` (`VARCHAR(255)`, NOT NULL): Kata sandi terenkripsi (*Bcrypt*).

* **`prodi`**
  * `id` (`UUID`, PK): Identitas unik program studi.
  * `nama_prodi` (`VARCHAR(100)`, NOT NULL): Nama program studi.
  * `jenjang` (`VARCHAR(10)`, NOT NULL): Jenjang pendidikan (misal: `D3`, `D4`).

* **`master_cpl`**
  * `id` (`UUID`, PK): Identitas unik Capaian Pembelajaran Lulusan.
  * `prodi_id` (`UUID`, FK $\rightarrow$ `prodi.id`, NULLABLE): Jika `NULL`, berarti merupakan CPL standar nasional (Sikap / Keterampilan Umum).
  * `kode_cpl` (`VARCHAR(10)`, NOT NULL): Kode unik CPL (misal: `CPL-01`).
  * `kategori` (`VARCHAR(5)`, NOT NULL): Kategori (`S`, `KU`, `P`, `KK`).
  * `deskripsi` (`TEXT`, NOT NULL): Rumusan deskripsi capaian lulusan.

* **`mata_kuliah`**
  * `id` (`UUID`, PK): Identitas unik mata kuliah.
  * `prodi_id` (`UUID`, FK $\rightarrow$ `prodi.id`, NOT NULL): Program studi pemilik mata kuliah.
  * `kode_mk` (`VARCHAR(20)`, NOT NULL): Kode mata kuliah (unik per prodi).
  * `nama_mk` (`VARCHAR(100)`, NOT NULL): Nama mata kuliah.
  * `sks` (`INTEGER`, NOT NULL): Bobot Satuan Kredit Semester.
  * `semester` (`INTEGER`, NOT NULL): Semester penempatan mata kuliah.
  * `deskripsi` (`TEXT`, NULLABLE): Deskripsi singkat mata kuliah.

### 1.2. Tabel Perantara (Junction Tables - Relasi Many-to-Many)
* **`mk_cpl`** *(Memecah relasi M:N antara `mata_kuliah` dan `master_cpl`)*
  * `mk_id` (`UUID`, PK, FK $\rightarrow$ `mata_kuliah.id`, `ON DELETE CASCADE`)
  * `cpl_id` (`UUID`, PK, FK $\rightarrow$ `master_cpl.id`, `ON DELETE RESTRICT`)
  * `urutan_rps` (`INTEGER`, NULLABLE): Urutan prioritas pemetaan di RPS.

* **`pengampu_krs`** *(Memecah relasi M:N antara `users` dan `mata_kuliah`)*
  * `user_id` (`UUID`, PK, FK $\rightarrow$ `users.id`, `ON DELETE CASCADE`)
  * `mk_id` (`UUID`, PK, FK $\rightarrow$ `mata_kuliah.id`, `ON DELETE CASCADE`)
  * `status` (`VARCHAR(20)`, NOT NULL): Peran dalam mata kuliah (`Dosen Pengampu` atau `Mahasiswa Mengambil`).

### 1.3. Tabel Transaksi & Penilaian OBE
* **`cpmk`**
  * `id` (`UUID`, PK): Identitas unik Capaian Pembelajaran Mata Kuliah.
  * `mk_id` (`UUID`, FK $\rightarrow$ `mata_kuliah.id`, `ON DELETE CASCADE`, NOT NULL)
  * `kode_cpmk` (`VARCHAR(20)`, NOT NULL): Kode CPMK (misal: `CPMK-1`).
  * `deskripsi` (`TEXT`, NOT NULL): Rumusan kemampuan akhir yang direncanakan.

* **`sub_cpmk`**
  * `id` (`UUID`, PK): Identitas unik Sub-CPMK.
  * `cpmk_id` (`UUID`, FK $\rightarrow$ `cpmk.id`, `ON DELETE CASCADE`, NOT NULL)
  * `kode_sub` (`VARCHAR(20)`, NOT NULL): Kode Sub-CPMK (misal: `Sub-CPMK-1.1`).
  * `deskripsi` (`TEXT`, NOT NULL): Indikator pencapaian spesifik per tahapan belajar.

* **`instrumen_penilaian`**
  * `id` (`UUID`, PK): Identitas unik komponen evaluasi.
  * `sub_cpmk_id` (`UUID`, FK $\rightarrow$ `sub_cpmk.id`, `ON DELETE CASCADE`, NOT NULL)
  * `jenis_instrumen` (`VARCHAR(50)`, NOT NULL): Bentuk asesmen (Tugas, Kuis, Praktikum, UTS, UAS).
  * `bobot_persentase` (`NUMERIC(5,2)`, NOT NULL): Bobot kontribusi instrumen terhadap penilaian (total akumulasi per MK wajib $100.00$).

* **`nilai_mahasiswa`**
  * `id` (`UUID`, PK): Identitas unik entri nilai.
  * `instrumen_id` (`UUID`, FK $\rightarrow$ `instrumen_penilaian.id`, `ON DELETE CASCADE`, NOT NULL)
  * `mahasiswa_id` (`UUID`, FK $\rightarrow$ `users.id`, `ON DELETE CASCADE`, NOT NULL)
  * `nilai_mentah` (`NUMERIC(5,2)`, NOT NULL): Skor aktual mahasiswa ($0.00 \le \text{nilai} \le 100.00$).
  * `waktu_input` (`TIMESTAMP`, DEFAULT `NOW()`): Waktu pencatatan nilai.

---

## 2. Logika Matematika & Agregasi Nilai OBE

Seluruh kalkulasi dilakukan di *Service Layer* FastAPI dengan alur agregasi *bottom-up*:

1. **Skor Terbobot Instrumen ($S_i$):**
   Untuk setiap instrumen penilaian ke-$i$ yang diambil mahasiswa:
   $$S_i = \text{nilai\_mentah}_i \times \left(\frac{\text{bobot\_persentase}_i}{100}\right)$$

2. **Persentase Ketercapaian Sub-CPMK ($P_{\text{sub}}$):**
   Jika satu Sub-CPMK dievaluasi oleh $n$ instrumen dengan total bobot $W_{\text{sub}} = \sum_{i=1}^{n} \text{bobot\_persentase}_i$:
   $$P_{\text{sub}} = \left(\frac{\sum_{i=1}^{n} S_i}{W_{\text{sub}}}\right) \times 100\%$$

3. **Persentase Ketercapaian CPMK ($P_{\text{cpmk}}$):**
   Rata-rata tertimbang dari seluruh Sub-CPMK yang bernaung di bawah CPMK terkait:
   $$P_{\text{cpmk}} = \left(\frac{\sum S_{\text{seluruh instrumen dalam CPMK}}}{\sum W_{\text{seluruh instrumen dalam CPMK}}}\right) \times 100\%$$

4. **Persentase Ketercapaian CPL ($P_{\text{cpl}}$):**
   Agregasi nilai dari seluruh CPMK/Mata Kuliah yang dipetakan ke CPL tertentu pada tabel `mk_cpl`. Data inilah yang dikembalikan sebagai *array* angka untuk me-render komponen **Radar Chart**.

---

## 3. Diagram Pemodelan Sistem (PlantUML Placeholders)

Tempelkan kode PlantUML yang sudah disusun pada masing-masing bagian di bawah ini sebagai dokumentasi visual arsitektur:

### 3.1. Entity Relationship Diagram (ERD)
```plantuml
[ISI KODE DISINI]
```

### 3.2. Class Diagram (Backend Domain Model)
```plantuml
[ISI KODE DISINI]
```

### 3.3. Sequence Diagram (Alur Utama Sistem)
```plantuml
[ISI KODE DISINI]
```

### 3.4. Use Case Diagram
```plantuml
[ISI KODE DISINI]
```

### 3.5. Activity Diagram (Kaprodi, Dosen, Mahasiswa)
```plantuml
[ISI KODE DISINI]
```