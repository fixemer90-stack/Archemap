import type {
  V2AspectNodeViewModel,
  V2CalculationLayerViewModel,
} from "@/lib/astrotype-v2/report-view-model";
interface V2AspectNetworkProps {
  network: V2CalculationLayerViewModel["aspectNetwork"];
}

interface PositionedNode extends V2AspectNodeViewModel {
  x: number;
  y: number;
  shortLabel: string;
}

const CENTER = 210;
const RADIUS = 150;
const NODE_LIMIT = 12;
const EDGE_LIMIT = 16;

export function V2AspectNetwork({ network }: V2AspectNetworkProps) {
  const nodes = positionNodes(network.nodes.slice(0, NODE_LIMIT));
  const nodeById = new Map(nodes.map((node) => [node.id.toLowerCase(), node]));
  const edges = network.edges
    .filter(
      (edge) =>
        nodeById.has(edge.source.toLowerCase()) &&
        nodeById.has(edge.target.toLowerCase()),
    )
    .sort((a, b) => (b.strength ?? 0) - (a.strength ?? 0))
    .slice(0, EDGE_LIMIT);

  return (
    <section
      data-v2-calculation-block="aspect_network"
      className="h-full min-h-[600px] w-full rounded-[22px] border border-white/10 bg-[linear-gradient(180deg,rgba(255,255,255,0.055),rgba(255,255,255,0.025))] p-5 shadow-[0_20px_70px_rgba(0,0,0,0.3)] max-[1100px]:min-h-0"
    >
      <h3 className="mb-[14px] text-[21px] font-semibold leading-tight text-[#F4EADB]">
        Сеть ключевых аспектов
      </h3>
      <div className="flex min-h-[500px] items-center justify-center max-[1100px]:min-h-0">
        <div className="w-full max-w-[420px]">
          <svg
            className="h-auto w-full"
            width="420"
            height="420"
            viewBox="0 0 420 420"
            role="img"
            aria-label="Сеть ключевых аспектов натальной карты"
          >
            <defs>
              <filter
                id="v2-aspect-node-shadow"
                x="-50%"
                y="-50%"
                width="200%"
                height="200%"
              >
                <feDropShadow
                  dx="0"
                  dy="8"
                  stdDeviation="8"
                  floodColor="#000000"
                  floodOpacity="0.35"
                />
              </filter>
            </defs>
            <circle
              cx={CENTER}
              cy={CENTER}
              r={RADIUS}
              fill="none"
              stroke="#252d3d"
              strokeWidth="1.5"
            />
            <circle
              cx={CENTER}
              cy={CENTER}
              r="106"
              fill="none"
              stroke="#1b2434"
              strokeDasharray="4 8"
            />
            {edges.map((edge) => {
              const source = nodeById.get(edge.source.toLowerCase());
              const target = nodeById.get(edge.target.toLowerCase());
              if (!source || !target) return null;
              const tone = aspectTone(edge.aspectCode);
              return (
                <line
                  key={`${edge.source}-${edge.target}-${edge.aspectCode}`}
                  x1={source.x}
                  y1={source.y}
                  x2={target.x}
                  y2={target.y}
                  className={
                    tone === "resource" ? "asp-resource" : "asp-tension"
                  }
                  stroke={tone === "resource" ? "#6fa8ff" : "#ff6f83"}
                  strokeLinecap="round"
                  strokeOpacity="0.78"
                  strokeWidth={strokeWidth(edge.strength)}
                />
              );
            })}
            {nodes.map((node) => (
              <g
                key={node.id}
                className="node"
                filter="url(#v2-aspect-node-shadow)"
              >
                <circle
                  cx={node.x}
                  cy={node.y}
                  r="22"
                  fill="#111827"
                  stroke="#d9b86f"
                  strokeOpacity="0.65"
                />
                <text
                  x={node.x}
                  y={node.y + 4}
                  textAnchor="middle"
                  className="fill-[#F5E9D0] text-[12px] font-semibold"
                >
                  {node.shortLabel}
                </text>
              </g>
            ))}
          </svg>
        </div>
      </div>
    </section>
  );
}

function positionNodes(nodes: V2AspectNodeViewModel[]): PositionedNode[] {
  return nodes.map((node, index) => {
    const angle =
      -Math.PI / 2 + (index / Math.max(1, nodes.length)) * Math.PI * 2;
    return {
      ...node,
      x: round(CENTER + Math.cos(angle) * RADIUS),
      y: round(CENTER + Math.sin(angle) * RADIUS),
      shortLabel: shortBodyLabel(node.label || node.id),
    };
  });
}

function strokeWidth(strength: number | null): number {
  const value = strength ?? 0.5;
  return round(2.2 + Math.max(0, Math.min(1, value)) * 3.2);
}

function aspectTone(aspectCode: string): "resource" | "tension" {
  return ["trine", "sextile"].includes(aspectCode) ? "resource" : "tension";
}

function shortBodyLabel(body: string): string {
  const label = bodyLabel(body);
  if (label === "MC") return "MC";
  return label.slice(0, 3);
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
      Lilith: "Лилит",
      "North Node": "Северный узел",
      Ascendant: "Асцендент",
      MC: "MC",
    }[body] ?? body
  );
}

function round(value: number): number {
  return Number(value.toFixed(1));
}
