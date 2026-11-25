import { measurementStages } from '../../data/landingContent.js';

export default function MeasurementFlowSection() {
  return (
    <section
      id="alur-pengukuran"
      className="w-full bg-[#FAF8F3] py-[72px]"
    >
      <div className="max-w-[1440px] mx-auto px-[72px] flex flex-col gap-[44px]">
        <div className="flex items-end justify-between gap-8">
          <div className="flex flex-col gap-[10px]">
            <p className="text-[12px] font-bold tracking-[0.08em] leading-[15px] text-[#CC6E38]">
              ALUR PENGUKURAN BOTTOM-UP
            </p>
            <h2 className="font-serif font-normal text-[42px] leading-[50px] text-[#15333A]">
              Bagaimana capaian diukur?
            </h2>
          </div>

          <p className="w-[440px] text-[15px] leading-[24px] text-[#4B6267]">
            Setiap angka capaian dihitung dari nilai mentah 0–100 di server
            sesuai bobot rancangan, tanpa pembulatan antara dan tanpa target
            buatan.
          </p>
        </div>

        <div className="grid grid-cols-4 gap-6">
          {measurementStages.map((stage) => {
            const isFeatured = stage.featured;

            return (
              <article
                key={stage.title}
                className={
                  isFeatured
                    ? 'min-h-[238px] rounded-[12px] overflow-hidden border bg-[#193A40] border-[#193A40] shadow-[0_8px_20px_rgba(21,51,58,0.10)] flex flex-col'
                    : 'min-h-[238px] rounded-[12px] overflow-hidden border bg-white border-[#E4DFD4] flex flex-col'
                }
              >
                <div
                  className="h-[3px] w-full shrink-0"
                  style={{ backgroundColor: stage.topBarColor }}
                  aria-hidden="true"
                />

                <div className="flex-1 px-6 py-[22px] flex flex-col justify-between">
                  <div className="flex flex-col gap-[14px]">
                    <div className="flex items-center justify-between">
                      {isFeatured ? (
                        <span className="rounded-full px-[10px] py-1 font-bold leading-none bg-[#CC6E38]/22 text-[#F3B389] text-[11px] tracking-[0.04em]">
                          {stage.badge}
                        </span>
                      ) : (
                        <span
                          className="rounded-full px-[10px] py-1 font-bold leading-none text-[12px]"
                          style={{
                            backgroundColor: stage.badgeBg,
                            color: stage.badgeText,
                          }}
                        >
                          {stage.badge}
                        </span>
                      )}

                      <span
                        className={
                          isFeatured
                            ? 'text-[16px] font-medium leading-none text-[#F0C3A4]'
                            : 'text-[20px] leading-none text-[#8B9D9B]'
                        }
                        aria-hidden="true"
                      >
                        {isFeatured ? '↗' : '→'}
                      </span>
                    </div>

                    <h3
                      className={
                        isFeatured
                          ? 'text-[22px] font-semibold leading-[27px] text-white'
                          : 'text-[22px] font-semibold leading-[27px] text-[#15333A]'
                      }
                    >
                      {stage.title}
                    </h3>

                    <p
                      className={
                        isFeatured
                          ? 'text-[14.5px] leading-[22px] text-[#D4E2DF]'
                          : 'text-[14.5px] leading-[22px] text-[#42595E]'
                      }
                    >
                      {stage.description}
                    </p>
                  </div>

                  <div className="flex flex-col gap-[10px] pt-4">
                    <div
                      className={
                        isFeatured
                          ? 'h-px w-full bg-[#2E5259]'
                          : 'h-px w-full bg-[#EFECE4]'
                      }
                      aria-hidden="true"
                    />
                    <p
                      className={
                        isFeatured
                          ? 'text-[12px] font-medium leading-[15px] text-[#9BB4B8]'
                          : 'text-[12px] font-medium leading-[15px] text-[#687C80]'
                      }
                    >
                      {stage.meta}
                    </p>
                  </div>
                </div>
              </article>
            );
          })}
        </div>
      </div>
    </section>
  );
}
