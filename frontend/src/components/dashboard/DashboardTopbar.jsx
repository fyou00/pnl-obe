import { useEffect, useState } from 'react';
import AnimatedNavIcon from '../icons/AnimatedNavIcon.jsx';

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
  topContextBadge = null,
}) {
  const [now, setNow] = useState(() => new Date());

  useEffect(() => {
    const timer = setInterval(() => {
      setNow(new Date());
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  const { timeText, dateText } = formatWibDateTime(now);
  const periodIdKey = selectedPeriod?.id || selectedPeriod?.periode_id || '';
  const periodStatus =
    selectedPeriod?.status || selectedPeriod?.status_periode || '';

  return (
    <header className="h-[64px] shrink-0 bg-white border-b border-[#E4DFD4] px-8 flex items-center justify-between gap-6">
      <div className="flex items-center gap-3 min-w-0">
        {showPeriodSelector ? (
          <>
            <label
              htmlFor="topbar-periode-select"
              className="text-[12.5px] font-medium text-[#566B70] whitespace-nowrap"
            >
              Periode akademik
            </label>
            <select
              id="topbar-periode-select"
              value={selectedPeriodId}
              onChange={(e) => onSelectPeriod?.(e.target.value)}
              disabled={periods.length === 0}
              className="h-[36px] min-w-[186px] px-3 rounded-[8px] bg-[#FAF8F3] border border-[#E4DFD4] text-[12.5px] font-semibold text-[#15333A] focus:outline-none focus:border-[#15333A] focus:bg-white disabled:opacity-60 transition-colors"
            >
              {periods.length === 0 ? (
                <option value="">Belum ada periode</option>
              ) : (
                periods.map((periode) => {
                  const optId = periode.id || periode.periode_id;
                  return (
                    <option key={optId} value={optId}>
                      {periode.tahun_akademik} {periode.semester}
                    </option>
                  );
                })
              )}
            </select>
            {periodIdKey && periodStatus && (
              <span
                className={[
                  'inline-flex items-center gap-1.5 h-7 px-2.5 rounded-full text-[11.5px] font-semibold whitespace-nowrap',
                  periodStatus === 'Dibuka'
                    ? 'bg-[#E6F2EE] text-[#1A5C4D]'
                    : 'bg-[#F7EAE1] text-[#B55824] border border-[#E8B899]',
                ].join(' ')}
              >
                {periodStatus !== 'Dibuka' && (
                  <AnimatedNavIcon name="lock" active size={12} />
                )}
                <span>{periodStatus}</span>
              </span>
            )}
            {topContextBadge}
          </>
        ) : (
          <div className="flex items-center gap-3">
            {leftContextLabel && (
              <span className="text-[13px] font-semibold text-[#566B70]">
                {leftContextLabel}
              </span>
            )}
            {topContextBadge}
          </div>
        )}
      </div>

      <div className="flex items-center shrink-0">
        <div className="min-w-[164px] text-right flex flex-col">
          <span className="text-[15px] font-semibold leading-[19px] tabular-nums text-[#15333A]">
            {timeText}
          </span>
          <span className="text-[11px] leading-[13px] text-[#566B70] mt-0.5">
            {dateText}
          </span>
        </div>
      </div>
    </header>
  );
}
