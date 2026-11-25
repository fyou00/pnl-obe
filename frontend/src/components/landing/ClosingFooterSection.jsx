import { Link } from 'react-router-dom';

export default function ClosingFooterSection() {
  return (
    <section className="w-full bg-[#FAF8F3] pt-[44px] pb-[28px]">
      <div className="max-w-[1440px] mx-auto px-[72px] flex flex-col gap-[33px]">
        <div className="bg-white border border-[#E4DFD4] rounded-[16px] min-h-[124px] px-9 py-6 flex items-center justify-between gap-8">
          <div className="flex flex-col gap-[6px]">
            <h2 className="font-serif font-normal text-[30px] leading-[36px] text-[#15333A]">
              Mulai dari ruang kerja Anda.
            </h2>
            <p className="text-[15px] leading-[22px] text-[#4B6267]">
              Masuk dengan akun PNL sesuai peran Admin / Kaprodi, Dosen, atau
              Mahasiswa Teknik Informatika.
            </p>
          </div>

          <Link
            to="/login"
            className="bg-[#15333A] hover:bg-[#1D434B] transition-colors rounded-[10px] px-[26px] py-[15px] inline-flex items-center gap-[10px] text-[15px] font-semibold leading-[18px] text-white shrink-0"
          >
            <span>Masuk ke PNL OBE</span>
            <span className="text-[#F0C3A4]" aria-hidden="true">
              ↗
            </span>
          </Link>
        </div>

        <footer className="flex flex-col gap-[18px]">
          <div className="h-px w-full bg-[#E3DDD1]" aria-hidden="true" />
          <div className="flex items-center justify-between gap-4">
            <div className="flex items-center gap-[10px]">
              <span className="w-6 h-6 rounded-[6px] bg-[#15333A] flex items-center justify-center text-[12px] font-bold leading-none text-[#FAF8F3]">
                O
              </span>
              <span className="text-[17px] font-bold leading-[21px] text-[#15333A]">
                PNL OBE
              </span>
              <span className="text-[13.5px] leading-[16px] text-[#5A6F73] whitespace-pre-wrap">
                ·  Pengukuran Capaian Pembelajaran Lulusan
              </span>
            </div>

            <p className="text-[13.5px] leading-[16px] text-[#5A6F73] whitespace-pre-wrap">
              Program Studi Teknik Informatika  ·  Politeknik Negeri Lhokseumawe
            </p>
          </div>
        </footer>
      </div>
    </section>
  );
}
