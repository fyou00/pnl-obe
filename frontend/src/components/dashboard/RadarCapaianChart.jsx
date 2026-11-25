import {
  PolarAngleAxis,
  PolarGrid,
  PolarRadiusAxis,
  Radar,
  RadarChart,
  ResponsiveContainer,
  Tooltip,
} from 'recharts';

export function formatIndonesianPercent(value) {
  if (value === null || value === undefined || value === '') {
    return '—';
  }
  const num = Number(value);
  if (Number.isNaN(num)) {
    return '—';
  }
  return `${num.toFixed(2).replace('.', ',')}%`;
}

export default function RadarCapaianChart({
  items = [],
  compact = false,
  emptyMessage = 'Belum ada data capaian untuk ditampilkan.',
}) {
  if (items.length === 0) {
    return (
      <div className="py-8 text-[13px] text-[#566B70]">{emptyMessage}</div>
    );
  }

  const numericItems = items.filter(
    (item) => item.capaian !== null && item.capaian !== undefined && item.capaian !== '',
  );
  const canRenderPolygon = numericItems.length >= 3;
  const missingCount = items.length - numericItems.length;

  const indexById = Object.fromEntries(
    items.map((item, idx) => [item.id, idx + 1]),
  );

  const chartData = numericItems.map((item) => ({
    axis: compact ? String(indexById[item.id]) : item.kode,
    kode: item.kode,
    label: item.label,
    nilai: Number(item.capaian),
  }));

  const strokeColor = '#15333A';
  const fillColor = 'rgba(21, 51, 58, 0.14)';
  const gridColor = '#E4DFD4';
  const tickColor = '#566B70';

  return (
    <div className="flex flex-col gap-3">
      <div
        className={
          compact
            ? 'flex flex-col gap-3 xl:grid xl:grid-cols-[152px_minmax(0,1fr)] xl:items-center xl:gap-4'
            : 'grid grid-cols-1 lg:grid-cols-[310px_minmax(0,1fr)] items-center gap-8'
        }
      >
        {canRenderPolygon ? (
          <div className={compact ? 'w-full h-[168px]' : 'w-full h-[270px]'}>
            <ResponsiveContainer width="100%" height="100%">
              <RadarChart
                cx="50%"
                cy="50%"
                outerRadius={compact ? '68%' : '74%'}
                data={chartData}
              >
                <PolarGrid stroke={gridColor} />
                <PolarAngleAxis
                  dataKey="axis"
                  tick={{ fill: tickColor, fontSize: compact ? 11 : 12 }}
                />
                <PolarRadiusAxis
                  angle={90}
                  domain={[0, 100]}
                  tick={false}
                  axisLine={false}
                />
                <Radar
                  name="Capaian aktual"
                  dataKey="nilai"
                  stroke={strokeColor}
                  strokeWidth={2}
                  fill={fillColor}
                  dot={{
                    r: compact ? 3 : 4,
                    fill: '#CC6E38',
                    stroke: '#FFFFFF',
                    strokeWidth: 1.5,
                  }}
                  activeDot={{
                    r: 5,
                    fill: '#B55824',
                    stroke: '#FFFFFF',
                    strokeWidth: 2,
                  }}
                />
                <Tooltip
                  formatter={(value) => [
                    formatIndonesianPercent(value),
                    'Capaian aktual',
                  ]}
                  labelFormatter={(label, payload) =>
                    payload?.[0]?.payload?.kode || label
                  }
                  contentStyle={{
                    backgroundColor: '#FFFFFF',
                    borderColor: '#E4DFD4',
                    borderRadius: 10,
                    fontSize: 12,
                    color: '#15333A',
                    boxShadow: '0 8px 24px rgba(21, 51, 58, 0.08)',
                  }}
                />
              </RadarChart>
            </ResponsiveContainer>
          </div>
        ) : (
          <div
            className={[
              'rounded-[10px] border border-dashed border-[#E4DFD4] bg-[#FAF8F3] flex flex-col items-center justify-center text-center px-3',
              compact ? 'h-[164px]' : 'h-[240px]',
            ].join(' ')}
          >
            <p className="text-[12px] font-semibold text-[#15333A]">
              Grafik radar menunggu kelengkapan data
            </p>
            <p className="text-[11px] text-[#566B70] mt-1">
              Minimal 3 item bernilai lengkap diperlukan ({numericItems.length}/
              {items.length} tersedia).
            </p>
          </div>
        )}

        <div className="flex flex-col gap-2.5 min-w-0">
          {items.map((item, idx) => {
            const hasValue =
              item.capaian !== null &&
              item.capaian !== undefined &&
              item.capaian !== '';
            return (
              <div
                key={item.id}
                className="flex items-center justify-between gap-3 text-[12px]"
              >
                <div className="flex items-center gap-2 min-w-0">
                  <span className="w-4 text-[#7A8C90] tabular-nums shrink-0">
                    {idx + 1}
                  </span>
                  <span className="font-semibold text-[#15333A] truncate">
                    {item.kode}
                  </span>
                </div>
                <span
                  className={
                    hasValue
                      ? 'tabular-nums font-medium text-[#15333A] shrink-0'
                      : 'text-[#B55824] font-medium shrink-0'
                  }
                >
                  {hasValue ? formatIndonesianPercent(item.capaian) : item.status}
                </span>
              </div>
            );
          })}
        </div>
      </div>

      {canRenderPolygon && missingCount > 0 && (
        <p className="text-[11px] text-[#566B70]">
          {missingCount} item berstatus belum lengkap tidak diplot (nilai belum
          lengkap tidak dianggap nol).
        </p>
      )}
    </div>
  );
}
