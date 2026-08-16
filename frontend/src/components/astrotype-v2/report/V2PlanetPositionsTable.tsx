import type { V2PlanetPositionViewModel } from "@/lib/astrotype-v2/report-view-model";
import { formatValue } from "./format";

interface V2PlanetPositionsTableProps {
  positions: V2PlanetPositionViewModel[];
}

export function V2PlanetPositionsTable({
  positions,
}: V2PlanetPositionsTableProps) {
  return (
    <section data-v2-calculation-block="planet_positions" className="space-y-4">
      <h3 className="text-xl font-semibold">Положения планет</h3>
      <div className="overflow-x-auto rounded-2xl border border-white/10">
        <table className="w-full min-w-[760px] text-left text-sm">
          <thead className="bg-white/[0.04] text-[#D8B45A]">
            <tr>
              <th className="px-4 py-3">Точка</th>
              <th className="px-4 py-3">Знак</th>
              <th className="px-4 py-3">Дом</th>
              <th className="px-4 py-3">Градус</th>
              <th className="px-4 py-3">R</th>
              <th className="px-4 py-3">Ключевые аспекты</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/10 text-[#D8DCE8]">
            {positions.map((position) => (
              <tr key={position.body}>
                <td className="px-4 py-3 font-medium text-[#F5E9D0]">
                  {position.body}
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
                            `${aspect.bodyA}/${aspect.bodyB} ${aspect.aspectCode}`,
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
