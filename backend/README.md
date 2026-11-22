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

Seed default membuat prodi dan Admin dari `.env`. `python -m app.services.seed --demo` juga membuat akun Dosen/Mahasiswa contoh, angkatan, dan kurikulum Draft. Semua kredensial harus diberikan di environment/.env; tidak ada password bawaan. Seed idempoten, tidak mereset password akun yang sudah ada, dan rollback seluruh batch jika ada konflik. Data demo belum menyusun paket/kelas/perkuliahan; susun melalui endpoint akademik dan penerapan paket Admin.

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

Setiap mutasi mengunci parent kurikulum (atau master MK terkait), melakukan validasi dan menyimpan audit sebelum/sesudah dalam satu transaksi. Salin versi mencatat sumber dan target tanpa menyalin riwayat akademik. Penguncian juga melindungi aktivasi dari race dengan edit isi. CRUD prodi, penilaian, dan perhitungan capaian masih tahap berikutnya. Penerapan paket/penugasan tersedia pada bagian di bawah.

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

Mutasi memakai transaksi, audit atomik (termasuk perubahan kepesertaan), lock angkatan lalu periode, serta lock akun mahasiswa saat koreksi roster. Periode Ditutup read-only. Payload salah menghasilkan 422; duplikasi, ketidakcocokan aturan, data yang sudah digunakan, atau penghapusan terhalang referensi menghasilkan 409. Endpoint manajemen akun, penutupan periode, penyusunan rancangan penilaian, dan nilai tetap pekerjaan berikutnya. Penerapan paket/penugasan dosen tersedia pada bagian berikut. Frontend tidak diubah.

## Modul Admin: paket MK massal dan pengampu

Prefix `/api/v1`, khusus Admin pada prodinya. Modul memakai model yang sudah ada, tanpa migrasi baru. Penerapan paket membuat kelas MK, rancangan kosong bersama, serta kepesertaan; belum menyusun CPMK/instrumen atau menginput nilai.

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

Seluruh batch memakai satu transaksi, lock angkatan lalu periode, serta lock akun dosen/mahasiswa dan rancangan terkait. Permintaan bersamaan pada periode sama diserialkan. Setiap perubahan kelas/rancangan/kepesertaan dan ringkasan penerapan dicatat atomik; kegagalan audit juga membatalkan semua perubahan. Tidak ada perubahan frontend, KRS mandiri, atau endpoint input nilai pada tahap ini.
