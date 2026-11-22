# PNL OBE Backend

Fondasi FastAPI, SQLAlchemy 2, Pydantic v2, PostgreSQL 15+, Alembic, JWT (HS256), dan Bcrypt. Python 3.11+; versi dependensi yang diuji tersimpan di `requirements.lock`. Skema 21 tabel mengikuti `../SCHEMA.md`.

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

Seed default membuat prodi dan Admin dari `.env`. `python -m app.services.seed --demo` juga membuat akun Dosen/Mahasiswa contoh, angkatan, dan kurikulum Draft. Semua kredensial harus diberikan di environment/.env; tidak ada password bawaan. Seed idempoten, tidak mereset password akun yang sudah ada, dan rollback seluruh batch jika ada konflik. Data demo belum menyusun paket/kelas/perkuliahan; itu bagian modul akademik berikutnya.

`alembic downgrade base` hanya untuk database development kosong yang boleh dihapus. Jangan menjalankannya pada database berisi riwayat akademik. Startup server tidak menjalankan migrasi atau seed secara otomatis.

## Endpoint tersedia

| Method | Path | Fungsi |
| --- | --- | --- |
| GET | `/health` | Liveness aplikasi tanpa koneksi database. |
| GET | `/ready` | Koneksi database dan revisi Alembic sesuai; 503 bila belum siap. |
| POST | `/api/v1/auth/token` | Form OAuth2: `username` = email, `password` = password akun; respons access token. |
| GET | `/api/v1/auth/me` | Profil pengguna JWT yang masih aktif; tidak memuat hash/password. |
| POST | `/api/v1/auth/logout` | Cabut seluruh access token pengguna, termasuk sesi browser lain; 204. |
| GET | `/api/v1/kelas-mk?periode_id=<uuid>` | Daftar kelas sesuai prodi/penugasan/kepesertaan; `offset` ≥ 0, `limit` 1–100. |
| GET | `/api/v1/kelas-mk/<uuid>` | Detail kelas sesuai cakupan akses; 404 juga untuk resource di luar cakupan. |
| GET | `/api/v1/kelas-mk/<uuid>/peserta` | ID peserta untuk Admin/Dosen terkait; Mahasiswa ditolak. |

Pemeriksaan HTTP lokal setelah seed demo/server berjalan: `python scripts/smoke_local.py`. Perintah ini login/logout tiga akun demo tanpa mencetak token/password.

Swagger tersedia di `/docs`. Gunakan tombol Authorize dan isi email pada kolom username. Tidak ada registrasi publik atau refresh token. Access token berlaku 30 menit secara default. JWT memvalidasi signature, expiry, issuer, audience, dan versi token. Role, status akun, dan status prodi dibaca dari database pada setiap request; perubahan role berlaku tanpa menerbitkan JWT baru. `users.token_version` mendukung pencabutan token secara persisten tanpa tabel baru.

Endpoint kelas MK masih hanya membaca; modul Admin untuk master MK dan kurikulum kini mendukung perubahan sebagaimana bagian berikut. Endpoint KRS mandiri dan tulis nilai belum tersedia. Layanan akademik berikutnya wajib memakai validasi lintas relasi, penguncian periode/rancangan, dan audit sesuai SCHEMA.md. Constraint FK/UNIQUE/CHECK bukan pengganti validasi layanan tersebut.

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

Setiap mutasi mengunci parent kurikulum (atau master MK terkait), melakukan validasi dan menyimpan audit sebelum/sesudah dalam satu transaksi. Salin versi mencatat sumber dan target tanpa menyalin riwayat akademik. Penguncian juga melindungi aktivasi dari race dengan edit isi. CRUD prodi, penerapan paket ke kelas, penugasan, penilaian, dan perhitungan capaian masih tahap berikutnya.
