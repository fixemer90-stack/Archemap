import type { V2HouseEmphasisBarViewModel } from "@/lib/astrotype-v2/report-view-model";
import { percentWidth } from "./format";

interface V2HouseEmphasisProps {
  houseEmphasis: {
    bars: V2HouseEmphasisBarViewModel[];
    topHouses: V2HouseEmphasisBarViewModel[];
  };
}

const HOUSE_META: Record<number, { name: string; description: string }> = {
  1: {
    name: "Личность и старт",
    description: "внешний образ, тело, импульс к действию",
  },
  2: {
    name: "Ресурсы и опора",
    description: "деньги, ценности, устойчивость, телесная база",
  },
  3: {
    name: "Обучение и среда",
    description: "контакты, речь, повседневное мышление",
  },
  4: { name: "Дом и корни", description: "семья, база, внутренний фундамент" },
  5: {
    name: "Творчество и выражение",
    description: "игра, сцена, романтика, дети",
  },
  6: {
    name: "Режим и служение",
    description: "здоровье, рутина, рабочий процесс",
  },
  7: {
    name: "Отношения и партнёрство",
    description: "пары, договоры, зеркало другого человека",
  },
  8: {
    name: "Обмен и кризисы",
    description: "общие ресурсы, трансформация, глубина",
  },
  9: {
    name: "Смысл и горизонт",
    description: "образование, мировоззрение, путешествия, вера",
  },
  10: {
    name: "Статус и реализация",
    description: "карьера, репутация, способ проявиться в мире",
  },
  11: {
    name: "Сообщества и будущее",
    description: "друзья, группы, проекты, дальняя цель",
  },
  12: {
    name: "Подсознание и завершение",
    description: "изоляция, внутренние циклы, отпускание",
  },
};

export function V2HouseEmphasis({ houseEmphasis }: V2HouseEmphasisProps) {
  const max = Math.max(1, ...houseEmphasis.bars.map((bar) => bar.accentWeight));
  const topHouses = [...houseEmphasis.bars]
    .sort(
      (a, b) =>
        b.accentWeight - a.accentWeight || a.houseNumber - b.houseNumber,
    )
    .slice(0, 4);

  return (
    <section
      data-v2-calculation-block="house_emphasis"
      className="h-full min-h-[600px] rounded-[22px] border border-border-default bg-[var(--hero-background)] p-5 shadow-elevated max-[1100px]:min-h-0"
    >
      <h3 className="mb-[14px] text-[21px] font-semibold leading-tight text-text-primary">
        Акцент домов
      </h3>
      <p className="mb-3 text-[15px] leading-[1.5] text-text-secondary">
        Высота столбца показывает относительную насыщенность дома планетами с
        весами. Самый высокий столбец — главный акцент карты; остальные
        сравниваются с ним.
      </p>

      <div className="mt-[14px] flex h-[220px] items-end gap-[10px] border-b border-border-default">
        {houseEmphasis.bars.map((bar) => {
          const value = (bar.accentWeight / max) * 100;
          return (
            <div
              key={bar.houseNumber}
              className="relative flex h-[190px] min-w-0 flex-1 items-end overflow-hidden rounded-t-[10px] bg-surface-subtle"
              title={`${bar.houseNumber} дом: ${Math.round(value)}%`}
            >
              <span
                className="block min-h-[28px] w-full bg-[var(--hero-background)]"
                style={{ height: percentWidth(value) }}
              />
              <b className="absolute inset-x-0 bottom-[7px] z-20 text-center text-[12px] font-extrabold text-text-primary [text-shadow:0_1px_3px_var(--scrim)]">
                {bar.houseNumber}
              </b>
              <span className="pointer-events-none absolute inset-x-0 bottom-0 z-10 h-[30px] bg-[var(--hero-background)]" />
            </div>
          );
        })}
      </div>

      <div className="mt-[18px] grid gap-2 md:grid-cols-2">
        {topHouses.map((bar) => (
          <div
            key={bar.houseNumber}
            className="grid min-h-[78px] min-w-0 grid-cols-[42px_minmax(0,1fr)] items-start gap-[10px] rounded-[13px] border border-border-default bg-surface-subtle p-[10px]"
          >
            <div className="font-extrabold text-accent-gold">
              {bar.houseNumber} дом
            </div>
            <div className="min-w-0">
              <span className="block [overflow-wrap:anywhere] text-text-primary">
                {HOUSE_META[bar.houseNumber]?.name ?? bar.sign}
              </span>
              <span className="block [overflow-wrap:anywhere] text-[12px] leading-[1.5] text-text-secondary">
                {HOUSE_META[bar.houseNumber]?.description ?? `знак ${bar.sign}`}
              </span>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
