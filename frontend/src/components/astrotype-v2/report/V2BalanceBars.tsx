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

const MODALITY_ORDER = ["mutable", "cardinal", "fixed"];

export function V2BalanceBars({ balanceBars }: V2BalanceBarsProps) {
  const entries = BALANCE_ORDER.flatMap((category) => {
    const rows = balanceBars[category];
    return rows
      ? ([[category, rows]] as Array<[string, V2BalanceBarViewModel[]]>)
      : [];
  });

  return (
    <section data-v2-calculation-block="balance_bars" className="h-full w-full">
      <div className="h-full rounded-[22px] border border-white/10 bg-[linear-gradient(180deg,rgba(255,255,255,0.055),rgba(255,255,255,0.025))] p-5 shadow-[0_20px_70px_rgba(0,0,0,0.3)]">
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
              {orderedBalanceRows(category, rows).map((row) => {
                const description = modalityDescription(row);
                return (
                  <div key={`${row.category}:${row.key}`}>
                    <div className="grid grid-cols-[128px_minmax(0,1fr)_46px] items-center gap-3">
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
                    {description && (
                      <p className="mt-[5px] pl-[128px] pr-[46px] text-[11px] leading-[1.35] text-[#7F8DA8] max-sm:pl-0 max-sm:pr-0">
                        {description}
                      </p>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

function orderedBalanceRows(
  category: string,
  rows: V2BalanceBarViewModel[],
): V2BalanceBarViewModel[] {
  if (category !== "modalities" && category !== "modality") {
    return rows;
  }
  return [...rows].sort(
    (left, right) => modalityOrderIndex(left) - modalityOrderIndex(right),
  );
}

function modalityOrderIndex(row: V2BalanceBarViewModel): number {
  const normalized = `${row.key} ${row.label}`.toLowerCase();
  const index = MODALITY_ORDER.findIndex((modality) =>
    normalized.includes(modality),
  );
  if (index >= 0) {
    return index;
  }
  if (normalized.includes("мутаб")) {
    return 0;
  }
  if (normalized.includes("кардин")) {
    return 1;
  }
  if (normalized.includes("фикс")) {
    return 2;
  }
  return MODALITY_ORDER.length;
}

function modalityDescription(row: V2BalanceBarViewModel): string | null {
  if (row.category !== "modalities" && row.category !== "modality") {
    return null;
  }
  const normalized = `${row.key} ${row.label}`.toLowerCase();
  if (normalized.includes("cardinal") || normalized.includes("кардин")) {
    return "Запускает движение: инициатива, первый шаг, быстрый разворот ситуации.";
  }
  if (normalized.includes("fixed") || normalized.includes("фикс")) {
    return "Удерживает форму: устойчивость, верность курсу, способность доводить до результата.";
  }
  if (normalized.includes("mutable") || normalized.includes("мутаб")) {
    return "Адаптирует процесс: гибкость, настройка под контекст, переход между этапами.";
  }
  return null;
}
