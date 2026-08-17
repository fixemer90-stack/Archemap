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
      formatIndicator(indicators.ascendant),
      "первый дом, внешний стиль контакта и первичная реакция на мир",
    ],
    [
      "MC",
      formatIndicator(indicators.mc),
      "верх карты, публичная траектория и способ проявляться в деле",
    ],
    [
      "Управитель ASC",
      formatAscRuler(indicators.ascendantRuler),
      "как энергия асцендента уходит в действие, границы и партнёрство",
    ],
  ] as const;

  return (
    <section data-v2-calculation-block="key_indicators" className="mt-4 space-y-4">
      <div className="grid gap-3 md:grid-cols-3">
        {items.map(([label, primary, secondary]) => (
          <div
            key={label}
            className="rounded-[17px] border border-[#263046] bg-[#101622] p-[13px]"
          >
            <div className="text-[15px] font-semibold text-[#FFE2A1]">{label}</div>
            <div className="mt-2 text-[18px] font-semibold leading-tight text-[#F4EADB]">
              {formatValue(primary)}
            </div>
            <div className="mt-2 text-[12px] leading-[1.45] text-[#9FB0CC]">
              {formatValue(secondary)}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

function formatIndicator(indicator?: V2ChartIndicatorViewModel): string {
  if (!indicator) return "—";
  const parts = [indicator.sign, indicator.degreeLabel].filter(Boolean);
  return parts.join(" · ");
}

function formatAscRuler(indicator?: V2ChartIndicatorViewModel): string {
  if (!indicator) return "—";
  const position = indicator.position;
  const sign = position?.sign;
  const house = position?.houseNumber ? `${position.houseNumber} дом` : undefined;
  return [indicator.planet, sign ? `в ${sign}` : undefined, house]
    .filter(Boolean)
    .join(" ");
}
