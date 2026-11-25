import {
  academicPrinciples,
  illustrativeRecap,
} from '../../data/landingContent.js';

export default function PrinciplesSection() {
  return (
    <section
      id="prinsip-sistem"
      className="w-full bg-[#F3EFE6] border-t border-[#E3DDD1] py-[56px]"
    >
      <div className="max-w-[1440px] mx-auto px-[72px] grid grid-cols-[minmax(0,580px)_minmax(0,660px)] justify-between items-center gap-[56px]">
        <div className="flex flex-col gap-5">
          <div className="flex flex-col gap-[10px]">
            <p className="text-[12px] font-bold tracking-[0.08em] leading-[15px] text-[#CC6E38]">
              KONTEKS &amp; INTEGRITAS DATA
            </p>
            <h2 className="font-serif font-normal text-[36px] leading-[44px] text-[#15333A]">
              Konteks akademik tetap terjaga.
            </h2>
          </div>

          <div className="flex flex-col gap-[14px]">
            {academicPrinciples.map((principle) => (
              <div key={principle.title} className="flex items-start gap-3">
                <span
                  className="w-[6px] h-[6px] rounded-[2px] bg-[#CC6E38] mt-[7px] shrink-0"
                  aria-hidden="true"
                />
                <div className="flex flex-col gap-[2px]">
                  <h3 className="text-[14.5px] font-semibold leading-[18px] text-[#15333A]">
                    {principle.title}
                  </h3>
                  <p className="text-[13.5px] leading-[20px] text-[#486065]">
                    {principle.description}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>

        <aside
          aria-label="Ilustrasi rekap kelas"
          className="bg-white border border-[#DDD8CC] rounded-[14px] shadow-[0_8px_24px_rgba(21,51,58,0.06)] pt-[22px] px-6 pb-5 flex flex-col gap-4"
        >
          <div className="flex items-start justify-between gap-4">
            <div className="flex flex-col gap-[3px]">
              <h3 className="text-[16px] font-semibold leading-[19px] text-[#15333A]">
                {illustrativeRecap.title}
              </h3>
              <p className="text-[12.5px] leading-[15px] text-[#5A6F73] whitespace-pre-wrap">
                {illustrativeRecap.context}
              </p>
            </div>

            <span className="bg-[#F3EFE6] border border-[#E2DCD0] rounded-full px-[10px] py-1 text-[11.5px] font-medium leading-[14px] text-[#546A6E] shrink-0">
              {illustrativeRecap.badge}
            </span>
          </div>

          <div className="grid grid-cols-3 gap-3">
            {illustrativeRecap.kpis.map((kpi) => (
              <div
                key={kpi.label}
                className="bg-[#FAF8F3] border border-[#EBE6DC] rounded-[8px] px-3 py-[10px] flex flex-col gap-[2px]"
              >
                <span className="text-[11px] leading-[13px] text-[#5E7377]">
                  {kpi.label}
                </span>
                <span
                  className={[
                    'font-bold tabular-nums',
                    kpi.valueSize === 'lg'
                      ? 'text-[17px] leading-[21px]'
                      : 'text-[15px] leading-[18px]',
                    kpi.valueTone === 'open'
                      ? 'text-[#1D6353]'
                      : 'text-[#15333A]',
                  ].join(' ')}
                >
                  {kpi.value}
                </span>
                <span className="text-[10.5px] leading-[13px] text-[#6E8185]">
                  {kpi.note}
                </span>
              </div>
            ))}
          </div>

          <div className="flex flex-col">
            <div className="bg-[#F7F4ED] rounded-t-[6px] px-[10px] py-2 grid grid-cols-[110px_170px_minmax(0,1fr)_120px] items-center text-[11.5px] font-semibold leading-[14px] text-[#566B70]">
              <span>CPMK</span>
              <span>Pemetaan CPL</span>
              <span>Status</span>
              <span className="text-right">Capaian aktual</span>
            </div>

            <div className="divide-y divide-[#EFECE4]">
              {illustrativeRecap.rows.map((row) => (
                <div
                  key={row.code}
                  className="px-[10px] py-[9px] grid grid-cols-[110px_170px_minmax(0,1fr)_120px] items-center"
                >
                  <span className="text-[12.5px] font-semibold leading-[15px] text-[#15333A]">
                    {row.code}
                  </span>
                  <span className="text-[12.5px] leading-[15px] text-[#4A6166]">
                    {row.cpl}
                  </span>
                  <div>
                    <span
                      className={
                        row.complete
                          ? 'bg-[#E6F2EE] text-[#1A5C4D] rounded-full px-[9px] py-[3px] text-[11px] font-medium leading-[13px] inline-flex w-fit'
                          : 'bg-[#F7EAE1] text-[#B55824] rounded-full px-[9px] py-[3px] text-[11px] font-medium leading-[13px] inline-flex w-fit'
                      }
                    >
                      {row.status}
                    </span>
                  </div>
                  <span
                    className={
                      row.complete
                        ? 'text-right text-[13px] font-semibold leading-[16px] tabular-nums text-[#15333A]'
                        : 'text-right text-[14px] font-bold leading-[17px] text-[#B55824]'
                    }
                  >
                    {row.value}
                  </span>
                </div>
              ))}
            </div>
          </div>

          <p className="text-[11.5px] leading-[14px] text-[#687B7F]">
            {illustrativeRecap.footnote}
          </p>
        </aside>
      </div>
    </section>
  );
}
