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
      className="space-y-8 rounded-[1.75rem] border border-[#D8B45A]/20 bg-[#0F172A] p-6 text-[#F5E9D0] md:p-8"
    >
      <header>
        <div className="text-xs font-semibold uppercase tracking-[0.22em] text-[#D8B45A]">
          Нижний расчётный слой
        </div>
        <h2 className="mt-3 text-2xl font-semibold md:text-4xl">
          Карта и ключевые показатели
        </h2>
        <p className="mt-4 max-w-3xl text-sm leading-7 text-[#BFC6D8]">
          Компактная deterministic-основа отчёта: положения, балансы, дома,
          аспекты и расчётные акценты карты. Здесь нет отдельного dashboard —
          только подложка к уже прочитанному портрету.
        </p>
      </header>
      <V2KeyIndicators indicators={layer.keyIndicators} />
      <V2PlanetPositionsTable positions={layer.planetPositions} />
      <V2BalanceBars balanceBars={layer.balanceBars} />
      <V2HouseEmphasis houseEmphasis={layer.houseEmphasis} />
      <V2AspectNetwork network={layer.aspectNetwork} />
      <V2KeyAspectsTable aspects={layer.keyAspects} />
      <V2CalculationMatrix matrix={layer.calculationMatrix} />
    </section>
  );
}
