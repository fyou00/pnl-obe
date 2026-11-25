import { useEffect, useState } from 'react';

function formatWibDateTime(date) {
  const timeParts = new Intl.DateTimeFormat('id-ID', {
    timeZone: 'Asia/Jakarta',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  }).formatToParts(date);

  const map = Object.fromEntries(timeParts.map((part) => [part.type, part.value]));
  const timeText = `${map.hour}:${map.minute}:${map.second} WIB`;

  const dateText = new Intl.DateTimeFormat('id-ID', {
    timeZone: 'Asia/Jakarta',
    weekday: 'long',
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  }).format(date);

  return { timeText, dateText };
}

export default function DashboardTopbar({
  showPeriodSelector = false,
  periods = [],
  selectedPeriodId = '',
  onSelectPeriod,
  selectedPeriod = null,
  leftContextLabel = '',
}) {
  const [now, setNow] = useState(() => new Date());

  useEffect(() => {
    const timer = setInterval(() => {
      setNow(new Date());
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  const { timeText, dateText } = formatWibDateTime(now);

  return (
    <header className="h-[80px] shrink-0 bg-white dark:bg-[#1D1D1B] border-b border-[#E5E5E5] dark:border-[#2E2E2B] px-8 flex items-center justify-between gap-6">
      <div className="flex items-center gap-4">
        {showPeriodSelector ? (
          <>
            <label
              htmlFor="topbar-periode-select"
              className="text-[13px] leading-[16px] text-[#737373] dark:text-[#A3A3A0]"
            >
              Periode akademik
            </label>
            <select
              id="topbar-periode-select"
              value={selectedPeriodId}
              onChange={(e) => onSelectPeriod?.(e.target.value)}
              disabled={periods.length === 0}
              className="h-[38px] min-w-[182px] px-3 rounded-[7px] bg-white dark:bg-[#242422] border border-[#E5E5E5] dark:border-[#343430] text-[12px] font-medium text-[#252525] dark:text-[#F5F5F4] focus:outline-none focus:ring-2 focus:ring-[#252525]/20 dark:focus:ring-[#F5F5F4]/20 disabled:opacity-60"
            >
              {periods.length === 0 ? (
                <option value="">Belum ada periode</option>
              ) : (
                periods.map((periode) => (
                  <option key={periode.id} value={periode.id}>
                    {periode.tahun_akademik} {periode.semester}
                  </option>
                ))
              )}
            </select>
            {selectedPeriod && (
              <span
                className={
                  selectedPeriod.status === 'Dibuka'
                    ? 'text-[12px] font-medium text-[#252525] dark:text-[#F5F5F4]'
                    : 'text-[12px] font-medium text-[#737373] dark:text-[#A3A3A0]'
                }
              >
                {selectedPeriod.status}
              </span>
            )}
          </>
        ) : (
          leftContextLabel && (
            <span className="text-[13px] font-medium text-[#737373] dark:text-[#A3A3A0]">
              {leftContextLabel}
            </span>
          )
        )}
      </div>

      <div className="flex items-center">
        <div className="min-w-[164px] flex flex-col">
          <span className="text-[17px] font-semibold leading-[21px] tabular-nums text-[#252525] dark:text-[#F5F5F4]">
            {timeText}
          </span>
          <span className="text-[11px] leading-[13px] text-[#737373] dark:text-[#A3A3A0] mt-1">
            {dateText}
          </span>
        </div>
      </div>
    </header>
  );
}
