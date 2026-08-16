import type { V2HouseEmphasisBarViewModel } from "@/lib/astrotype-v2/report-view-model";
import { percentWidth } from "./format";

interface V2HouseEmphasisProps {
  houseEmphasis: {
    bars: V2HouseEmphasisBarViewModel[];
    topHouses: V2HouseEmphasisBarViewModel[];
  };
}

export function V2HouseEmphasis({ houseEmphasis }: V2HouseEmphasisProps) {
  const max = Math.max(1, ...houseEmphasis.bars.map((bar) => bar.accentWeight));
  return (
    <section data-v2-calculation-block="house_emphasis" className="space-y-4">
      <h3 className="text-xl font-semibold">Акцент домов</h3>
      <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_18rem]">
        <div className="grid grid-cols-6 gap-2 rounded-2xl border border-white/10 bg-white/[0.03] p-4 md:grid-cols-12">
          {houseEmphasis.bars.map((bar) => (
            <div
              key={bar.houseNumber}
              className="flex h-40 flex-col items-center justify-end gap-2"
            >
              <div className="flex h-28 items-end">
                <div
                  className="w-4 rounded-t bg-[#D8B45A]"
                  style={{
                    height: percentWidth((bar.accentWeight / max) * 100),
                  }}
                />
              </div>
              <span className="text-xs text-[#BFC6D8]">{bar.houseNumber}</span>
            </div>
          ))}
        </div>
        <div className="space-y-3">
          {houseEmphasis.topHouses.map((bar) => (
            <div
              key={bar.houseNumber}
              className="rounded-2xl border border-[#D8B45A]/20 bg-[#D8B45A]/10 p-4"
            >
              <div className="text-sm uppercase tracking-[0.18em] text-[#D8B45A]">
                Дом {bar.houseNumber}
              </div>
              <div className="mt-2 text-[#F5E9D0]">{bar.sign}</div>
              <div className="text-sm text-[#BFC6D8]">
                точек: {bar.bodyCount}
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
