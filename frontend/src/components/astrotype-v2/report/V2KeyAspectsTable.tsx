import type { V2AspectViewModel } from "@/lib/astrotype-v2/report-view-model";
import { formatValue } from "./format";

interface V2KeyAspectsTableProps {
  aspects: V2AspectViewModel[];
}

export function V2KeyAspectsTable({ aspects }: V2KeyAspectsTableProps) {
  return (
    <section data-v2-calculation-block="key_aspects" className="space-y-4">
      <h3 className="text-xl font-semibold">Ключевые аспекты</h3>
      <div className="overflow-x-auto rounded-2xl border border-white/10">
        <table className="w-full min-w-[640px] text-left text-sm">
          <thead className="bg-white/[0.04] text-[#D8B45A]">
            <tr>
              <th className="px-4 py-3">Пара</th>
              <th className="px-4 py-3">Аспект</th>
              <th className="px-4 py-3">Орб</th>
              <th className="px-4 py-3">Тип</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/10 text-[#D8DCE8]">
            {aspects.map((aspect) => (
              <tr key={`${aspect.bodyA}-${aspect.bodyB}-${aspect.aspectCode}`}>
                <td className="px-4 py-3 text-[#F5E9D0]">
                  {aspect.bodyA} / {aspect.bodyB}
                </td>
                <td className="px-4 py-3">{aspect.aspectCode}</td>
                <td className="px-4 py-3">{formatValue(aspect.orbDegrees)}°</td>
                <td className="px-4 py-3">
                  <span className="rounded-full border border-[#D8B45A]/25 px-3 py-1 text-xs text-[#D8B45A]">
                    {aspect.applying ? "сходящийся" : "расходящийся"}
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
