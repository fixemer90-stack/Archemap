import type { V2PlanetPositionViewModel } from "@/lib/astrotype-v2/report-view-model";
import { formatValue } from "./format";
import { V2GlossaryTerm } from "./V2GlossaryText";

interface V2PlanetPositionsTableProps {
  positions: V2PlanetPositionViewModel[];
}

export function V2PlanetPositionsTable({
  positions,
}: V2PlanetPositionsTableProps) {
  const orderedPositions = [...positions].sort(
    (a, b) => sortRank(a.body) - sortRank(b.body),
  );

  return (
    <section data-v2-calculation-block="planet_positions" className="space-y-4">
      <h3 className="text-[21px] font-semibold text-[#F4EADB]">
        Положения планет
      </h3>
      <div className="overflow-x-auto rounded-[22px] border border-white/10 bg-[linear-gradient(180deg,rgba(255,255,255,0.055),rgba(255,255,255,0.025))] shadow-[0_20px_70px_rgba(0,0,0,0.3)]">
        <table className="w-full min-w-[760px] text-left text-sm">
          <thead className="text-[#C4CCDB]">
            <tr>
              <th className="px-4 py-3">
                <V2GlossaryTerm term="Планета" />
              </th>
              <th className="px-4 py-3">
                <V2GlossaryTerm term="Знак" />
              </th>
              <th className="px-4 py-3">
                <V2GlossaryTerm term="Дом" />
              </th>
              <th className="px-4 py-3">
                <V2GlossaryTerm term="Градус" />
              </th>
              <th className="px-4 py-3">
                <V2GlossaryTerm term="Ретроградность" />
              </th>
              <th className="px-4 py-3">Ключевые аспекты из выборки</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[#2d3548] text-[#DCE4F3]">
            {orderedPositions.map((position) => (
              <tr key={position.body}>
                <td className="px-4 py-3 font-medium text-[#F4EADB]">
                  {bodyLabel(position.body)}
                </td>
                <td className="px-4 py-3">{position.sign}</td>
                <td className="px-4 py-3">
                  {formatValue(position.houseNumber)}
                </td>
                <td className="px-4 py-3">{position.degreeLabel}</td>
                <td className="px-4 py-3">{position.retrograde ? "R" : "—"}</td>
                <td className="px-4 py-3">
                  {position.sampledAspects.length > 0
                    ? position.sampledAspects
                        .map(
                          (aspect) =>
                            `${otherBody(position.body, aspect)} ${aspectLabel(aspect.aspectCode)}`,
                        )
                        .join(", ")
                    : "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function bodyLabel(body: string): string {
  return (
    {
      Sun: "Солнце",
      Moon: "Луна",
      Mercury: "Меркурий",
      Venus: "Венера",
      Mars: "Марс",
      Jupiter: "Юпитер",
      Saturn: "Сатурн",
      Uranus: "Уран",
      Neptune: "Нептун",
      Pluto: "Плутон",
      Ascendant: "Асцендент",
      MC: "MC",
    }[body] ?? body
  );
}

function aspectLabel(aspectCode: string): string {
  return (
    {
      conjunction: "соединение",
      opposition: "оппозиция",
      trine: "трин",
      square: "квадрат",
      sextile: "секстиль",
      quincunx: "квинконс",
    }[aspectCode] ?? aspectCode
  );
}

function otherBody(
  body: string,
  aspect: V2PlanetPositionViewModel["sampledAspects"][number],
): string {
  const other = aspect.bodyA === body ? aspect.bodyB : aspect.bodyA;
  return bodyLabel(other);
}

function sortRank(body: string): number {
  return (
    {
      Sun: 0,
      Moon: 1,
      Mercury: 2,
      Venus: 3,
      Mars: 4,
      Jupiter: 5,
      Saturn: 6,
      Uranus: 7,
      Neptune: 8,
      Pluto: 9,
      Ascendant: 10,
      MC: 11,
    }[body] ?? 999
  );
}
