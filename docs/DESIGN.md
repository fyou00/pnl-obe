# DESIGN.md - Analisis dan Perancangan Sistem OBE PNL

**Institusi:** Politeknik Negeri Lhokseumawe (PNL). **Lingkup awal:** Program Studi Teknik Informatika. **Teknologi:** React, FastAPI, PostgreSQL.

Dokumen ini menjelaskan kebutuhan, alur bisnis, dan UI/UX. Aturan wajib aktor ada di `AGENTS.md`; skema fisik, integritas, agregasi, dan diagram ada di `SCHEMA.md`; progres ada di `PLAN.md`.

## 1. Tujuan dan Aktor

Aplikasi mengukur capaian pembelajaran berbasis OBE pada sistem **KRS paket yang ditetapkan kampus**. Aplikasi bukan sarana mahasiswa memilih KRS. Data diorganisasi per prodi, angkatan, versi kurikulum, periode akademik, kelas, dan pelaksanaan MK.

* **Admin/Kaprodi:** mengelola kurikulum, angkatan, kelas, status mahasiswa, paket MK dan pengampu, serta membuka/menutup periode dan melihat laporan. Tidak menginput nilai harian.
* **Dosen:** menyusun rancangan penilaian dan menginput nilai hanya pada kelas MK penugasannya. Satu kelas MK hanya satu dosen; tidak ada tim dosen.
* **Mahasiswa:** melihat nilai dan capaian pribadi dari kelas MK yang ditetapkan kampus, seluruhnya read-only.

Teknik Informatika menjadi satu-satunya prodi pada peluncuran awal; identitas dan relasi prodi tetap disimpan agar penambahan prodi kelak tidak memerlukan penggabungan data tanpa konteks.

## 2. Kebutuhan Sistem

### 2.1. Kebutuhan Fungsional

* Autentikasi JWT, logout, RBAC, dan pembatasan akses resource menurut prodi/penugasan/kepesertaan.
* Master prodi, pengguna, identitas MK, versi kurikulum, CPL, dan pemetaan MK–CPL per kurikulum.
* Paket MK per semester studi 1–8 pada versi kurikulum; satu angkatan menggunakan satu versi. Kurikulum Aktif bersifat tetap dan revisinya melalui versi baru.
* Periode tahun akademik + Ganjil/Genap, contoh 2026/2027 Ganjil. Tidak ada semester pendek.
* Penempatan mahasiswa per periode pada kelas reguler A–E atau kelas K untuk Cuti/Nonaktif. Status individual tetap dibedakan. K tidak menerima paket.
* Penerapan paket secara massal oleh Admin pada seluruh kelas reguler angkatan, beserta satu dosen per kelas MK; daftar MK semester sama bagi seluruh kelas angkatan. Tidak ada pengulangan MK.
* Satu rancangan bersama per dosen/kurikulum MK/periode, mencakup CPMK, pemetaan CPL, Sub-CPMK, instrumen dan bobot. Dosen berbeda boleh berbeda; nilai dan peserta tetap per kelas MK.
* Input nilai mentah 0–100 secara massal dengan validasi atomik. Instrumen: Tugas, Kuis, Praktikum, UTS, UAS.
* Grafik capaian aktual CPL/CPMK dan status kelengkapan; rekap kelas menyertakan jumlah mahasiswa lengkap/total. Tidak mengarang target capaian.
* Laporan serta ekspor CSV/PDF bagi Admin/Dosen sesuai cakupan akses. Mahasiswa hanya laporan pribadi read-only.
* Penguncian periode dan pembukaan kembali oleh Admin dengan alasan/audit; riwayat kurikulum, kelas, dan nilai tidak ditimpa periode baru.

### 2.2. Kebutuhan Non-Fungsional

* Respons API standar maksimal 500 ms; agregasi satu kelas di bawah 2 detik; minimal 200 pengguna bersamaan sebagai sasaran pengujian.
* JWT, Bcrypt, validasi Pydantic, ORM SQLAlchemy, transaksi, constraint database, dan rahasia melalui environment.
* **Desktop saja** untuk lingkup proyek ini; tidak membuat desain atau implementasi mobile. Grafik interaktif dan tabel mudah dibaca pada desktop.
* Backup harian otomatis, audit perubahan nilai dan penguncian, serta perlindungan penghapusan riwayat.

## 3. Alur Akademik dan Penilaian

### 3.1. Kurikulum dan Angkatan

Admin menyusun kurikulum Draft, memasukkan snapshot MK (nama/SKS/semester) dan CPL, lalu membebankan CPL ke MK. Setelah valid, kurikulum diaktifkan dan ditetapkan ke angkatan. Seluruh kelas dalam satu angkatan mengikuti paket semester yang sama. Perubahan kurikulum berikutnya memakai versi baru; data lama tetap dapat dilaporkan.

### 3.2. Periode dan Kelas

Admin membuka periode Ganjil/Genap, menentukan semester studi dan kelas A–E bagi angkatan, serta menempatkan mahasiswa. Angka pada TI-1A–TI-4E adalah tingkat tahun: semester 1–2 tingkat 1 hingga semester 7–8 tingkat 4. Contoh: angkatan 2024 pada semester studi 5 kelas C = TI-3C; angkatan 2026 semester studi 1 kelas A = TI-1A.

Cuti/Nonaktif ditempatkan di K, ditampilkan sebagai TI-K dengan angkatan/periode. Huruf kelas reguler biasanya tetap. Roster dan status dibuat per periode sehingga perpindahan tidak menimpa riwayat. Admin meninjau penempatan mahasiswa kembali dari K; aplikasi tidak otomatis menaikkan semester hanya berdasarkan tahun masuk.

### 3.3. Penerapan Paket

Admin memilih angkatan dan periode → memilih dosen untuk setiap MK di setiap kelas reguler → sistem mengambil paket dari kurikulum/semester studi → validasi roster aktif dan tanpa pengulangan → buat kelas MK, gunakan/buat rancangan bersama, dan catat peserta. Operasi atomik dan aman dijalankan ulang tanpa duplikasi; K dikecualikan. Detail integritas mengikuti SCHEMA.md §1.4.

Sebelum ada nilai, Admin dapat memperbaiki penempatan/penugasan secara konsisten. Setelah ada nilai, perubahan struktural atas peserta/kelas terkait ditolak; riwayat tidak dipindah atau dihapus otomatis. Penempatan berbeda dicatat pada periode berikutnya.

### 3.4. Rancangan Dosen dan Nilai

Dosen memilih periode dan kelas MK penugasannya → sistem menampilkan CPL yang dibebankan pada kurikulum MK → dosen menyusun CPMK/pemetaan CPL/Sub-CPMK/instrumen/bobot → lengkapi semua pemetaan dan bobot 100% → input nilai peserta kelas → sistem menghitung capaian.

Jika dosen X mengajar MK yang sama pada A dan B dalam periode/kurikulum sama, kedua kelas memakai satu rancangan. Antarmuka menyebutkan kelas-kelas pengguna dan bahwa perubahan berlaku untuk semua kelas tersebut. Dosen Y untuk MK sama pada C dapat memiliki rancangan berbeda. Nilai dan rekap A/B/C tetap terpisah.

Rancangan periode sebelumnya boleh disalin ke periode baru pada kurikulum MK yang sama ke rancangan tujuan kosong hasil penugasan Admin, sebagai draft tanpa peserta/nilai. Tujuan yang sudah berisi tidak ditimpa. Sesudah nilai pertama ada di salah satu kelas terkait, struktur rancangan bersama dibekukan; dosen masih dapat melengkapi/mengoreksi nilai selama periode terbuka.

### 3.5. Mahasiswa dan Penutupan

Mahasiswa memilih periode → **Tampilkan mata kuliah** dari paket yang telah ditetapkan → melihat rincian nilai serta grafik capaian pribadi. Dropdown hanya filter; tidak ada tindakan ambil/tambah/batalkan KRS. Periode Cuti/Nonaktif menampilkan status akademik dan tidak adanya paket, bukan nilai nol.

Admin menutup periode → semua perubahan akademik dan nilai periode terkunci → laporan historis tetap tersedia. Pembukaan kembali memerlukan alasan dan audit. Dosen dapat mengoreksi nilai pada periode yang dibuka kembali; struktur rancangan yang sudah memiliki nilai tetap dibekukan. Periode boleh ditutup walaupun nilai belum lengkap; status kelengkapan tidak berubah menjadi nol atau lengkap.

## 4. Arsitektur Data

`SCHEMA.md` §1 menetapkan 21 tabel beserta PK/FK/UNIQUE/CHECK dan kebijakan hapus. Struktur inti:

* `kurikulum` → `kurikulum_mk`/CPL/pemetaan; `angkatan` memilih versi kurikulum.
* `periode_akademik` → `kelas_periode` dan `mahasiswa_periode` untuk kelas/status historis.
* `kelas_mk` menghubungkan kelas, MK kurikulum, dan satu `rancangan_penilaian` milik dosen; `peserta_kelas_mk` menyimpan peserta yang ditetapkan Admin.
* Rancangan bersama → CPMK → Sub-CPMK → instrumen; CPMK terhubung ke CPL melalui `cpmk_cpl`.
* Nilai mengacu instrumen dan peserta kelas MK, tidak hanya instrumen/mahasiswa tanpa konteks kelas.

Skema lama `pengampu_krs(user_id, mk_id)` digantikan; jangan diimplementasikan. Kalkulasi hanya di service FastAPI menggunakan Decimal sesuai SCHEMA.md §2. Antarmuka mengirim konteks periode/kelas dan menampilkan angka/status dari backend.

## 5. Blueprint UI/UX Desktop

Palet netral dengan komponen konsisten. Artefak saat ini `design/pnl-obe.figcraft` masih desain statis, bukan aplikasi berjalan.

1. **Dashboard:** sidebar kiri dengan profil paling bawah; topbar breadcrumb, toggle dark mode, jam digital/tanggal WIB; dropdown konteks di samping judul. Kartu ringkasan, tabel dan grafik menampilkan konteks periode secara jelas. Toggle/jam dalam artefak masih contoh statis.
2. **Master dan kurikulum (Admin):** tabel CPL berkode/kategori/deskripsi, form versi kurikulum dan MK paket. Kurikulum aktif/arsip memiliki indikator read-only dan tindakan membuat versi baru.
3. **Matriks pembebanan (Admin):** pilih versi kurikulum/MK, tautkan CPL dengan checkbox hanya pada Draft. Penggunaan lintas versi ditolak.
4. **Akademik (Admin):** angkatan, periode, kelas A–E/K, status mahasiswa, penugasan satu dosen per kelas MK, dan penerapan paket massal. Tidak ada pengisian KRS mandiri mahasiswa.
5. **Rancangan (Dosen):** accordion CPMK/Sub-CPMK, pilihan CPL yang dibebankan, instrumen dan bobot. Tampilkan semua kelas pengguna rancangan dan alasan read-only jika struktur dibekukan/periode ditutup.
6. **Input nilai (Dosen):** grid peserta kelas MK × instrumen rancangan. Filter periode/kelas wajib jelas; input 0–100, simpan bulk atomik, tampilkan kesalahan tanpa menyimpan sebagian.
7. **Capaian (Dosen/Mahasiswa):** grafik aktual CPL/CPMK, status kesiapan/kelengkapan, dan lengkap/total pada rekap kelas. Nilai belum lengkap ditampilkan “—”, bukan nol; tanpa garis target buatan.

Catatan implementasi frontend untuk grid nilai: saat sel berisi teks nonnumerik atau skor di luar rentang 0–100, tampilkan garis tepi merah dan pesan “Masukkan nilai 0–100” tepat di bawah input. Hubungkan pesan ke input dengan `aria-describedby` dan tandai input dengan `aria-invalid`. Pertahankan isian, tahan pengiriman selama ada kesalahan, dan bersihkan peringatan ketika skor diperbaiki. Sel kosong berarti belum diinput; angka 0 adalah skor sah. Validasi dan umpan balik berlangsung di halaman yang sama. API tetap memeriksa skor dan integritas seluruh kiriman sesuai SCHEMA.md.

Rincian nilai mahasiswa memakai satu tampilan. Setiap baris instrumen menunjukkan status “Sudah dinilai” atau “Belum diinput”. Tampilkan capaian setiap CPMK yang datanya lengkap dan status “Belum lengkap” pada CPMK yang masih menunggu nilai wajib.

Pada dashboard Dosen/Mahasiswa, dropdown **“Tampilkan mata kuliah”** dibatasi penugasan/kepesertaan dalam periode yang dilihat dan menampilkan identitas kelas bila diperlukan. Ringkasan/list keseluruhan dan panel yang mengikuti filter diberi label konteks berbeda agar tidak menyesatkan. Desain layar akademik tambahan dan penyesuaian periode pada artefak Figcraft adalah pekerjaan selanjutnya, belum dibuat oleh revisi dokumentasi ini. Tidak menambah RPS, login, landing page, atau mobile pada tugas desain dashboard.

## 6. Artefak dan Validasi

ERD 21 tabel, class diagram inti, sequence paket–nilai, use case, activity flow, dan skenario penerimaan terpusat di `SCHEMA.md` §3–4. Sebelum migrasi, periksa semua relasi terhadap pemisahan kurikulum/periode/kelas/rancangan bersama. Implementasi berikutnya wajib menguji isolasi akses, paket K, tanpa pengulangan, riwayat, bobot/pemetaan, penguncian serentak, dan akurasi capaian.

## 7. Status Implementasi Backend Awal

Fondasi di `backend/` mencakup 21 model, migrasi awal Alembic, konfigurasi PostgreSQL, seed, health/readiness, JWT/Bcrypt, profil dan logout (mencabut seluruh sesi pengguna). Endpoint baca kelas MK memeriksa prodi, dosen penugasan, atau peserta mahasiswa; daftar peserta hanya untuk Admin/Dosen terkait. Tidak ada endpoint pengisian KRS mahasiswa. API tulis kurikulum/paket/periode/rancangan/nilai, penguncian dan perhitungan capaian masih fase berikutnya. Rincian menjalankan dan menguji tersedia di `backend/README.md`.
