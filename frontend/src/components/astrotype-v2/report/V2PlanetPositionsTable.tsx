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
    <section
      data-v2-calculation-block="planet_positions"
      className="h-full w-full rounded-[22px] border border-border-default bg-[var(--hero-background)] p-5 shadow-elevated"
    >
      <h3 className="mb-4 text-[21px] font-semibold text-text-primary">
        Положения планет
      </h3>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[760px] text-left text-sm">
          <thead className="text-text-secondary">
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
          <tbody className="divide-y divide-[var(--border-default)] text-text-secondary">
            {orderedPositions.map((position) => (
              <tr key={position.body}>
                <td className="px-4 py-3 font-medium text-text-primary">
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
