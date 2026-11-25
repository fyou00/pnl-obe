export default function BackendPendingNotice({
  title,
  description,
  missingEndpoints = [],
}) {
  return (
    <section className="bg-white dark:bg-[#1D1D1B] border border-[#E5E5E5] dark:border-[#2E2E2B] rounded-[12px] p-6 flex flex-col gap-4">
      <div className="flex items-start justify-between gap-4">
        <div className="flex flex-col gap-1">
          <h2 className="text-[17px] font-semibold text-[#252525] dark:text-[#F5F5F4]">
            {title}
          </h2>
          <p className="text-[13px] leading-[20px] text-[#737373] dark:text-[#A3A3A0]">
            {description}
          </p>
        </div>

        <span className="px-3 py-1 rounded-full bg-[#F0F0EF] dark:bg-[#2A2A27] border border-[#E5E5E5] dark:border-[#343430] text-[11px] font-medium text-[#525252] dark:text-[#D4D4D0] shrink-0">
          Menunggu endpoint backend
        </span>
      </div>

      {missingEndpoints.length > 0 && (
        <div className="border-t border-[#E5E5E5] dark:border-[#2E2E2B] pt-4 flex flex-col gap-2">
          <p className="text-[12px] font-medium text-[#525252] dark:text-[#D4D4D0]">
            Endpoint backend yang belum tersedia:
          </p>
          <ul className="list-disc pl-5 space-y-1 text-[12.5px] text-[#737373] dark:text-[#A3A3A0]">
            {missingEndpoints.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}
