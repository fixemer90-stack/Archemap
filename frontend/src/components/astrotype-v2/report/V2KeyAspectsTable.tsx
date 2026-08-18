import type { V2AspectViewModel } from "@/lib/astrotype-v2/report-view-model";
import { formatValue } from "./format";
import { V2GlossaryTerm } from "./V2GlossaryText";

interface V2KeyAspectsTableProps {
  aspects: V2AspectViewModel[];
}

export function V2KeyAspectsTable({ aspects }: V2KeyAspectsTableProps) {
  const toneFor = (aspectCode: string) =>
    ["trine", "sextile"].includes(aspectCode) ? "resource" : "tension";

  const labelFor = (aspectCode: string) =>
    ({
      conjunction: "соединение",
      opposition: "оппозиция",
      trine: "трин",
      square: "квадрат",
      sextile: "секстиль",
      quincunx: "квинконс",
    })[aspectCode] ?? aspectCode;

  const bodyLabel = (body: string) =>
    ({
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
    })[body] ?? body;

  return (
    <section data-v2-calculation-block="key_aspects" className="space-y-4">
      <h3 className="text-[21px] font-semibold text-[#F4EADB]">
        Ключевые аспекты
      </h3>
      <div className="overflow-x-auto rounded-[22px] border border-white/10 bg-[linear-gradient(180deg,rgba(255,255,255,0.055),rgba(255,255,255,0.025))] shadow-[0_20px_70px_rgba(0,0,0,0.3)]">
        <table className="w-full min-w-[640px] text-left text-sm">
          <thead className="text-[#C4CCDB]">
            <tr>
              <th className="px-4 py-3">Связка</th>
              <th className="px-4 py-3">
                <V2GlossaryTerm term="Аспект" />
              </th>
              <th className="px-4 py-3">
                <V2GlossaryTerm term="Орб" />
              </th>
              <th className="px-4 py-3">Тип</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[#2d3548] text-[#DCE4F3]">
            {aspects.map((aspect) => (
              <tr key={`${aspect.bodyA}-${aspect.bodyB}-${aspect.aspectCode}`}>
                <td className="px-4 py-3 text-[#F4EADB]">
                  {bodyLabel(aspect.bodyA)} — {bodyLabel(aspect.bodyB)}
                </td>
                <td className="px-4 py-3">{labelFor(aspect.aspectCode)}</td>
                <td className="px-4 py-3">{formatValue(aspect.orbDegrees)}°</td>
                <td className="px-4 py-3">
                  <span
                    className={
                      toneFor(aspect.aspectCode) === "resource"
                        ? "rounded-full bg-[rgba(111,168,255,0.15)] px-3 py-1 text-xs text-[#afd0ff]"
                        : "rounded-full bg-[rgba(255,111,131,0.14)] px-3 py-1 text-xs text-[#ffa3ae]"
                    }
                  >
                    {toneFor(aspect.aspectCode) === "resource"
                      ? "ресурс"
                      : "напряжение"}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
