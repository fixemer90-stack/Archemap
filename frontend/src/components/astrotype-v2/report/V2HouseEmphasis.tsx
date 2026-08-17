import type { V2HouseEmphasisBarViewModel } from "@/lib/astrotype-v2/report-view-model";
import { percentWidth } from "./format";

interface V2HouseEmphasisProps {
  houseEmphasis: {
    bars: V2HouseEmphasisBarViewModel[];
    topHouses: V2HouseEmphasisBarViewModel[];
  };
}

const HOUSE_META: Record<number, { name: string; description: string }> = {
  1: { name: "Личность и старт", description: "внешний образ, тело, импульс к действию" },
  2: { name: "Ресурсы и опора", description: "деньги, ценности, устойчивость, телесная база" },
  3: { name: "Обучение и среда", description: "контакты, речь, повседневное мышление" },
  4: { name: "Дом и корни", description: "семья, база, внутренний фундамент" },
  5: { name: "Творчество и выражение", description: "игра, сцена, романтика, дети" },
  6: { name: "Режим и служение", description: "здоровье, рутина, рабочий процесс" },
  7: { name: "Отношения и партнёрство", description: "пары, договоры, зеркало другого человека" },
  8: { name: "Обмен и кризисы", description: "общие ресурсы, трансформация, глубина" },
  9: { name: "Смысл и горизонт", description: "образование, мировоззрение, путешествия, вера" },
  10: { name: "Статус и реализация", description: "карьера, репутация, способ проявиться в мире" },
  11: { name: "Сообщества и будущее", description: "друзья, группы, проекты, дальняя цель" },
  12: { name: "Подсознание и завершение", description: "изоляция, внутренние циклы, отпускание" },
};

export function V2HouseEmphasis({ houseEmphasis }: V2HouseEmphasisProps) {
  const max = Math.max(1, ...houseEmphasis.bars.map((bar) => bar.accentWeight));
  const topHouses = [...houseEmphasis.bars]
    .sort((a, b) => b.accentWeight - a.accentWeight || a.houseNumber - b.houseNumber)
    .slice(0, 4);

  return (
    <section data-v2-calculation-block="house_emphasis" className="space-y-4">
      <h3 className="text-[21px] font-semibold text-[#F4EADB]">Акцент домов</h3>
      <p className="text-[12px] leading-[1.45] text-[#9FB0CC]">
        Высота столбца показывает относительную насыщенность дома планетами с
        весами. Самый высокий столбец — главный акцент карты; остальные
        сравниваются с ним.
      </p>
      <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_18rem]">
        <div className="rounded-[22px] border border-[#263046] bg-[#101622] p-4">
          <div className="grid grid-cols-6 gap-2 md:grid-cols-12">
            {houseEmphasis.bars.map((bar) => (
              <div
                key={bar.houseNumber}
                className="flex h-40 flex-col items-center justify-end gap-2"
                title={`${bar.houseNumber} дом: ${Math.round((bar.accentWeight / max) * 100)}%`}
              >
                <div className="flex h-28 items-end">
                  <div
                    className="w-4 rounded-t bg-[linear-gradient(180deg,#f2d991,#d9b86f)]"
                    style={{
                      height: percentWidth((bar.accentWeight / max) * 100),
                    }}
                  />
                </div>
                <span className="text-xs text-[#BFC6D8]">{bar.houseNumber}</span>
              </div>
            ))}
          </div>
        </div>
        <div className="space-y-3">
          {topHouses.map((bar) => (
            <div
              key={bar.houseNumber}
              className="grid grid-cols-[58px_minmax(0,1fr)] gap-3 rounded-[16px] border border-[#263046] bg-[#101622] p-[14px]"
            >
              <div className="text-[18px] font-semibold text-[#FFE2A1]">
                {bar.houseNumber} дом
              </div>
              <div>
                <span className="block text-[13px] text-[#DCE4F3]">
                  {HOUSE_META[bar.houseNumber]?.name ?? bar.sign}
                </span>
                <span className="mt-1 block text-[12px] leading-[1.45] text-[#9FB0CC]">
                  {HOUSE_META[bar.houseNumber]?.description ?? `знак ${bar.sign}`}
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
