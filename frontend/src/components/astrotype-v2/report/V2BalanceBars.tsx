import type { V2BalanceBarViewModel } from "@/lib/astrotype-v2/report-view-model";
import { formatValue, percentWidth } from "./format";

interface V2BalanceBarsProps {
  balanceBars: Record<string, V2BalanceBarViewModel[]>;
}

const TITLES: Record<string, string> = {
  elements: "Баланс стихий",
  element: "Баланс стихий",
  modalities: "Баланс модальностей",
  modality: "Баланс модальностей",
};

export function V2BalanceBars({ balanceBars }: V2BalanceBarsProps) {
  return (
    <section
      data-v2-calculation-block="balance_bars"
      className="grid gap-4 md:grid-cols-2"
    >
      {Object.entries(balanceBars).map(([category, rows]) => (
        <div
          key={category}
          className="rounded-2xl border border-white/10 bg-white/[0.03] p-5"
        >
          <h3 className="text-xl font-semibold">
            {TITLES[category] ?? category}
          </h3>
          <div className="mt-4 space-y-3">
            {rows.map((row) => (
              <div key={`${row.category}:${row.key}`}>
                <div className="mb-1 flex justify-between text-sm text-[#D8DCE8]">
                  <span>{row.label}</span>
                  <span>{formatValue(row.value)}%</span>
                </div>
                <div className="h-2 rounded-full bg-white/10">
                  <div
                    className="h-2 rounded-full bg-[#D8B45A]"
                    style={{ width: percentWidth(row.value) }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
      ))}
    </section>
  );
}
