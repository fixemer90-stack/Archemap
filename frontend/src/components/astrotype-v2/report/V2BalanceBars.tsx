import type { V2BalanceBarViewModel } from "@/lib/astrotype-v2/report-view-model";
import { formatValue, percentWidth } from "./format";
import { V2GlossaryTerm } from "./V2GlossaryText";

interface V2BalanceBarsProps {
  balanceBars: Record<string, V2BalanceBarViewModel[]>;
}

const TITLES: Record<string, string> = {
  elements: "Баланс стихий",
  element: "Баланс стихий",
  modalities: "Баланс модальностей",
  modality: "Баланс модальностей",
};

const BALANCE_ORDER = ["elements", "element", "modalities", "modality"];

export function V2BalanceBars({ balanceBars }: V2BalanceBarsProps) {
  const entries = BALANCE_ORDER.flatMap((category) => {
    const rows = balanceBars[category];
    return rows
      ? ([[category, rows]] as Array<[string, V2BalanceBarViewModel[]]>)
      : [];
  });

  return (
    <section data-v2-calculation-block="balance_bars">
      <div className="rounded-[22px] border border-white/10 bg-[linear-gradient(180deg,rgba(255,255,255,0.055),rgba(255,255,255,0.025))] p-5 shadow-[0_20px_70px_rgba(0,0,0,0.3)]">
        {entries.map(([category, rows], index) => (
          <div key={category}>
            <h3
              className={
                index > 0
                  ? "mt-6 text-[21px] font-semibold text-[#F4EADB]"
                  : "text-[21px] font-semibold text-[#F4EADB]"
              }
            >
              {category === "elements" || category === "element" ? (
                <>
                  Баланс <V2GlossaryTerm term="Стихия" />
                </>
              ) : category === "modalities" || category === "modality" ? (
                <>
                  Баланс <V2GlossaryTerm term="Модальность" />
                </>
              ) : (
                (TITLES[category] ?? category)
              )}
            </h3>
            {index === 0 && (
              <p className="mt-2 text-[12px] leading-[1.45] text-[#9FB0CC]">
                Метод: эвристические веса Astrotype v2; один и тот же вес каждой
                точки используется для стихий и модальностей. ASC и MC включены
                как углы карты.
              </p>
            )}
            <div className="mt-4 space-y-[13px]">
              {rows.map((row) => (
                <div
                  key={`${row.category}:${row.key}`}
                  className="grid grid-cols-[128px_minmax(0,1fr)_46px] items-center gap-3"
                >
                  <span className="text-[15px] text-[#DCE4F3]">
                    {row.label}
                  </span>
                  <div className="h-4 overflow-hidden rounded-[99px] border border-[#2c3548] bg-[#0b1019]">
                    <div
                      className="h-full bg-[linear-gradient(90deg,#d9b86f,#f2d991)]"
                      style={{ width: percentWidth(row.value) }}
                    />
                  </div>
                  <span className="text-right text-[15px] text-[#AEB6C7]">
                    {formatValue(row.value)}%
                  </span>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
