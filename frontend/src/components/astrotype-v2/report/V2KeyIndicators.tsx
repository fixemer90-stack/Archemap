import type { V2ChartIndicatorViewModel } from "@/lib/astrotype-v2/report-view-model";
import { formatValue } from "./format";

interface V2KeyIndicatorsProps {
  indicators: {
    ascendant?: V2ChartIndicatorViewModel;
    mc?: V2ChartIndicatorViewModel;
    ascendantRuler?: V2ChartIndicatorViewModel;
  };
}

export function V2KeyIndicators({ indicators }: V2KeyIndicatorsProps) {
  const items = [
    [
      "Асцендент",
      indicators.ascendant?.degreeLabel,
      indicators.ascendant?.sign,
    ],
    ["MC", indicators.mc?.degreeLabel, indicators.mc?.sign],
    [
      "Управитель ASC",
      indicators.ascendantRuler?.planet,
      indicators.ascendantRuler?.position?.degreeLabel,
    ],
  ];
  return (
    <section data-v2-calculation-block="key_indicators" className="space-y-4">
      <h3 className="text-xl font-semibold">Карта и ключевые показатели</h3>
      <div className="grid gap-3 md:grid-cols-3">
        {items.map(([label, primary, secondary]) => (
          <div
            key={label}
            className="rounded-2xl border border-white/10 bg-white/[0.03] p-4"
          >
            <div className="text-xs uppercase tracking-[0.18em] text-[#D8B45A]">
              {label}
            </div>
            <div className="mt-3 text-lg font-semibold text-[#F5E9D0]">
              {formatValue(primary)}
            </div>
            <div className="mt-1 text-sm text-[#BFC6D8]">
              {formatValue(secondary)}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
