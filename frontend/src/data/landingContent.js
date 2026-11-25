export const navLinks = [
  { label: 'Alur pengukuran', href: '#alur-pengukuran' },
  { label: 'Prinsip sistem', href: '#prinsip-sistem' },
  { label: 'Peran pengguna', href: '#peran-pengguna' },
];

export const contextStripItems = [
  {
    title: 'KRS Paket Terpusat',
    subtitle: 'Mata kuliah ditetapkan prodi per angkatan',
  },
  {
    title: 'Rancangan Bersama',
    subtitle: 'Satu rancangan dosen untuk kelas paralel',
  },
  {
    title: 'Bobot Tervalidasi 100%',
    subtitle: 'Struktur dibekukan sejak nilai pertama',
  },
  {
    title: 'Data Jujur & Berversi',
    subtitle: 'Belum dinilai tampil “—”, bukan nol',
  },
];

export const measurementStages = [
  {
    badge: '01',
    title: 'Instrumen',
    description:
      'Dosen mencatat skor mentah 0–100 untuk Tugas, Kuis, Praktikum, UTS, dan UAS.',
    meta: 'Total bobot rancangan wajib 100%',
    topBarColor: '#CC6E38',
    badgeBg: '#F7EAE1',
    badgeText: '#B55824',
    featured: false,
  },
  {
    badge: '02',
    title: 'Sub-CPMK',
    description:
      'Nilai instrumen diagregasi berbobot untuk membentuk capaian rinci tiap Sub-CPMK.',
    meta: 'Nilai belum diinput tidak dihitung nol',
    topBarColor: '#D88F60',
    badgeBg: '#F3EFE6',
    badgeText: '#3D565C',
    featured: false,
  },
  {
    badge: '03',
    title: 'CPMK',
    description:
      'Seluruh instrumen unik di bawah CPMK dihitung berbobot menjadi capaian mata kuliah.',
    meta: 'Wajib terpetakan ke CPL mata kuliah',
    topBarColor: '#5F838A',
    badgeBg: '#EDF2F1',
    badgeText: '#2B4C54',
    featured: false,
  },
  {
    badge: '04 · HASIL AKHIR',
    title: 'CPL',
    description:
      'Pemetaan CPMK menghubungkan hasil lintas mata kuliah dalam versi kurikulum yang sama.',
    meta: 'Terbaca per periode & grafik radar',
    topBarColor: '#CC6E38',
    featured: true,
  },
];

export const academicPrinciples = [
  {
    title: 'Paket per angkatan & versi kurikulum',
    description:
      'Kelas reguler TI-1A s.d. TI-4E menerima paket seragam; TI-K mencatat Cuti/Nonaktif tanpa paket.',
  },
  {
    title: 'Pembekuan struktur & audit periode',
    description:
      'Rancangan bersama terkunci otomatis sejak nilai pertama; penutupan periode tercatat audit.',
  },
  {
    title: 'Tanpa asumsi nilai nol',
    description:
      'Instrumen yang belum dinilai tampil sebagai “—” (Belum lengkap), bukan 0.',
  },
];

export const illustrativeRecap = {
  title: 'Rekap kelas · Basis Data',
  context: 'TI-3A  ·  Kurikulum TI 2024  ·  2026/2027 Ganjil',
  badge: 'Data ilustrasi',
  kpis: [
    {
      label: 'Peserta lengkap',
      value: '24 / 30',
      note: 'Hanya peserta lengkap dihitung',
      valueTone: 'default',
      valueSize: 'lg',
    },
    {
      label: 'Rancangan bersama',
      value: 'Terkunci · 100%',
      note: 'Dipakai TI-3A & TI-3B',
      valueTone: 'default',
      valueSize: 'md',
    },
    {
      label: 'Status periode',
      value: 'Dibuka',
      note: 'Semester 5 · Ganjil',
      valueTone: 'open',
      valueSize: 'md',
    },
  ],
  rows: [
    {
      code: 'CPMK-01',
      cpl: 'CPL-02, CPL-05',
      status: 'Lengkap',
      complete: true,
      value: '81,40%',
    },
    {
      code: 'CPMK-02',
      cpl: 'CPL-05',
      status: 'Lengkap',
      complete: true,
      value: '76,85%',
    },
    {
      code: 'CPMK-03',
      cpl: 'CPL-07',
      status: 'Belum lengkap',
      complete: false,
      value: '—',
    },
  ],
  footnote:
    'Nilai instrumen yang belum diinput ditampilkan “—” dan tidak dihitung sebagai nol.',
};

export const userRoles = [
  {
    number: '01',
    name: 'Admin / Kaprodi',
    description:
      'Mengelola versi kurikulum, master CPL, matriks pembebanan, angkatan, periode, kelas A–E/K, paket massal, penugasan dosen, dan kunci periode.',
    pills: ['Kurikulum berversi', 'Paket massal', 'Kunci & audit periode'],
  },
  {
    number: '02',
    name: 'Dosen',
    description:
      'Menyusun rancangan penilaian bersama (CPMK, pemetaan CPL, Sub-CPMK, instrumen berbobot 100%) serta mengisi nilai mentah pada kelas yang diampu.',
    pills: ['Rancangan bersama', 'Input nilai 0–100', 'Rekap & radar kelas'],
  },
  {
    number: '03',
    name: 'Mahasiswa',
    description:
      'Melihat rincian nilai instrumen, status kelengkapan tiap CPMK, dan capaian CPL pribadi untuk mata kuliah paket pada tiap periode akademik.',
    pills: ['Akses read-only', 'Rincian instrumen', 'Capaian pribadi'],
  },
];
