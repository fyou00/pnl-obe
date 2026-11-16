# SCHEMA.md - Arsitektur Data, Relasi Database, dan Logika Kalkulasi OBE

Dokumen ini berfungsi sebagai *single source of truth* teknis mengenai struktur basis data PostgreSQL, pemodelan sistem, dan rumus agregasi nilai *Outcome-Based Education* (OBE) pada proyek Politeknik Negeri Lhokseumawe (PNL).

---

## 1. Spesifikasi Tabel Database (PostgreSQL Physical Schema)

Entitas utama memakai `id UUID` sebagai PK. Tabel junction `mk_cpl`, `cpmk_cpl`, dan `pengampu_krs` memakai PK gabungan dari dua FK UUID.

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

* **`cpmk_cpl`**: pemetaan M:N CPMK ke CPL.
  * `cpmk_id` (`UUID`, PK, FK → `cpmk.id`, `ON DELETE CASCADE`).
  * `cpl_id` (`UUID`, PK, FK → `master_cpl.id`, `ON DELETE RESTRICT`).
  * Service memvalidasi bahwa CPL ada pada `mk_cpl` untuk MK milik CPMK. Penghapusan pemetaan MK–CPL ditolak bila masih dipakai CPMK; perubahan diproses dalam transaksi.

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

### 1.4. Integritas dan validasi layanan
* `UNIQUE(instrumen_id, mahasiswa_id)` untuk nilai; bulk upsert harus atomik.
* `UNIQUE(prodi_id, kode_mk)`; nilai dan bobot memakai `Decimal`, CHECK nilai 0–100 dan bobot > 0 hingga 100.
* Status pengampu harus sesuai role pengguna. Nilai hanya untuk mahasiswa peserta MK; akses dosen ditelusuri dari instrumen/Sub-CPMK/CPMK hingga MK yang diampu.
* Draft boleh belum lengkap (termasuk pemetaan CPMK), tetapi input nilai dan laporan capaian mensyaratkan setiap CPMK terpetakan serta total bobot MK 100%. Penambahan instrumen bertahap tidak harus langsung 100%, tetapi tidak boleh melebihi 100%.
* CPL tanpa prodi hanya kategori S/KU; CPL prodi yang dipetakan harus sesuai prodi MK.

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
   Untuk mahasiswa dan CPL tertentu, ambil instrumen unik dari CPMK yang ditautkan melalui `cpmk_cpl`, hanya pada MK yang diambil mahasiswa. Capaian numerik 0–100 = `sum(nilai_mentah × bobot_persentase) / sum(bobot_persentase)`. Dalam satu MK gunakan instrumen MK itu; lintas MK gabungkan pembilang dan penyebut, tanpa bobot SKS tambahan. Satu instrumen dihitung sekali per CPL, dan boleh berkontribusi pada beberapa CPL tanpa dibagi.
   Nilai belum diinput bukan nol: hasil belum lengkap diberi `null` dan status belum lengkap; penyebut nol menghasilkan `null`. Rekap kelas adalah rata-rata capaian mahasiswa yang lengkap, disertai jumlah mahasiswa lengkap/total. Hitung dengan Decimal, bulatkan dua desimal hanya di hasil akhir. Contoh nilai 80 berbobot 20 dan nilai 60 berbobot 30 menghasilkan capaian 68.00. Label CPL/CPMK dan status kelengkapan dikirim bersama angka ke chart; target capaian belum dikonfigurasi, sehingga jangan mengarang nilai target.

---

## 3. Diagram Pemodelan Sistem

Diagram berikut mendokumentasikan skema dan alur sistem; nama endpoint merupakan rancangan, belum API yang diimplementasikan.

### 3.1. Entity Relationship Diagram (ERD)
```plantuml
@startuml
' Konfigurasi tampilan ERD
hide circle
skinparam linetype ortho
skinparam EntityBackgroundColor #F8F9FA
skinparam EntityBorderColor #343A40
skinparam EntityHeaderBackgroundColor #E9ECEF

' Definisi Makro untuk Primary dan Foreign Key (Tanpa OpenIconic)
!define PK(x) <b><color:#B8860B>[PK]</color> x</b>
!define FK(x) <color:#4682B4>[FK]</color> x

entity "users" {
  PK(id) : UUID
  --
  nim_nidn : VARCHAR(20)
  nama : VARCHAR(100)
  email : VARCHAR(100)
  role : VARCHAR(20)
  password_hash : VARCHAR(255)
}

entity "prodi" {
  PK(id) : UUID
  --
  nama_prodi : VARCHAR(100)
  jenjang : VARCHAR(10)
}

entity "master_cpl" {
  PK(id) : UUID
  --
  FK(prodi_id) : UUID <<nullable>>
  kode_cpl : VARCHAR(10)
  kategori : VARCHAR(5)
  deskripsi : TEXT
}

entity "mata_kuliah" {
  PK(id) : UUID
  --
  FK(prodi_id) : UUID
  kode_mk : VARCHAR(20)
  nama_mk : VARCHAR(100)
  sks : INTEGER
  semester : INTEGER
  deskripsi : TEXT
}

entity "mk_cpl" {
  PK(FK(mk_id)) : UUID
  PK(FK(cpl_id)) : UUID
  --
  urutan_rps : INTEGER
}

entity "cpmk" {
  PK(id) : UUID
  --
  FK(mk_id) : UUID
  kode_cpmk : VARCHAR(20)
  deskripsi : TEXT
}

entity "sub_cpmk" {
  PK(id) : UUID
  --
  FK(cpmk_id) : UUID
  kode_sub : VARCHAR(20)
  deskripsi : TEXT
}

entity "instrumen_penilaian" {
  PK(id) : UUID
  --
  FK(sub_cpmk_id) : UUID
  jenis_instrumen : VARCHAR(50)
  bobot_persentase : NUMERIC(5,2)
}

entity "nilai_mahasiswa" {
  PK(id) : UUID
  --
  FK(instrumen_id) : UUID
  FK(mahasiswa_id) : UUID
  nilai_mentah : NUMERIC(5,2)
  waktu_input : TIMESTAMP
}

entity "pengampu_krs" {
  PK(FK(user_id)) : UUID
  PK(FK(mk_id)) : UUID
  --
  status : VARCHAR(20)
}

entity "cpmk_cpl" {
  PK(FK(cpmk_id)) : UUID
  PK(FK(cpl_id)) : UUID
}
cpmk ||--o{ cpmk_cpl
master_cpl ||--o{ cpmk_cpl

' Relasi
prodi |o--o{ master_cpl : "1:N"
prodi ||--o{ mata_kuliah : "1:N"

mata_kuliah ||--o{ mk_cpl : "1:N"
master_cpl ||--o{ mk_cpl : "1:N"

mata_kuliah ||--o{ cpmk : "1:N"
cpmk ||--o{ sub_cpmk : "1:N"

sub_cpmk ||--o{ instrumen_penilaian : "1:N"
instrumen_penilaian ||--o{ nilai_mahasiswa : "1:N"
users ||--o{ nilai_mahasiswa : "1:N"

users ||--o{ pengampu_krs : "1:N"
mata_kuliah ||--o{ pengampu_krs : "1:N"

@enduml
```

### 3.2. Class Diagram (Backend Domain Model)
```plantuml
@startuml
skinparam classAttributeIconSize 0
skinparam nodesep 50
skinparam ranksep 50

class User {
  + id : UUID
  + nim_nidn : String
  + nama : String
  + email : String
  + role : Enum(Admin, Dosen, Mahasiswa)
  + password_hash : String
}

class Prodi {
  + id : UUID
  + nama_prodi : String
  + jenjang : String
}

class MasterCPL {
  + id : UUID
  + kode_cpl : String
  + kategori : Enum(S, KU, P, KK)
  + deskripsi : Text
}

class MataKuliah {
  + id : UUID
  + kode_mk : String
  + nama_mk : String
  + sks : Integer
  + semester : Integer
  + deskripsi : Text
}

class MatriksPembebanan {
  + mk_id : UUID
  + cpl_id : UUID
  + urutan_rps : Integer
}

class CPMK {
  + id : UUID
  + kode_cpmk : String
  + deskripsi : Text
}

class SubCPMK {
  + id : UUID
  + kode_sub : String
  + deskripsi : Text
}

class InstrumenPenilaian {
  + id : UUID
  + jenis_instrumen : String
  + bobot_persentase : Decimal
}

class NilaiMahasiswa {
  + id : UUID
  + nilai_mentah : Decimal
  + waktu_input : DateTime
}

' Relasi
Prodi "0..1" -- "*" MasterCPL : memiliki >
Prodi "1" -- "*" MataKuliah : menaungi >

MataKuliah "1" -- "*" MatriksPembebanan : dibebankan >
MasterCPL "1" -- "*" MatriksPembebanan : memuat <

MataKuliah "1" *-- "*" CPMK : memiliki >
CPMK "1" *-- "*" SubCPMK : dipecah menjadi >

SubCPMK "1" -- "*" InstrumenPenilaian : dievaluasi oleh >
InstrumenPenilaian "1" -- "*" NilaiMahasiswa : menghasilkan >
User "1" -- "*" NilaiMahasiswa : mendapat >

class PengampuKRS {
  + user_id : UUID
  + mk_id : UUID
  + status : String
}
class CPMKCPL {
  + cpmk_id : UUID
  + cpl_id : UUID
}
User "1" -- "*" PengampuKRS
MataKuliah "1" -- "*" PengampuKRS
CPMK "1" -- "*" CPMKCPL
MasterCPL "1" -- "*" CPMKCPL
@enduml
```

### 3.3. Sequence Diagram (Alur Utama Sistem)
```plantuml
@startuml
autonumber
skinparam maxMessageSize 150
skinparam ParticipantPadding 20
skinparam BoxPadding 10

actor "Dosen" as dosen
box "Frontend Layer" #LightCyan
participant "Frontend\n(React.js)" as react
end box
box "Backend Layer" #LightYellow
participant "API Service\n(FastAPI)" as api
end box
box "Data Layer" #LightGreen
database "Database\n(PostgreSQL)" as db
end box

note over api
Pada SETIAP request: Depends JWT, role Dosen, dan MK di pengampu_krs.
Telusuri resource anak ke MK; validasi payload Pydantic.
end note
alt Token tidak valid / akses ditolak
  api --> react : 401 / 403; hentikan request tanpa perubahan
else Payload atau aturan bisnis tidak valid
  api --> react : 422; hentikan request tanpa perubahan
end
note over api : Cabang 401/403/422 mengakhiri request; alur berikut hanya untuk request valid.

== Fase 1: Penyusunan CPMK & Sub-CPMK ==
dosen -> react : Membuka menu Mata Kuliah
react -> api : GET /api/v1/mk/{mk_id}/cpl
api -> db : JOIN master_cpl dengan mk_cpl WHERE mk_id = {mk_id}
db --> api : Data CPL dari Kaprodi
api --> react : Response JSON (Data CPL)
react --> dosen : Tampilkan list CPL yang dibebankan

dosen -> react : Input rumusan CPMK baru
react -> api : POST /api/v1/cpmk (Payload JSON)
api -> api : Validasi schema menggunakan Pydantic
api -> db : Transaksi INSERT cpmk dan cpmk_cpl (CPL harus ada di mk_cpl)
db --> api : Success (Return ID)
api --> react : 201 Created
react --> dosen : Update UI (CPMK ditambahkan)

dosen -> react : Input rumusan Sub-CPMK
react -> api : POST /api/v1/sub-cpmk (dengan cpmk_id)
api -> db : INSERT INTO sub_cpmk
db --> api : Success
api --> react : 201 Created
react --> dosen : Update UI (Sub-CPMK ditambahkan)

== Fase 2: Penetapan Penilaian & Input Nilai ==
dosen -> react : Buat Instrumen (misal: Tugas 1)\n& tautkan ke Sub-CPMK
react -> api : POST /api/v1/instrumen
api -> db : INSERT INTO instrumen_penilaian
db --> api : Success
api --> react : 201 Created
react --> dosen : Form instrumen tersimpan

dosen -> react : Input nilai mahasiswa pada instrumen
react -> api : PUT /api/v1/nilai (Bulk Upsert)
api -> api : Validasi peserta MK, skor 0–100, pemetaan dan bobot 100%
api -> db : Transaksi UPSERT nilai_mahasiswa; rollback seluruh batch jika gagal
db --> api : Success
api --> react : 200 OK
react --> dosen : Notifikasi Nilai Tersimpan

== Fase 3: Kalkulasi & Visualisasi OBE ==
dosen -> react : Buka tab "Visualisasi Capaian"
react -> api : GET /api/v1/capaian/mk/{mk_id}
api -> db : Query JOIN nilai_mahasiswa, instrumen, sub_cpmk, cpmk
db --> api : Raw data nilai
api -> api : Kalkulasi agregat persentase OBE (Logic Service)
api --> react : Response JSON (Data agregat jaring laba-laba/radar)
react --> dosen : Render komponen Chart (Recharts/Chart.js)
@enduml
```

### 3.4. Use Case Diagram
```plantuml
@startuml
left to right direction
skinparam packageStyle rectangle

actor "Pengguna" as User
actor "Dosen" as Dosen
actor "Kaprodi\n(Admin)" as Kaprodi
actor "Mahasiswa" as Mahasiswa

User <|-- Dosen
User <|-- Kaprodi
User <|-- Mahasiswa

rectangle "Aplikasi Pengukuran CPMK PNL" {
  usecase "Tetapkan Pengampu dan Peserta MK" as UC_KRS
  usecase "Lihat Rincian Nilai Pribadi" as UC_Nilai
  usecase "Login" as UC1
  usecase "Logout" as UC2

  usecase "Kelola Data Master\n(Prodi, CPL, MK, Pengguna)" as UC3
  usecase "Petakan CPL ke Mata Kuliah\n(Matriks Pembebanan)" as UC_Map
  usecase "Susun CPMK, Pemetaan CPL & Sub-CPMK" as UC4
  usecase "Tentukan Komponen Penilaian\nberdasarkan Sub-CPMK" as UC5
  usecase "Input Nilai Mahasiswa\n(Tugas, Kuis, Praktikum, Ujian)" as UC6
  usecase "Lihat Visualisasi Capaian CPL/CPMK" as UC7
  usecase "Buat Laporan Asesmen OBE" as UC8
  usecase "Ekspor Data ke CSV/PDF" as UC9
  usecase "Hitung Persentase Capaian\n(otomatis)" as UC10
}

User --> UC1
User --> UC2

Kaprodi --> UC_KRS
Kaprodi --> UC3
Kaprodi --> UC_Map
Kaprodi --> UC8
Kaprodi --> UC9

Dosen --> UC4
Dosen --> UC5
Dosen --> UC6
Dosen --> UC7
Dosen --> UC8
Dosen --> UC9

Mahasiswa --> UC7
Mahasiswa --> UC_Nilai

UC7 .> UC10 : <<include>>
UC8 .> UC10 : <<include>>
UC9 .> UC10 : <<include>>
@enduml
```

### 3.5. Activity Diagram (Kaprodi, Dosen, Mahasiswa)
```plantuml
@startuml
skinparam activityBorderColor #343A40
skinparam activityBackgroundColor #F8F9FA
skinparam swimlaneBorderColor #343A40

|Kaprodi (Admin)|
start
:Membuka sistem;
:Memasukkan daftar Mata Kuliah;
:Memasukkan daftar target lulusan (CPL);
:Menentukan Mata Kuliah mana\nyang menanggung target tersebut;

|Sistem|
:Menyimpan aturan kurikulum;

|Kaprodi (Admin)|
:Menetapkan dosen pengampu dan peserta MK;

|Kaprodi (Admin)|
:Selesai mengatur kurikulum;
stop
@enduml

@startuml
skinparam activityBorderColor #343A40
skinparam activityBackgroundColor #F8F9FA
skinparam swimlaneBorderColor #343A40

|Dosen|
start
:Memilih mata kuliah yang diajar;

|Sistem|
:Menampilkan target lulusan\nyang diminta oleh Kaprodi;

|Dosen|
:Menyusun CPMK dan memilih CPL yang dibebankan;
:Menyusun Sub-CPMK;
:Membuat daftar tugas/ujian\nbeserta bobot nilainya;
:Memasukkan nilai tugas mahasiswa;

|Sistem|
:Validasi pengampuan, peserta, pemetaan, bobot 100% dan skor;
if (Valid?) then (ya)
:Simpan nilai dalam transaksi;
else (tidak)
:Tolak perubahan dan tampilkan kesalahan;
stop
endif

|Sistem|
:Menghitung persentase keberhasilan\nmahasiswa secara otomatis;

|Dosen|
:Melihat laporan capaian belajar kelas;
:Ekspor CSV/PDF untuk MK yang diampu;
stop
@enduml

@startuml
skinparam activityBorderColor #343A40
skinparam activityBackgroundColor #F8F9FA
skinparam swimlaneBorderColor #343A40

|Mahasiswa|
start
:Membuka sistem;
:Memilih mata kuliah yang diambil;

|Sistem|
:Validasi mahasiswa terdaftar pada MK;
:Ambil hanya nilai mahasiswa yang sedang login;
:Menggambar grafik capaian pribadi;

|Mahasiswa|
:Melihat rincian nilai tugas dan ujian;
:Melihat grafik seberapa jauh\ntarget belajar telah tercapai;
stop
@enduml
```
