import type { V2CalculationLayerViewModel } from "@/lib/astrotype-v2/report-view-model";
import { formatValue } from "./format";

interface V2CalculationMatrixProps {
  matrix: V2CalculationLayerViewModel["calculationMatrix"];
}

function entries(value: unknown): Array<[string, unknown]> {
  return value && typeof value === "object" && !Array.isArray(value)
    ? Object.entries(value as Record<string, unknown>)
    : [];
}

export function V2CalculationMatrix({ matrix }: V2CalculationMatrixProps) {
  const groups = [
    ["Режим домов", matrix.houseMode],
    ["Полусферы", matrix.hemispheres],
    ["Квадранты", matrix.quadrants],
    ["Профиль аспектов", matrix.aspectProfile],
  ];
  return (
    <section
      data-v2-calculation-block="calculation_matrix"
      className="space-y-4"
    >
      <h3 className="text-xl font-semibold">Расчётные акценты карты</h3>
      <div className="grid gap-4 md:grid-cols-2">
        {groups.map(([title, value]) => (
          <div
            key={String(title)}
            className="rounded-2xl border border-white/10 bg-white/[0.03] p-5"
          >
            <h4 className="font-semibold text-[#F5E9D0]">{String(title)}</h4>
            <dl className="mt-3 space-y-2 text-sm text-[#D8DCE8]">
              {entries(value).map(([key, item]) => (
                <div key={key} className="flex justify-between gap-4">
                  <dt>{key}</dt>
                  <dd>
                    {typeof item === "object"
                      ? JSON.stringify(item)
                      : formatValue(item)}
                  </dd>
                </div>
              ))}
            </dl>
          </div>
        ))}
      </div>
    </section>
  );
}
