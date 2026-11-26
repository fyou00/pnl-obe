# PNL OBE Backend

Fondasi FastAPI, SQLAlchemy 2, Pydantic v2, PostgreSQL 15+, Alembic, JWT (HS256), dan Bcrypt. Python 3.11+; versi dependensi yang diuji tersimpan di `requirements.lock`. Skema 23 tabel (revisi `20261126_0002`) mengikuti `../SCHEMA.md`.

## Instalasi

Jalankan dari folder `backend/`:

```sh
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.lock
python -m pip install --no-deps -e .
```

`requirements.lock` mencakup dependensi aplikasi dan pengujian. Untuk menjalankan server production, dependensi aplikasi dapat dipasang dengan `python -m pip install .`; pgserver tidak menjadi dependensi aplikasi.

## Database dan environment

Gunakan salah satu cara berikut. Aplikasi tidak membuat tabel saat startup; migrasi Alembic wajib dijalankan.

### PostgreSQL yang tersedia / Docker

Salin `.env.example` ke `.env`, isi `DATABASE_URL`, `JWT_SECRET_KEY`, dan kredensial seed. Buat JWT secret acak dengan `python -c 'import secrets; print(secrets.token_urlsafe(48))'`. Jangan menggunakan kredensial contoh sebagai kredensial produksi.

Untuk Docker, isi juga `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, dan opsional `POSTGRES_PORT`; samakan dengan DATABASE_URL. Jalankan:

```sh
docker compose up -d --wait
```

Container database hanya dipublikasikan pada localhost. PostgreSQL 15+ eksternal juga didukung melalui DATABASE_URL berdriver `postgresql+psycopg`.

### Alternatif development lokal tanpa Docker (macOS/Linux)

```sh
python -m pip install '.[local-postgres]'
python scripts/dev_postgres.py --init-env
```

Biarkan terminal tersebut berjalan. Server memakai PostgreSQL sungguhan melalui Unix socket, autentikasi lokal trust, dan data di `.local/postgres`; ini hanya untuk development. Opsi `--init-env` membuat `.env` berisi JWT secret serta password akun lokal yang acak dengan izin 0600, dan tidak menimpa file yang sudah ada. Lihat kredensial langsung di `.env`; script tidak mencetaknya. Untuk menjalankan ulang server, gunakan `python scripts/dev_postgres.py` tanpa menghapus datanya. Ctrl+C menghentikan server dengan data tetap tersimpan. Tool lokal opsional ini tidak diperlukan bila PostgreSQL sudah tersedia.

## Migrasi, seed, dan server

Di terminal lain dengan virtualenv aktif:

```sh
alembic upgrade head
alembic check
python -m app.services.seed
uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8000 --reload
```

Seed default membuat prodi dan Admin dari `.env`. `python -m app.services.seed --demo` juga membuat akun Dosen/Mahasiswa contoh, angkatan, dan kurikulum Draft. Semua kredensial harus diberikan di environment/.env; tidak ada password bawaan. Seed idempoten, tidak mereset password akun yang sudah ada, dan rollback seluruh batch jika ada konflik. Data demo belum menyusun paket/kelas/perkuliahan; susun melalui endpoint akademik dan penerapan paket Admin.

`alembic downgrade base` hanya untuk database development kosong yang boleh dihapus. Jangan menjalankannya pada database berisi riwayat akademik. Startup server tidak menjalankan migrasi atau seed secara otomatis.

### Seed kurikulum, deskripsi mata kuliah, CPL, dan matriks MK–CPL (JSON)

Data Kurikulum OBE 2024 Teknik Informatika (`TI-2024`, berstatus `Draft`) tersedia dalam berkas JSON berikut:

- `seeds/kurikulum_ti_2024_mata_kuliah.json`: 61 mata kuliah (144 SKS) dari Bab 7 Subbab 7.2 *Deskripsi Mata Kuliah* (hlm. 64–80).
- `seeds/kurikulum_ti_2024_cpl.json`: 12 CPL (`CPL-01`–`CPL-12`) dari Bab 3 Subbab 3.4 Tabel 3.5 *Capaian Pembelajaran Lulusan (CPL)* (hlm. 32–33).
- `seeds/kurikulum_ti_2024_profil_lulusan.json`: 4 Profil Lulusan (`PL-01`–`PL-04`) beserta 30 relasi matriks PL–CPL (`pl_cpl`) dari Bab 3 Tabel 3.3 & 3.6 serta Bab 6 Tabel 6.2.
- `seeds/kurikulum_ti_2024_mk_cpl.json`: draft pemetaan awal 61 MK ke 12 CPL (118 relasi `mk_cpl`) berbasis Tabel 3.5, 6.1, dan 7.9 agar `TI-2024` memenuhi syarat aktivasi (`POST /api/v1/kurikulum/{id}/aktifkan`).

Seed kurikulum dapat dijalankan bersamaan dengan seed awal (flag `--kurikulum-file` dapat diulang) atau secara terpisah:

```sh
python -m app.services.seed --kurikulum-file seeds/kurikulum_ti_2024_mata_kuliah.json --kurikulum-file seeds/kurikulum_ti_2024_cpl.json --kurikulum-file seeds/kurikulum_ti_2024_profil_lulusan.json --kurikulum-file seeds/kurikulum_ti_2024_mk_cpl.json
python -m app.services.seed_curriculum seeds/kurikulum_ti_2024_mata_kuliah.json seeds/kurikulum_ti_2024_cpl.json seeds/kurikulum_ti_2024_profil_lulusan.json seeds/kurikulum_ti_2024_mk_cpl.json
python -m app.services.seed_curriculum seeds/kurikulum_ti_2024_mk_cpl.json
```

Keduanya bersifat idempoten, tidak menimpa suntingan manual (MK, `bidang_kerja` PL, dan `urutan_rps` hanya mengisi `NULL` pada kurikulum `Draft`; CPL/PL yang sudah ada dipertahankan), dan membatalkan seluruh transaksi bila terjadi konflik data atau upaya penambahan pada kurikulum non-`Draft`.

### Seed demo operasional (JSON)

`seeds/demo_operasional_ti_2024.json` mengisi data operasional realistis di atas `TI-2024` (mengaktifkan `TI-2024`, 3 Dosen, 2 angkatan `2024`/`2025`, 9 Mahasiswa termasuk status `Cuti`/`Nonaktif` di `TI-K`, periode `2025/2026 Genap` `Ditutup` & `2026/2027 Ganjil` `Dibuka`, rancangan bersama/terpisah, draf belum lengkap `TI-24502`, nilai `0.00` sah, serta sel kosong/`NULL`). Tidak ada password di file JSON; seluruh akun memakai `SEED_DOSEN_PASSWORD` / `SEED_MAHASISWA_PASSWORD` dari `backend/.env`:

```sh
python -m app.services.seed --demo \
  --kurikulum-file seeds/kurikulum_ti_2024_mata_kuliah.json \
  --kurikulum-file seeds/kurikulum_ti_2024_cpl.json \
  --kurikulum-file seeds/kurikulum_ti_2024_profil_lulusan.json \
  --kurikulum-file seeds/kurikulum_ti_2024_mk_cpl.json \
  --demo-file seeds/demo_operasional_ti_2024.json

# Atau terpisah setelah seed awal + kurikulum:
python -m app.services.seed_demo seeds/demo_operasional_ti_2024.json
```

Email demo: Dosen (`dosen.rpl@demo.pnl.ac.id`, `dosen.jarkom@demo.pnl.ac.id`, `dosen.ai@demo.pnl.ac.id`) dan Mahasiswa (`mhs.a1@demo.pnl.ac.id`..`mhs.a3@demo.pnl.ac.id`, `mhs.b1@demo.pnl.ac.id`..`mhs.b3@demo.pnl.ac.id`, `mhs.cuti@demo.pnl.ac.id`, `mhs.nonaktif@demo.pnl.ac.id`, `mhs.c1@demo.pnl.ac.id`).

## Endpoint tersedia

| Method | Path | Fungsi |
| --- | --- | --- |
| GET | `/health` | Liveness aplikasi tanpa koneksi database. |
| GET | `/ready` | Koneksi database dan revisi Alembic sesuai; 503 bila belum siap. |
| POST | `/api/v1/auth/token` | Form OAuth2: `username` = email, `password` = password akun; respons access token. |
| GET | `/api/v1/auth/me` | Profil pengguna JWT yang masih aktif; tidak memuat hash/password. |
| POST | `/api/v1/auth/logout` | Cabut seluruh access token pengguna, termasuk sesi browser lain; 204. |
| POST | `/api/v1/auth/ganti-password` | Perbarui kata sandi akun sendiri (wajib sandi lama; sandi baru 12–72 byte UTF-8); menerbitkan token baru dan mencabut sesi lain. |
| GET | `/api/v1/kelas-mk?periode_id=<uuid>` | Daftar kelas sesuai prodi/penugasan/kepesertaan; `offset` ≥ 0, `limit` 1–100. |
| GET | `/api/v1/kelas-mk/<uuid>` | Detail kelas sesuai cakupan akses; 404 juga untuk resource di luar cakupan. |
| GET | `/api/v1/kelas-mk/<uuid>/peserta` | ID peserta untuk Admin/Dosen terkait; Mahasiswa ditolak. |

Pemeriksaan HTTP lokal setelah seed demo/server berjalan: `python scripts/smoke_local.py`. Perintah ini login/logout tiga akun demo tanpa mencetak token/password.

Swagger tersedia di `/docs`. Gunakan tombol Authorize dan isi email pada kolom username. Tidak ada registrasi publik atau refresh token. Access token berlaku 30 menit secara default. JWT memvalidasi signature, expiry, issuer, audience, dan versi token. Role, status akun, dan status prodi dibaca dari database pada setiap request; perubahan role berlaku tanpa menerbitkan JWT baru. `users.token_version` mendukung pencabutan token secara persisten tanpa tabel baru.

Modul Admin, perencanaan Dosen, input nilai dan capaian tersedia pada bagian berikut. KRS ditetapkan kampus melalui paket; tidak ada endpoint KRS mandiri. Layanan tulis memakai validasi lintas relasi, penguncian periode/rancangan, dan audit sesuai SCHEMA.md; constraint database tetap menjadi pelindung tambahan.

## Pengujian

```sh
ruff check .
ruff format --check .
pytest -q
```

Tes memakai PostgreSQL asli: pasang extra `.[local-postgres]` atau tentukan `TEST_DATABASE_URL` ke server PostgreSQL development yang mengizinkan CREATE/DROP DATABASE. Setiap tes membuat database baru bernama `obe_test_<uuid>` dan hanya menghapus database buatannya sendiri. Tidak memakai database aplikasi atau SQLite. Fixture menjalankan migrasi, bukan `metadata.create_all`.

Cakupan tahap fondasi: migrasi upgrade/downgrade/upgrade dan perbandingan metadata, CHECK/FK/UNIQUE/RESTRICT, seed idempoten/rollback, health/readiness, autentikasi tiga peran, JWT invalid/expired, logout/revokasi, status akun/prodi, perubahan role, serta isolasi kelas Dosen/Mahasiswa/prodi. Uji alur paket, input nilai, penguncian, perhitungan capaian dan concurrency layanan belum dinyatakan selesai sampai modul terkait diimplementasikan.

## Modul Admin: master MK dan kurikulum

Semua rute berikut memakai prefix `/api/v1` dan memerlukan akun **Admin**. Prodi ditentukan dari akun login; field `prodi_id`, status kurikulum, dan parent ID tidak diterima sebagai input bebas. Resource di luar prodi atau parent yang salah menghasilkan 404. Dosen/Mahasiswa mendapat 403. Tidak ada migrasi tambahan untuk modul ini.

| Resource | Method/path relatif terhadap /api/v1 |
| --- | --- |
| Master MK | GET/POST `/mata-kuliah`; GET/PATCH/DELETE `/mata-kuliah/{mk_id}` |
| Versi kurikulum | GET/POST `/kurikulum`; GET/PATCH/DELETE `/kurikulum/{kurikulum_id}` |
| MK paket | GET/POST `/kurikulum/{kurikulum_id}/mata-kuliah`; GET/PATCH/DELETE `.../mata-kuliah/{kurikulum_mk_id}` |
| CPL per versi | GET/POST `/kurikulum/{kurikulum_id}/cpl`; GET/PATCH/DELETE `.../cpl/{cpl_id}` |
| Profil lulusan | GET/POST `/kurikulum/{kurikulum_id}/profil-lulusan`; GET/PATCH/DELETE `.../profil-lulusan/{pl_id}` |
| Matriks PL–CPL | GET/PUT `/kurikulum/{kurikulum_id}/profil-lulusan/{pl_id}/cpl` |
| Ringkasan PL | GET `/profil-lulusan/ringkasan` (Admin/Dosen/Mahasiswa sesuai prodi, status kurikulum, dan kurikulum angkatan) |
| Matriks | GET/PUT `/kurikulum/{kurikulum_id}/mata-kuliah/{kurikulum_mk_id}/cpl` |
| Aktivasi/arsip | POST `/kurikulum/{kurikulum_id}/aktifkan` dan `/arsipkan` |
| Salin versi | POST `/kurikulum/{kurikulum_id}/salin` dengan kode/nama tujuan baru |

Daftar berupa array dengan `offset` (default 0), `limit` (default 50, maksimum 100), dan pencarian literal `q` (maksimum 100 karakter). Kurikulum dapat difilter `status=Draft|Aktif|Arsip`; MK paket dapat difilter `semester=1..8`. Pengurutan deterministik berdasarkan kode, atau semester/nama untuk MK paket, dengan UUID sebagai pembeda. Create/salin mengembalikan 201, delete 204, payload tidak valid 422, dan konflik aturan/duplikasi/referensi 409. Konflik membatalkan seluruh transaksi tanpa mengembalikan detail SQL.

Contoh urutan di Swagger setelah Authorize sebagai Admin:

1. POST `/mata-kuliah`: `{"kode_mk":"TI-DB","nama_mk":"Basis Data"}`. Deskripsi opsional dan `aktif` default true.
2. POST `/kurikulum`: `{"kode_kurikulum":"TI-2026","nama":"Kurikulum TI 2026"}`. Status awal selalu Draft.
3. POST `/kurikulum/{id}/mata-kuliah`: `{"mk_id":"<UUID-master-MK>","nama_mk":"Basis Data","sks":3,"semester":1}`. Nama/deskripsi snapshot diisi eksplisit; identitas master MK tidak dapat diganti melalui PATCH snapshot.
4. POST `/kurikulum/{id}/cpl`: `{"kode_cpl":"P-01","kategori":"P","deskripsi":"Menguasai konsep basis data","nasional":false}`. `nasional=true` hanya untuk S/KU dan menyimpan prodi_id null; respons menampilkan prodi_id sebagai cakupan. CPL nasional tetap hanya milik versi kurikulumnya.
5. PUT `.../mata-kuliah/{kurikulum_mk_id}/cpl`: `{"items":[{"cpl_id":"<UUID-CPL>","urutan_rps":1}]}`. Ini mengganti seluruh daftar secara atomik; items kosong menghapus seluruh pembebanan yang belum digunakan. CPL duplikat ditolak, urutan opsional harus positif. Kolom urutan tidak menambah modul RPS.
6. POST `/kurikulum/{id}/aktifkan`. Minimal satu MK dan seluruh MK harus memiliki CPL dari versi/prodi yang sesuai; tidak mewajibkan semua delapan semester sudah diisi.
7. Untuk revisi: POST `/kurikulum/{id}/salin`: `{"kode_kurikulum":"TI-2027","nama":"Revisi TI 2027"}`. Sumber boleh Draft/Aktif/Arsip; tujuan selalu Draft dengan UUID snapshot/CPL baru dan matriks tertaut ke CPL baru. Master MK tetap sama. Angkatan, kelas, rancangan dosen, peserta, dan nilai tidak disalin.

PATCH menggunakan field yang dikirim saja; payload kosong atau null pada field wajib ditolak. Deskripsi MK/master snapshot dapat dibersihkan dengan null, sedangkan deskripsi CPL wajib terisi. Field tak dikenal ditolak. Kode MK yang sudah direferensikan tidak dapat diganti; master MK yang sudah dipakai tidak dapat dihapus, tetapi dapat dinonaktifkan. Penonaktifan tidak menghapus snapshot historis dan MK nonaktif tidak dapat ditambahkan sebagai entri paket baru.

Transisi hanya Draft → Aktif → Arsip. Isi Aktif/Arsip bersifat read-only; tidak ada endpoint kembali ke Draft. Kurikulum Draft yang belum direferensikan dapat dihapus bersama snapshot/CPL/matriksnya. MK paket yang sudah dipakai perkuliahan tidak dapat diedit/dihapus; CPL yang masih ditautkan harus dilepas terlebih dahulu, dan pembebanan yang masih dipakai CPMK tidak boleh dilepas. Perubahan nama master tidak merambat ke snapshot.

Setiap mutasi mengunci parent kurikulum (atau master MK terkait), melakukan validasi dan menyimpan audit sebelum/sesudah dalam satu transaksi. Salin versi mencatat sumber dan target tanpa menyalin riwayat akademik. Penguncian juga melindungi aktivasi dari race dengan edit isi. CRUD prodi, input nilai, dan perhitungan capaian masih tahap berikutnya. Penerapan paket/penugasan tersedia pada bagian di bawah.

## Modul Admin: angkatan, periode, kelas, dan roster

Seluruh endpoint di bawah menggunakan prefix `/api/v1`, khusus Admin, dan dibatasi prodi dari akun login. Parent/resource di luar cakupan menghasilkan 404; Dosen/Mahasiswa 403. Daftar memakai `offset` default 0 dan `limit` default 50 (maksimum 100). Tahun berupa integer 1900–9998; semester studi 1–8. Tidak ada perubahan model atau migrasi baru.

| Resource | Method/path relatif terhadap /api/v1 |
| --- | --- |
| Angkatan | GET/POST `/angkatan`; GET/PATCH/DELETE `/angkatan/{angkatan_id}`; filter `tahun_masuk` |
| Profil mahasiswa angkatan | GET/POST `/angkatan/{angkatan_id}/mahasiswa`; POST menerima `user_id` akun Mahasiswa yang sudah ada; tidak membuat akun/password |
| Periode | GET/POST `/periode-akademik`; GET/PATCH/DELETE `/periode-akademik/{periode_id}`; filter `tahun_mulai`, `semester` |
| Kelas periode | GET/POST `/periode-akademik/{periode_id}/kelas`; GET/PATCH/DELETE `.../kelas/{kelas_id}`; filter `angkatan_id` |
| Roster periode | GET/POST `/periode-akademik/{periode_id}/mahasiswa`; GET/PATCH/DELETE `.../mahasiswa/{mahasiswa_id}`; filter `kelas_periode_id`, `status` |

Contoh alur melalui Swagger:

1. Aktifkan kurikulum yang sudah memiliki MK dan CPL. POST `/angkatan` dengan `{"tahun_masuk":2024,"kurikulum_id":"<UUID-kurikulum-Aktif>"}`. Kurikulum Draft/Arsip ditolak untuk penetapan baru. Angkatan lama tetap dapat menggunakan kurikulum yang kemudian diarsipkan.
2. Jika akun mahasiswa belum memiliki profil angkatan, POST `/angkatan/{id}/mahasiswa` dengan `{"user_id":"<UUID-akun-Mahasiswa>"}`. Akun harus aktif, berperan Mahasiswa, dan satu prodi. Profil yang sudah terhubung tidak dipindah/ditimpa. Daftar profil menampilkan nama/NIM/status akun tanpa password/hash.
3. POST `/periode-akademik` dengan `{"tahun_mulai":2026,"semester":"Ganjil"}`. Respons tahun akademik `2026/2027`, status selalu Dibuka. Tidak ada semester pendek atau input bebas status periode. Penutupan/pembukaan kembali tetap modul berikutnya.
4. POST `/periode-akademik/{id}/kelas` dengan `{"angkatan_id":"<UUID-angkatan>","kode_kelas":"C","semester_studi":5}` → label TI-3C. Semester 7/8 menghasilkan tingkat 4. Prefix label berasal dari prodi, bukan hardcode. K menggunakan `"kode_kelas":"K","semester_studi":null` dan label TI-K; angkatan/periode tetap dibawa untuk membedakan kelompok K.
5. POST `/periode-akademik/{id}/mahasiswa` dengan `{"mahasiswa_id":"<UUID-mahasiswa>","kelas_periode_id":"<UUID-kelas>","status":"Aktif"}`. Aktif wajib A–E; Cuti/Nonaktif wajib K. Mahasiswa harus satu angkatan dengan kelas, dan akun nonaktif tidak dapat diberi penempatan Aktif.
6. PATCH `.../mahasiswa/{mahasiswa_id}` dengan pasangan kelas/status yang valid untuk koreksi sebelum ada nilai, misalnya `{"kelas_periode_id":"<UUID-kelas-K>","status":"Cuti"}`. Roster baru untuk periode berikutnya dibuat melalui POST; tidak mengedit roster periode lama untuk kenaikan kelas.

Ganjil hanya semester studi 1/3/5/7; Genap hanya 2/4/6/8. Seluruh kelas reguler satu angkatan pada periode sama memakai semester studi yang sama. Periode tidak boleh mendahului tahun masuk. Semester studi ditetapkan Admin, tidak dihitung otomatis dari usia angkatan, sehingga mahasiswa K tidak otomatis mendapat paket/kenaikan semester. K tidak memiliki kelas MK atau penugasan baru dari modul ini.

Perubahan kurikulum angkatan ditolak setelah terdapat kelas MK/paket pada angkatan tersebut. Tahun masuk tidak dapat diganti setelah mempunyai mahasiswa/kelas. Perubahan metadata angkatan juga memeriksa periode-periode terkait dan ditolak bila ada yang ditutup. Identitas periode yang sudah mempunyai kelas/rancangan tidak dapat diganti. Periode kosong yang belum memiliki kegiatan/riwayat akademik dapat dihapus; periode yang sudah memiliki audit kegiatan dipertahankan. Audit pembuatan/perubahan identitas periode menyimpan entitas_id dan snapshot tanpa FK periode_id agar penghapusan periode yang benar-benar belum digunakan tetap memungkinkan.

Kelas yang sudah mempunyai kelas MK tidak dapat diganti identitasnya. Kelas yang masih menampung roster tidak dapat dihapus; perubahan A–E/K juga tidak boleh membuat status mahasiswa tidak konsisten. Penghapusan angkatan dibatasi FK RESTRICT untuk menjaga profil/kelas/riwayat.

Koreksi roster sebelum nilai menyelaraskan peserta **kelas MK yang sudah ada** dalam periode yang sama: hapus kepesertaan lama, tambah kepesertaan kelas tujuan untuk status Aktif, dan kosongkan kepesertaan periode tersebut untuk K. Tidak membuat kelas MK, rancangan, instrumen, atau penugasan dosen baru. Mahasiswa dengan nilai pada periode tersebut tidak boleh dipindah/dihapus penempatannya; skor 0 juga dianggap nilai yang sudah ada. Larangan mengulang MK lintas periode ditegakkan UNIQUE mahasiswa/master MK, dengan rollback seluruh perubahan jika dilanggar. Periode baru tidak mengubah peserta atau nilai periode lama.

Mutasi memakai transaksi, audit atomik (termasuk perubahan kepesertaan), lock angkatan lalu periode, serta lock akun mahasiswa saat koreksi roster. Periode Ditutup read-only. Payload salah menghasilkan 422; duplikasi, ketidakcocokan aturan, data yang sudah digunakan, atau penghapusan terhalang referensi menghasilkan 409. Penerapan paket/penugasan, penutupan periode, input nilai, dan manajemen akun pengguna tersedia pada bagian berikut.

## Modul Admin: manajemen akun pengguna (`/api/v1/pengguna`)

Prefix `/api/v1`, khusus **Admin** pada prodi sendiri (`403` untuk Dosen/Mahasiswa, `404` lintas prodi). Tidak ada migrasi tambahan; seluruh respons dan payload audit log tidak pernah menyertakan `password_hash`, `token_version`, ataupun kata sandi mentah.

| Method | Path relatif terhadap /api/v1 | Fungsi |
| --- | --- | --- |
| GET | `/pengguna` | Daftar akun prodi sendiri; filter `role`, `aktif`, `angkatan_id`, pencarian literal `q`, `offset`/`limit` (maksimum 100). |
| POST | `/pengguna` | Buat akun `Dosen` atau `Mahasiswa` baru (sandi 12–72 byte UTF-8; opsi `angkatan_id` khusus `Mahasiswa`). |
| GET | `/pengguna/{user_id}` | Detail profil akun prodi sendiri beserta `angkatan_id` dan `tahun_masuk` bila Mahasiswa. |
| PATCH | `/pengguna/{user_id}` | Perbarui `nim_nidn`, `nama`, `email`, `aktif`, atau tautkan Mahasiswa yang belum berangkatan ke `angkatan_id` (tidak memindah angkatan yang sudah terpasang). |
| POST | `/pengguna/{user_id}/reset-password` | Reset sandi akun `Dosen`/`Mahasiswa` (alasan opsional ke `audit_log`), langsung mencabut seluruh JWT target. |

Aturan perlindungan: Admin tidak dapat menonaktifkan atau mereset sandi akunnya sendiri maupun mengubah/mereset akun Admin lain (`409`), sedangkan penonaktifan `aktif=false` atau reset sandi otomatis menaikkan `token_version` sehingga seluruh sesi target segera dicabut tanpa menghapus riwayat akademik.

## Modul Admin: paket MK massal dan pengampu

Prefix `/api/v1`, khusus Admin pada prodinya. Modul memakai model yang sudah ada, tanpa migrasi baru. Penerapan paket membuat kelas MK, rancangan kosong bersama, serta kepesertaan. CPMK/instrumen disusun Dosen melalui endpoint perencanaan di bawah; sesudah rancangan siap, nilai diinput melalui modul nilai.

| Method | Path relatif terhadap /api/v1 | Fungsi |
| --- | --- | --- |
| GET | `/dosen` | Pilihan akun Dosen prodi sendiri; default aktif, filter `aktif`, pencarian literal `q`, offset/limit maksimum 100. Respons hanya id, NIDN, nama, dan status akun. |
| GET | `/periode-akademik/{periode_id}/angkatan/{angkatan_id}/paket` | Pratinjau paket, seluruh kelas reguler, jumlah roster Aktif per kelas, serta pasangan kelas/MK dan penugasan yang sudah ada. |
| POST | `/periode-akademik/{periode_id}/angkatan/{angkatan_id}/paket/terapkan` | Terapkan seluruh paket semester kepada kelas reguler angkatan secara atomik. |
| PATCH | `/kelas-mk/{kelas_mk_id}/pengampu` | Koreksi satu dosen pengampu sebelum kelas memiliki nilai. |

Alur penggunaan:

1. Tetapkan kurikulum Aktif ke angkatan, buat periode, kelas A–E/K dan roster melalui modul tahap 2. Kurikulum yang kemudian diarsipkan tetap boleh digunakan angkatan lamanya. Semester paket mengikuti semester studi kelas, bukan input bebas atau umur angkatan.
2. GET pratinjau paket. Respons `kelas`, `mata_kuliah`, dan `penugasan` menunjukkan semua pasangan yang wajib diisi. Pada pasangan baru, `kelas_mk_id`, `dosen_id`, dan `rancangan_id` masih null. K dikecualikan. Kelas reguler kosong boleh disiapkan sebelum roster lengkap; tidak membuat mahasiswa/roster otomatis.
3. Ambil pilihan dosen dari GET `/dosen`, lalu kirim body berikut ke endpoint `terapkan`, dengan satu entri untuk **setiap** pasangan kelas reguler dan MK dalam pratinjau:

```json
{
  "penugasan": [
    {
      "kelas_periode_id": "<UUID-kelas-reguler>",
      "kurikulum_mk_id": "<UUID-MK-kurikulum-paket-semester>",
      "dosen_id": "<UUID-akun-Dosen-aktif>"
    }
  ]
}
```

Field tak dikenal, daftar kosong, atau pasangan kelas/MK duplikat ditolak 422. Pasangan di luar kelas/paket angkatan/periode (termasuk K) menghasilkan 404. Pasangan yang belum diisi, dosen salah role/nonaktif, kurikulum Draft, semester tanpa paket, roster tidak konsisten, atau periode Ditutup menghasilkan 409. Prodi selalu dari akun login; resource lintas prodi 404 dan peran Dosen/Mahasiswa 403.

Roster Aktif harus merupakan akun Mahasiswa aktif, profil satu angkatan/prodi, dan kelas reguler yang sesuai periode. Cuti/Nonaktif di K tidak dimasukkan. Mahasiswa yang belum mempunyai roster periode tidak didaftarkan otomatis. Nama/SKS/semester diambil dari snapshot kurikulum; penonaktifan master MK tidak mengubah paket angkatan lama. Setiap MK tetap membutuhkan pembebanan CPL dari versi/prodi yang sesuai.

Respons penerapan berstatus 200 dan memuat konteks serta `total_kelas_mk`, `total_peserta`, `kelas_mk_dibuat`, `kelas_mk_diperbarui`, `rancangan_dibuat`, dan `peserta_ditambahkan`. `total_peserta` adalah jumlah kepesertaan mahasiswa **per kelas MK**, bukan jumlah mahasiswa unik lintas MK.

Dosen/MK kurikulum/periode yang sama memakai satu rancangan untuk seluruh kelas terkait. Dosen berbeda mendapatkan rancangan berbeda; versi kurikulum dan periode lain terpisah. Rancangan baru kosong dan dapat dilengkapi Dosen pada tahap 4. Rancangan yang sudah ada digunakan kembali, tanpa mengubah CPMK, instrumen, bobot, atau nilai.

Permintaan yang sama dapat dikirim ulang: ID tetap, tidak menggandakan peserta/rancangan, tidak mereset nilai, dan seluruh counter perubahan bernilai 0 bila tidak ada tambahan/perubahan. Permintaan tanpa perubahan juga tidak menambah audit. Kepesertaan yang hilang dapat dilengkapi dari roster Aktif; peserta lama yang tidak sesuai roster tidak dihapus diam-diam, tetapi menyebabkan konflik agar dikoreksi melalui modul roster. Larangan mengulang MK berlaku lintas periode, dengan pembatalan seluruh batch bila satu peserta melanggar.

Untuk koreksi pengampu, PATCH `/kelas-mk/{id}/pengampu` dengan `{"dosen_id":"<UUID-Dosen-aktif>"}`. Penerapan massal juga dapat mengoreksi pengampu sesuai body yang diberikan. Keduanya menolak perubahan pada kelas yang memiliki nilai. Penggantian sebelum nilai menautkan kelas ke rancangan dosen tujuan (buat bila belum ada); rancangan lama dan seluruh isinya dipertahankan. Rancangan bersama yang dipakai kelas lain tidak diubah. Kelas yang sudah bernilai tetap boleh menerima penerapan ulang dengan dosen yang sama, tanpa mengubah skor.

Seluruh batch memakai satu transaksi, lock angkatan lalu periode, serta lock akun dosen/mahasiswa dan rancangan terkait. Permintaan bersamaan pada periode sama diserialkan. Setiap perubahan kelas/rancangan/kepesertaan dan ringkasan penerapan dicatat atomik; kegagalan audit juga membatalkan semua perubahan. Penerapan paket tidak menginput nilai atau menyediakan KRS mandiri.

## Modul Dosen: rancangan penilaian bersama

Endpoint perencanaan khusus **Dosen** yang masih mempunyai kelas penugasan pada rancangan tersebut, dalam prodi yang sama. Admin/Mahasiswa mendapat 403; rancangan milik dosen lain, rancangan tanpa kelas penugasan, atau child ID di bawah parent yang salah menghasilkan 404. Modul ini tidak membuat/menghapus induk rancangan: induk dibuat Admin melalui penugasan tahap 3. Tidak ada migrasi baru atau perubahan frontend.

Untuk tabel berikut, `R` adalah `/api/v1/rancangan-penilaian/{rancangan_id}`, `C` adalah `R/cpmk/{cpmk_id}`, dan `S` adalah `C/sub-cpmk/{sub_id}`:

| Method | Path | Fungsi |
| --- | --- | --- |
| GET | `/api/v1/rancangan-penilaian` | Daftar rancangan sendiri, satu baris per rancangan bersama; filter opsional `periode_id`, offset/limit maksimum 100. Label tahun akademik dan semester disertakan. |
| GET | `R` | Detail lengkap CPMK → Sub-CPMK → instrumen, CPL yang boleh dipilih, kelas pengguna, bobot dan status kesiapan/kunci. |
| GET | `/api/v1/kelas-mk/{kelas_mk_id}/rancangan-penilaian` | Buka rancangan dari kelas penugasan; kelas-kelas terkait menunjukkan rancangan yang sama. |
| GET/POST | `R/cpmk` | Daftar/tambah CPMK. |
| GET/PATCH/DELETE | `C` | Baca/edit/hapus CPMK draft beserta anaknya. |
| PUT | `C/cpl` | Ganti daftar pemetaan CPL secara atomik. |
| GET/POST | `C/sub-cpmk` | Daftar/tambah Sub-CPMK. |
| GET/PATCH/DELETE | `S` | Baca/edit/hapus Sub-CPMK draft beserta instrumennya. |
| GET/POST | `S/instrumen` | Daftar/tambah instrumen. |
| GET/PATCH/DELETE | `S/instrumen/{instrumen_id}` | Baca/edit/hapus instrumen. |
| POST | `R/salin` | Isi rancangan tujuan kosong dari sumber milik dosen yang sama pada periode lain dan kurikulum MK yang sama. |

Daftar anak memakai offset/limit default 0/50, maksimum 100; detail rancangan memuat seluruh tree. Daftar rancangan diurutkan dari periode terbaru, dengan UUID sebagai pembeda. Semua create anak menghasilkan 201, delete 204, edit/pemetaan/salin 200; payload tidak valid 422 dan konflik aturan/duplikasi/kunci 409. Field tak dikenal dan PATCH kosong/null pada field wajib ditolak.

Contoh penggunaan setelah Authorize sebagai Dosen:

1. GET `/api/v1/rancangan-penilaian` untuk menemukan rancangan dan konteks periode. GET detailnya untuk membaca `cpl_tersedia` dan `kelas_pengguna`.
2. POST `R/cpmk`: `{"kode_cpmk":"CPMK-2","deskripsi":"Mampu merancang basis data","cpl_ids":["<UUID-CPL-dibebankan>"]}`. `cpl_ids` boleh kosong atau dihilangkan selama draft. PATCH CPMK juga dapat memperbarui daftar ini.
3. PUT `C/cpl`: `{"cpl_ids":["<UUID-CPL-dibebankan>"]}`. Array kosong boleh untuk draft; ID duplikat ditolak. Hanya CPL pada mk_cpl untuk kurikulum_mk rancangan yang sama yang diterima; CPL nasional juga tetap dibatasi versi. Dosen tidak mengubah Master CPL.
4. POST `C/sub-cpmk`: `{"kode_sub":"SUB-2.1","deskripsi":"Mampu menyusun skema relasional"}`.
5. POST `S/instrumen`: `{"nama_instrumen":"Tugas 1","jenis_instrumen":"Tugas","bobot_persentase":"20.00"}`. Jenis: Tugas, Kuis, Praktikum, UTS, UAS. Bobot harus >0 hingga 100, maksimal dua desimal; gunakan string desimal untuk mengirim presisi yang jelas. Bobot dan total pada respons diserialisasi sebagai string desimal.
6. Salin dari periode lain dengan POST ke **rancangan tujuan** `R/salin`: `{"sumber_rancangan_id":"<UUID-rancangan-sumber>"}`. Target harus sudah dibuat Admin melalui penugasan kelas.

Total bobot dijumlahkan oleh service menggunakan Decimal untuk seluruh instrumen rancangan, melintasi semua CPMK/Sub-CPMK. Total di bawah 100 diperbolehkan selama draft; tambah/edit yang membuat total >100 ditolak secara atomik. Penghapusan instrumen/anak draft mengurangi total. Tidak ada pembulatan input berlebih secara diam-diam atau perhitungan kesiapan di frontend.

`siap_dinilai` memerlukan minimal satu CPMK, setiap CPMK terpetakan secara valid, dan total instrumen tepat 100.00%. Kelengkapan ini diturunkan dari data, bukan kolom status yang dapat diedit. `alasan_belum_siap` menjelaskan kekurangan. `boleh_input_nilai` juga memerlukan periode terbuka. CPMK/Sub-CPMK tanpa instrumen tidak diberi bobot/capaian buatan; aturan agregasi dan penyebut nol tetap mengikuti SCHEMA.md.

`struktur_terkunci` true ketika periode ditutup atau terdapat nilai pada salah satu kelas pengguna rancangan. Nilai 0 juga mengunci. Semua perubahan CPMK, pemetaan CPL, Sub-CPMK, instrumen dan bobot lalu ditolak, termasuk penghapusan parent yang akan menghapus anak. Rancangan/kelas terkait tetap dapat dibaca; membuka kembali periode tidak menghapus pembekuan karena nilai. Struktur yang sudah terkunci tidak menghalangi koreksi nilai pada periode terbuka jika rancangan siap dinilai, melalui modul nilai berikutnya.

Salin memerlukan tujuan tanpa CPMK/instrumen/nilai pada periode terbuka, dan sumber milik Dosen yang sama dengan kelas penugasan yang masih terkait. Sumber boleh berupa draft belum lengkap, periode tertutup, atau rancangan yang telah memiliki nilai. Kurikulum MK harus persis sama; kode/nama master yang kebetulan sama pada versi lain tidak cukup. Salinan mendapat UUID CPMK/Sub-CPMK/instrumen baru dan pemetaan ke CPL yang sama, serta sumber_rancangan_id. Sumber tidak berubah, dan peserta/kelas/nilai tidak disalin. Tujuan yang sudah berisi ditolak, tidak ditimpa; salinan draft tetap mengikuti status kelengkapannya sendiri.

Mutasi mengunci periode lalu rancangan sebelum memeriksa nilai atau total bobot. Salin mengunci kedua periode lalu kedua rancangan menurut urutan UUID untuk mencegah deadlock. Penugasan diperiksa kembali setelah menunggu lock. Audit dan seluruh perubahan disimpan atomik, termasuk pemetaan dan salinan tree; kegagalan satu validasi/audit membatalkan seluruh transaksi. Modul nilai dan capaian tersedia di bawah; ekspor CSV/PDF masih pekerjaan berikutnya.

## Tahap 5: nilai, penguncian periode, dan capaian OBE

Semua path berikut memakai prefix `/api/v1`. Tidak ada perubahan skema atau frontend.

| Method | Path | Hak akses dan fungsi |
| --- | --- | --- |
| PUT | `/kelas-mk/{kelas_mk_id}/nilai` | Dosen pengampu: bulk upsert nilai atomik, maksimum 2.000 entri per request. |
| GET | `/kelas-mk/{kelas_mk_id}/nilai` | Admin prodi/Dosen pengampu: nilai kelas; Mahasiswa peserta: hanya nilai sendiri. Array kosong berarti belum ada nilai tersimpan. |
| POST | `/periode-akademik/{periode_id}/tutup` | Admin prodi: tutup periode, tanpa body; nilai boleh belum lengkap. |
| POST | `/periode-akademik/{periode_id}/buka-kembali` | Admin prodi: buka kembali dengan body `{"alasan":"Koreksi nilai"}`. |
| GET | `/kelas-mk/{kelas_mk_id}/capaian` | Admin prodi/Dosen pengampu: capaian setiap peserta dan rekap kelas; Mahasiswa peserta: hanya capaian sendiri, `rekap: []`. |
| GET | `/capaian/saya?periode_id=<UUID>&kumulatif=false` | Khusus Mahasiswa: CPL lintas MK yang diikuti pada periode pilihan. `kumulatif=true` menyertakan periode terdahulu hingga periode pilihan. |

Contoh body PUT nilai setelah rancangan terpetakan dan bobot tepat 100.00%:

```json
{
  "items": [
    {
      "instrumen_id": "<UUID-instrumen-rancangan-kelas>",
      "mahasiswa_id": "<UUID-peserta-Aktif-kelas>",
      "nilai_mentah": "82.50"
    }
  ]
}
```

Skor harus 0–100 dengan maksimal dua desimal, bukan null/NaN/Infinity. Field tak dikenal, daftar kosong dan pasangan instrumen/mahasiswa duplikat ditolak 422. Instrumen harus berasal dari rancangan kelas, peserta harus sesuai roster Aktif, angkatan/kurikulum/prodi kelas dan akun Mahasiswa aktif. Pasangan di luar konteks menghasilkan 404; peran tanpa hak tulis 403; periode tertutup atau rancangan belum siap 409. Satu entri salah atau audit gagal membatalkan seluruh batch.

Upsert memakai pasangan instrumen + kelas MK + mahasiswa. Entri yang dihilangkan dari request tidak dihapus atau diubah menjadi nol. Pengiriman skor yang sama mempertahankan ID, timestamp dan audit; koreksi mempertahankan ID serta mencatat pelaku, waktu dan skor sebelum/sesudah sebagai string desimal. Respons nilai memakai string dua desimal. Tidak ada endpoint penghapusan nilai historis.

Input nilai mengunci periode lalu rancangan, memeriksa ulang penugasan setelah menunggu lock, kemudian memvalidasi kesiapan dan seluruh peserta. Nilai pertama, termasuk 0, membekukan struktur rancangan bersama. Koreksi nilai tetap boleh selama periode terbuka. Penutupan mengunci baris periode yang sama sehingga diserialkan dengan input nilai dan mutasi akademik. Menutup periode yang sudah tertutup atau membuka kembali periode terbuka menghasilkan 409. Alasan pembukaan kembali wajib nonkosong (maksimal 2.000 karakter); audit menyimpan status sebelum/sesudah, pelaku dan waktu secara atomik. Kolom penutupan terkini dikosongkan saat dibuka kembali; seluruh riwayat penutupan tetap tersimpan di audit. Membuka kembali tidak melepas pembekuan struktur yang sudah bernilai.

Respons capaian kelas memuat `peserta[{mahasiswa_id, hasil}]` dan `rekap`. Setiap hasil memiliki `jenis` (Mata kuliah/Sub-CPMK/CPMK/CPL), `id`, `kode`, `label`, `kurikulum_id`, `capaian`, `status`, serta jumlah instrumen terisi/total. Rekap mengganti jumlah instrumen dengan `mahasiswa_lengkap`/`total_mahasiswa`. Kode/label dan capaian CPL/CPMK dapat langsung menjadi seri radar chart; tidak ada target atau ambang kelulusan buatan.

Perhitungan memakai Decimal, pembulatan HALF_UP dua desimal hanya pada hasil akhir. Sub-CPMK/CPMK/CPL menggunakan `sum(nilai × bobot) / sum(bobot)` atas instrumen relevan yang unik. CPL lintas MK menggabungkan pembilang/penyebut tanpa bobot SKS tambahan; satu instrumen boleh berkontribusi penuh pada beberapa CPL. CPL dengan kode sama pada versi kurikulum berbeda tetap berupa hasil terpisah berdasarkan UUID/kurikulum. Capaian Mata kuliah memakai seluruh instrumen rancangan dengan bobot total 100%.

Nilai yang dibutuhkan belum diisi atau penyebut nol menghasilkan `capaian: null`, status `Belum lengkap`; rancangan belum siap menghasilkan null, `Belum siap dinilai`. Nilai 0 yang sudah diinput tetap sah dan lengkap. Rekap hanya merata-ratakan capaian mahasiswa lengkap sebelum pembulatan, disertai jumlah lengkap/total. Jika sebagian mahasiswa belum lengkap, rata-rata yang tersedia tetap ditampilkan dengan status `Belum lengkap`; tanpa mahasiswa lengkap, capaian null. Kelas A/B tidak digabung walaupun instrumennya sama. GET historis tetap tersedia setelah periode ditutup.

Laporan CPL pribadi selalu membatasi peserta berdasarkan identitas JWT. Periode wajib eksplisit, urutan kumulatif mengikuti tahun akademik lalu Ganjil/Genap; semester masa depan dan MK yang tidak diikuti tidak dimasukkan. Cuti/Nonaktif di K tanpa peserta tidak menambah instrumen wajib. Endpoint ini tidak menerima pilihan mahasiswa lain. Endpoint audit log, laporan prodi/lintas kelas, dan ekspor CSV/PDF tersedia pada Tahap 6 di bawah.

## Tahap 6: Audit log, laporan prodi/lintas kelas, dan ekspor CSV/PDF

Seluruh path menggunakan prefix `/api/v1` tanpa migrasi database maupun dependensi eksternal baru (ekspor PDF memakai PDF 1.4 stdlib dengan font Type1 Helvetica/WinAnsiEncoding dan CSV UTF-8 BOM yang dinetralkan dari *formula injection*).

| Method | Path | Hak akses dan fungsi |
| --- | --- | --- |
| GET | `/audit-log` | Khusus Admin prodi: riwayat `audit_log` terbaru lebih dulu dengan filter opsional `periode_id`, `aksi`, `entitas`, pencarian literal `q`, `offset`, `limit` (1–100); menyertakan `aktor_nama`, `aktor_role`, serta `alasan` pembukaan kembali tanpa field sensitif. |
| GET | `/laporan/prodi` | Khusus Admin prodi: rekap kelas MK dan agregasi CPL terisolasi per `periode_id` + `kurikulum_id` (+ filter opsional `semester`), mengecualikan kelas TI-K dan menghitung `total_audit_periode`. |
| GET | `/laporan/prodi/ekspor` | Khusus Admin prodi: unduhan CSV/PDF dari laporan prodi (`format=csv|pdf`). |
| GET | `/laporan/lintas-kelas` | Admin prodi atau Dosen pengampu: agregasi terbobot `Decimal` lintas `kelas_mk_ids` eksplisit pada satu `periode_id` dan satu `kurikulum_id` yang sama (`409` bila lintas kurikulum, `422` bila duplikat/kosong). |
| GET | `/laporan/lintas-kelas/ekspor` | Admin prodi atau Dosen pengampu: unduhan CSV/PDF laporan lintas kelas (`format=csv|pdf`). |
| GET | `/kelas-mk/{kelas_mk_id}/ekspor` | Admin prodi atau Dosen pengampu: unduhan CSV/PDF rekap kelas beserta rincian instrumen/CPMK/CPL/MK tiap peserta; tetap tersedia saat periode ditutup, memisahkan nilai kosong (`""`/`-`) dari `0.00` valid. |
| GET | `/capaian/saya/ekspor` | Khusus Mahasiswa (identitas JWT): unduhan PDF (default) atau CSV capaian CPL/MK pribadi per periode atau kumulatif tanpa nilai teman sejawat maupun rekap kelas; peserta TI-K tetap dapat mengunduh tanpa angka `0.00` buatan. |
| GET | `/mahasiswa/periode` | Khusus Mahasiswa (identitas JWT): daftar riwayat periode akademik pribadi beserta kelas (`TI-1A` s.d. `TI-4E` atau `TI-K`), status (`Aktif`/`Cuti`/`Nonaktif`), kurikulum angkatan, dan jumlah mata kuliah paket. |
| GET | `/mahasiswa/kelas-mk/{kelas_mk_id}/rincian` | Khusus Mahasiswa peserta terdaftar: rincian instrumen penilaian pribadi (`Sudah diinput`/`Belum diinput`, mempertahankan `0.00` vs `null`), pemetaan CPMK/Sub-CPMK/CPL, dan ringkasan capaian pribadi tanpa data mahasiswa lain. |

Verifikasi: 100 tes PostgreSQL lulus (termasuk 5 grup skenario pelaporan, endpoint baca Mahasiswa, isolasi kurikulum, rata-rata terbobot lintas kelas, pemisahan NULL vs `0.00`, validasi xref PDF 1.4, dan ACL audit/ekspor), serta `ruff check` dan `ruff format --check` lolos.
