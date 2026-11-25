import { Fragment } from 'react';
import { contextStripItems } from '../../data/landingContent.js';

export default function ContextStripSection() {
  return (
    <section
      aria-label="Konteks akademik"
      className="w-full bg-[#F3EFE6] border-y border-[#E3DDD1]"
    >
      <div className="max-w-[1440px] mx-auto px-[72px] min-h-[82px] flex items-center justify-between gap-6">
        {contextStripItems.map((item, index) => (
          <Fragment key={item.title}>
            {index > 0 && (
              <div
                className="w-px h-[34px] bg-[#DCD5C8] shrink-0"
                aria-hidden="true"
              />
            )}
            <div className="flex flex-col gap-[3px]">
              <h2 className="text-[13.5px] font-semibold leading-[16px] text-[#15333A]">
                {item.title}
              </h2>
              <p className="text-[12.5px] leading-[15px] text-[#53696E]">
                {item.subtitle}
              </p>
            </div>
          </Fragment>
        ))}
      </div>
    </section>
  );
}
