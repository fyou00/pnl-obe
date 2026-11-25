import { Link } from 'react-router-dom';
import panoramaImg from '../../assets/gedung-tik-panorama.png';
import LandingNavbar from './LandingNavbar.jsx';

export default function HeroSection() {
  return (
    <section className="relative w-full h-[640px] overflow-hidden bg-[#FAF8F3]">
      <img
        src={panoramaImg}
        alt="Gedung TIK Politeknik Negeri Lhokseumawe"
        className="absolute inset-0 w-full h-full object-cover object-[41.6667%_50%] select-none pointer-events-none"
      />

      {/* Gradasi keterbacaan sisi kiri untuk menjaga kontras tipografi */}
      <div
        className="absolute inset-y-0 left-0 flex pointer-events-none"
        aria-hidden="true"
      >
        <div className="w-[max(0px,calc(50%-720px))] h-full bg-[rgba(250,248,243,0.988)]" />
        <div
          className="w-[900px] h-full"
          style={{
            background:
              'linear-gradient(90deg, rgba(250,248,243,0.988) 0%, rgba(250,248,243,0.949) 48%, rgba(250,248,243,0.533) 74%, rgba(250,248,243,0) 100%)',
          }}
        />
      </div>

      {/* Gradasi atas navigasi */}
      <div
        className="absolute inset-x-0 top-0 h-[110px] pointer-events-none"
        aria-hidden="true"
        style={{
          background:
            'linear-gradient(180deg, rgba(250,248,243,0.271) 0%, rgba(250,248,243,0) 100%)',
        }}
      />

      <LandingNavbar />

      <div className="relative z-10 max-w-[1440px] mx-auto h-full px-[72px]">
        <div className="pt-[150px] w-[496px] flex flex-col gap-[22px]">
          <div className="flex items-center gap-[10px]">
            <span
              className="w-6 h-[2px] rounded-[1px] bg-[#CC6E38] shrink-0"
              aria-hidden="true"
            />
            <span className="text-[12px] font-bold tracking-[0.08em] leading-[15px] text-[#4A6065]">
              PROGRAM STUDI TEKNIK INFORMATIKA · PNL
            </span>
          </div>

          <h1 className="font-serif font-normal text-[56px] leading-[64px] tracking-[-0.01em] text-[#132F36]">
            Dari nilai kuliah
            <br />
            ke capaian lulusan.
          </h1>

          <p className="w-[452px] text-[17px] leading-[27px] text-[#314B51]">
            Sistem pengukuran OBE berbasis KRS paket untuk menelusuri nilai
            tugas, kuis, praktikum, hingga ujian menjadi capaian CPMK dan CPL.
          </p>

          <div className="pt-2 flex items-center gap-[14px]">
            <Link
              to="/login"
              className="bg-[#15333A] hover:bg-[#1D434B] transition-colors rounded-[10px] px-6 py-[15px] shadow-[0_6px_16px_rgba(21,51,58,0.15)] inline-flex items-center gap-[10px] text-[15px] font-semibold leading-[18px] text-white"
            >
              <span>Masuk ke PNL OBE</span>
              <span className="text-[#F0C3A4]" aria-hidden="true">
                ↗
              </span>
            </Link>

            <a
              href="#alur-pengukuran"
              className="bg-[#FAF8F3]/85 hover:bg-[#FAF8F3] transition-colors border border-[#C7CFCB] rounded-[10px] px-5 py-[15px] inline-flex items-center gap-2 text-[15px] font-medium leading-[18px] text-[#1D3B42]"
            >
              <span>Lihat alur pengukuran</span>
              <span className="font-normal text-[#5A7074]" aria-hidden="true">
                ↓
              </span>
            </a>
          </div>
        </div>

        <div className="absolute right-[72px] bottom-[23px] rounded-full bg-white/72 border border-white/88 backdrop-blur-[14px] px-[14px] py-[7px] inline-flex items-center gap-2">
          <span
            className="w-[6px] h-[6px] rounded-full bg-[#CC6E38] shrink-0"
            aria-hidden="true"
          />
          <span className="text-[12px] font-medium leading-[15px] text-[#19363D]">
            Gedung TIK · Politeknik Negeri Lhokseumawe
          </span>
        </div>
      </div>
    </section>
  );
}
