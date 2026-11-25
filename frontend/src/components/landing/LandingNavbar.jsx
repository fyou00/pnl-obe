import { Link } from 'react-router-dom';
import { navLinks } from '../../data/landingContent.js';

export default function LandingNavbar() {
  return (
    <header className="absolute top-6 inset-x-0 z-20 px-12">
      <nav
        aria-label="Navigasi utama"
        className="mx-auto max-w-[1344px] h-16 px-6 rounded-[16px] flex items-center justify-between bg-white/66 border border-white/85 backdrop-blur-[20px] shadow-[0_8px_24px_rgba(21,51,58,0.08)]"
      >
        <Link to="/" className="flex items-center gap-3 shrink-0">
          <span className="w-8 h-8 rounded-[8px] bg-[#15333A] flex items-center justify-center text-[#FAF8F3] font-bold text-[16px] leading-none">
            O
          </span>
          <span className="text-[18px] font-bold tracking-[-0.01em] text-[#15333A]">
            PNL OBE
          </span>
          <span className="w-px h-[18px] bg-[#B9C5C3]" aria-hidden="true" />
          <span className="text-[13px] font-medium text-[#486065]">
            Teknik Informatika
          </span>
        </Link>

        <div className="flex items-center gap-[30px]">
          {navLinks.map((item) => (
            <a
              key={item.href}
              href={item.href}
              className="text-[14px] font-medium text-[#1D373E] hover:text-[#CC6E38] transition-colors"
            >
              {item.label}
            </a>
          ))}

          <Link
            to="/login"
            className="bg-[#15333A] hover:bg-[#1D434B] transition-colors rounded-[9px] px-[18px] py-[10px] inline-flex items-center gap-2 text-[14px] font-semibold leading-[17px] text-white"
          >
            <span>Masuk</span>
            <span className="font-medium text-[#F0C3A4]" aria-hidden="true">
              ↗
            </span>
          </Link>
        </div>
      </nav>
    </header>
  );
}
