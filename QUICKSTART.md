# Panduan Cepat Menjalankan Backend, Frontend, dan Seed (PNL OBE)

Panduan singkat untuk menjalankan aplikasi lokal dari root repositori `pnl-obe`.

## Prasyarat & Instalasi Awal

* **Backend (Python 3.11+):**
  ```sh
  cd backend
  python3.11 -m venv .venv
  source .venv/bin/activate
  python -m pip install -r requirements.lock
  python -m pip install --no-deps -e .
  # Tambahkan baris berikut hanya jika menjalankan PostgreSQL lokal tanpa Docker:
  python -m pip install '.[local-postgres]'
  ```
* **Frontend (Node.js):**
  ```sh
  cd frontend
  npm install
  ```

---

## 1. Jalankan PostgreSQL

Pilih salah satu opsi:

* **Opsi A — PostgreSQL lokal tanpa Docker** (jalankan dari `backend/` dengan `.venv` aktif, biarkan terminal ini terbuka):
  ```sh
  # Pertama kali (membuat backend/.env otomatis bila belum ada):
  python scripts/dev_postgres.py --init-env

  # Selanjutnya:
  python scripts/dev_postgres.py
  ```
* **Opsi B — Docker Compose:** salin `backend/.env.example` menjadi `backend/.env`, isi variabel koneksi & kredensial, lalu jalankan dari `backend/`:
  ```sh
  docker compose up -d --wait
  ```

---

## 2. Jalankan Migrasi Database

Di terminal baru dari `backend/` dengan `.venv` aktif:

```sh
alembic upgrade head
```

---

## 3. Memasukkan Seed

Semua perintah di bawah dijalankan dari `backend/` dengan `.venv` aktif (urutan file JSON: `mata_kuliah` → `cpl` → `profil_lulusan` → `mk_cpl`):

* **Seed lengkap (akun awal + demo operasional + Kurikulum TI 2024 aktif, 61 MK, 12 CPL, 4 Profil Lulusan, 30 PL–CPL, 118 MK–CPL, 2 periode & nilai demo):**
  ```sh
  python -m app.services.seed --demo \
    --kurikulum-file seeds/kurikulum_ti_2024_mata_kuliah.json \
    --kurikulum-file seeds/kurikulum_ti_2024_cpl.json \
    --kurikulum-file seeds/kurikulum_ti_2024_profil_lulusan.json \
    --kurikulum-file seeds/kurikulum_ti_2024_mk_cpl.json \
    --demo-file seeds/demo_operasional_ti_2024.json
  ```
  > Hapus `--demo` dan `--demo-file ...` jika hanya ingin membuat Prodi `TI`, akun `Admin`, dan kurikulum `TI-2024` (`Draft`).

* **Seed kurikulum / demo terpisah (jika akun `Admin` sudah ada):**
  ```sh
  python -m app.services.seed_curriculum \
    seeds/kurikulum_ti_2024_mata_kuliah.json \
    seeds/kurikulum_ti_2024_cpl.json \
    seeds/kurikulum_ti_2024_profil_lulusan.json \
    seeds/kurikulum_ti_2024_mk_cpl.json
  python -m app.services.seed_demo seeds/demo_operasional_ti_2024.json
  ```

**Catatan & Akun Demo:**
* Seed bersifat idempoten (aman dijalankan ulang dan tidak mereset password/nilai yang sudah ada).
* Jika dijalankan tanpa `--demo-file`, `TI-2024` masuk berstatus `Draft` dan siap diaktifkan di **Versi Kurikulum** (`/admin/kurikulum`).
* Jika memakai `demo_operasional_ti_2024.json`, seluruh akun demo memakai password `SEED_DOSEN_PASSWORD` / `SEED_MAHASISWA_PASSWORD` dari `backend/.env`:
  * **Dosen:** `dosen.rpl@demo.pnl.ac.id`, `dosen.jarkom@demo.pnl.ac.id`, `dosen.ai@demo.pnl.ac.id`
  * **Mahasiswa aktif:** `mhs.a1@demo.pnl.ac.id`..`mhs.a3@demo.pnl.ac.id`, `mhs.b1@demo.pnl.ac.id`..`mhs.b3@demo.pnl.ac.id`, `mhs.c1@demo.pnl.ac.id`
  * **Mahasiswa `TI-K`:** `mhs.cuti@demo.pnl.ac.id` (`Cuti`), `mhs.nonaktif@demo.pnl.ac.id` (`Nonaktif`)

---

## 4. Jalankan Backend (FastAPI)

Dari `backend/` dengan `.venv` aktif:

```sh
uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8000 --reload
```

* API & Swagger UI: `http://127.0.0.1:8000/docs`
* Liveness / Readiness: `http://127.0.0.1:8000/health` dan `http://127.0.0.1:8000/ready`

---

## 5. Jalankan Frontend (React + Vite)

Di terminal lain dari root repositori:

```sh
cd frontend
npm run dev
```

* Aplikasi Web: `http://localhost:5173` (proxy `/api`, `/health`, `/ready` otomatis mengarah ke `http://127.0.0.1:8000`; `frontend/.env` opsional).
* Login memakai email dan password akun yang tertulis di `backend/.env` (jangan commit `.env`).

---

## Verifikasi Singkat (Opsional)

```sh
# Backend lint, format, dan tes PostgreSQL
cd backend && .venv/bin/ruff check . && .venv/bin/ruff format --check . && .venv/bin/pytest -q

# Frontend production build
npm --prefix frontend run build
```
