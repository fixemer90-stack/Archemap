import type { V2CalculationLayerViewModel } from "@/lib/astrotype-v2/report-view-model";
import { V2AspectNetwork } from "./V2AspectNetwork";
import { V2BalanceBars } from "./V2BalanceBars";
import { V2CalculationMatrix } from "./V2CalculationMatrix";
import { V2HouseEmphasis } from "./V2HouseEmphasis";
import { V2KeyAspectsTable } from "./V2KeyAspectsTable";
import { V2KeyIndicators } from "./V2KeyIndicators";
import { V2PlanetPositionsTable } from "./V2PlanetPositionsTable";

interface V2CalculationLayerProps {
  layer: V2CalculationLayerViewModel;
}

export function V2CalculationLayer({ layer }: V2CalculationLayerProps) {
  return (
    <section
      data-v2-reader-block="calculation_layer"
      className="space-y-[18px] text-[#F4EADB]"
    >
      <header className="rounded-[22px] border border-white/10 bg-[linear-gradient(180deg,rgba(255,255,255,0.055),rgba(255,255,255,0.025))] p-5 shadow-[0_20px_70px_rgba(0,0,0,0.3)] md:p-6">
        <div className="text-[13px] font-semibold uppercase tracking-[0.08em] text-[#D9B86F]">
          Расчётная основа
        </div>
        <h2 className="mt-3 text-[21px] font-semibold text-[#F4EADB] md:text-[28px]">
          Карта и ключевые показатели
        </h2>
        <V2KeyIndicators indicators={layer.keyIndicators} />
      </header>
      <div className="grid gap-[18px] xl:grid-cols-12">
        <div className="flex xl:col-span-8">
          <V2PlanetPositionsTable positions={layer.planetPositions} />
        </div>
        <div className="flex xl:col-span-4">
          <V2BalanceBars balanceBars={layer.balanceBars} />
        </div>
      </div>
      <div className="grid items-stretch gap-[18px] xl:grid-cols-12">
        <div className="flex w-full xl:col-span-6">
          <V2HouseEmphasis houseEmphasis={layer.houseEmphasis} />
        </div>
        <div className="flex w-full xl:col-span-6">
          <V2AspectNetwork network={layer.aspectNetwork} />
        </div>
      </div>
      <V2KeyAspectsTable aspects={layer.keyAspects} />
      <V2CalculationMatrix
        matrix={layer.calculationMatrix}
        aspects={layer.keyAspects}
      />
    </section>
  );
}
