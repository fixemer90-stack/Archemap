import type { V2CalculationLayerViewModel } from "@/lib/astrotype-v2/report-view-model";
import { formatValue } from "./format";

interface V2AspectNetworkProps {
  network: V2CalculationLayerViewModel["aspectNetwork"];
}

export function V2AspectNetwork({ network }: V2AspectNetworkProps) {
  return (
    <section data-v2-calculation-block="aspect_network" className="space-y-4">
      <h3 className="text-xl font-semibold">Сеть ключевых аспектов</h3>
      <div className="grid gap-4 lg:grid-cols-[18rem_minmax(0,1fr)]">
        <div className="relative aspect-square rounded-full border border-[#D8B45A]/25 bg-white/[0.03] p-6">
          {network.nodes.slice(0, 12).map((node, index) => {
            const angle =
              (index / Math.max(1, network.nodes.length)) * Math.PI * 2;
            const x = 50 + Math.cos(angle) * 36;
            const y = 50 + Math.sin(angle) * 36;
            return (
              <div
                key={node.id}
                className="absolute -translate-x-1/2 -translate-y-1/2 rounded-full border border-[#D8B45A]/30 bg-[#111827] px-3 py-1 text-xs text-[#F5E9D0]"
                style={{ left: `${x}%`, top: `${y}%` }}
              >
                {node.label}
              </div>
            );
          })}
        </div>
        <div className="flex flex-wrap content-start gap-2">
          {network.edges.map((edge) => (
            <span
              key={`${edge.source}-${edge.target}-${edge.aspectCode}`}
              className="rounded-full border border-white/10 bg-white/[0.03] px-3 py-2 text-sm text-[#D8DCE8]"
            >
              {edge.source} → {edge.target} · {edge.aspectCode} · сила{" "}
              {formatValue(edge.strength)}
            </span>
          ))}
        </div>
      </div>
    </section>
  );
}
