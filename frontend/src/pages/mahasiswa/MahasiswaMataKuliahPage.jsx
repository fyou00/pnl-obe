import { Link } from 'react-router-dom';
import {
  EmptyTikState,
  LoadingSkeleton,
  LockedPeriodBanner,
} from '../../components/states/SystemStates.jsx';
import { useMahasiswaWorkspace } from '../../context/MahasiswaWorkspaceContext.jsx';

export default function MahasiswaMataKuliahPage() {
  const {
    periods,
    selectedPeriod,
    isTikOrInactive,
    classes,
    loadingWorkspace,
    workspaceError,
  } = useMahasiswaWorkspace();

  return (
    <div className="max-w-[1136px] flex flex-col gap-6">
      <div>
        <h1 className="text-[28px] font-semibold leading-[34px] text-[#15333A]">
          Mata Kuliah Saya
        </h1>
        <p className="text-[14px] text-[#566B70] mt-1.5">
          Daftar mata kuliah paket yang ditetapkan Program Studi berdasarkan kurikulum angkatan dan semester studi Anda (tanpa pengisian atau pembatalan KRS mandiri).
        </p>
      </div>

      <LockedPeriodBanner period={selectedPeriod} />

      {workspaceError && (
        <div
          role="alert"
          className="rounded-[10px] bg-[#FEF3F2] border border-[#FECDCA] px-4 py-3 text-[13px] text-[#B42318]"
        >
          {workspaceError}
        </div>
      )}

      {loadingWorkspace ? (
        <LoadingSkeleton variant="table" />
      ) : !selectedPeriod ? (
        <div className="bg-white border border-[#E4DFD4] rounded-[12px] p-6 text-[13px] text-[#566B70]">
          Belum ada data periode akademik.
        </div>
      ) : isTikOrInactive ? (
        <EmptyTikState
          period={selectedPeriod}
          classLabel={selectedPeriod.kelas}
          studentStatus={selectedPeriod.status_mahasiswa}
          hasOtherPeriods={periods.length > 1}
        />
      ) : (
        <section className="bg-white border border-[#E4DFD4] rounded-[12px] p-6 flex flex-col gap-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 className="text-[18px] font-semibold text-[#15333A]">
                Daftar Paket MK · {selectedPeriod.kelas} (
                {selectedPeriod.tahun_akademik} {selectedPeriod.semester})
              </h2>
              <p className="text-[12.5px] text-[#566B70] mt-0.5">
                Kurikulum {selectedPeriod.kode_kurikulum} ·{' '}
                {classes.length} mata kuliah terdaftar
              </p>
            </div>
          </div>

          {classes.length === 0 ? (
            <p className="text-[13px] text-[#566B70]">
              Belum ada paket mata kuliah yang diterapkan untuk kelas Anda pada periode ini.
            </p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="border-b border-[#E4DFD4] text-[11.5px] font-semibold text-[#566B70]">
                    <th className="py-3 pr-4">Kode MK</th>
                    <th className="py-3 pr-4">Nama Mata Kuliah</th>
                    <th className="py-3 pr-4">Kelas</th>
                    <th className="py-3 pr-4">Periode</th>
                    <th className="py-3 text-right">Aksi</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#EFECE4] text-[13px]">
                  {classes.map((cls) => (
                    <tr key={cls.id} className="hover:bg-[#FAF8F3]/70">
                      <td className="py-3 pr-4 font-semibold text-[#CC6E38] whitespace-nowrap">
                        {cls.kode_mk}
                      </td>
                      <td className="py-3 pr-4 font-medium text-[#15333A]">
                        {cls.nama_mk}
                      </td>
                      <td className="py-3 pr-4 text-[#334B51] whitespace-nowrap">
                        {cls.kelas}
                      </td>
                      <td className="py-3 pr-4 text-[#566B70] whitespace-nowrap">
                        {cls.tahun_akademik} {cls.semester}
                      </td>
                      <td className="py-3 text-right whitespace-nowrap">
                        <Link
                          to={`/mahasiswa/rincian?kelas=${cls.id}`}
                          className="inline-flex items-center h-8 px-3 rounded-[7px] bg-[#15333A] hover:bg-[#193A40] text-white text-[12px] font-semibold transition-colors"
                        >
                          Buka Rincian Nilai →
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      )}
    </div>
  );
}
