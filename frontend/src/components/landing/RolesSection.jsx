import { userRoles } from '../../data/landingContent.js';

export default function RolesSection() {
  return (
    <section id="peran-pengguna" className="w-full bg-[#193A40] py-[64px]">
      <div className="max-w-[1440px] mx-auto px-[72px] grid grid-cols-[410px_minmax(0,1fr)] gap-[66px] items-stretch">
        <div className="flex flex-col justify-between gap-8">
          <div className="flex flex-col gap-4">
            <p className="text-[12px] font-bold tracking-[0.08em] leading-[15px] text-[#E89B6C]">
              AKSES BERBASIS PERAN
            </p>
            <h2 className="font-serif font-normal text-[44px] leading-[52px] text-[#FCF8EE]">
              Siapa yang
              <br />
              menggunakannya?
            </h2>
            <p className="text-[15.5px] leading-[25px] text-[#B8CCCA]">
              Setiap peran memiliki ruang kerja dan batas akses tersendiri
              sesuai kewenangan akademik di program studi.
            </p>
          </div>

          <div className="bg-[#132E33] border border-[#2C5058] rounded-[10px] px-4 py-[14px] flex flex-col gap-1">
            <h3 className="text-[13px] font-semibold leading-[16px] text-white">
              Akses berbasis akun PNL (RBAC)
            </h3>
            <p className="text-[12.5px] leading-[19px] text-[#9BB4B8]">
              Aplikasi desktop internal · Tanpa pengisian KRS mandiri oleh
              mahasiswa.
            </p>
          </div>
        </div>

        <div className="border-y border-[#33575E] divide-y divide-[#33575E]">
          {userRoles.map((role) => (
            <div
              key={role.number}
              className="py-[22px] grid grid-cols-[210px_minmax(0,1fr)] gap-6 items-start"
            >
              <div className="flex flex-col gap-1">
                <span className="text-[12px] font-semibold leading-[15px] text-[#E89B6C]">
                  {role.number}
                </span>
                <h3 className="text-[20px] font-semibold leading-[24px] text-white">
                  {role.name}
                </h3>
              </div>

              <div className="flex flex-col gap-[10px]">
                <p className="text-[15px] leading-[23px] text-[#D6E2DF]">
                  {role.description}
                </p>
                <div className="flex flex-wrap gap-2">
                  {role.pills.map((pill) => (
                    <span
                      key={pill}
                      className="bg-[#22484F] text-[#B9D0CE] rounded-[6px] px-[10px] py-1 text-[12px] font-medium leading-[15px]"
                    >
                      {pill}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
