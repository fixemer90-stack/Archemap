import type {
  V2AspectNodeViewModel,
  V2CalculationLayerViewModel,
} from "@/lib/astrotype-v2/report-view-model";
import {
  aspectTone,
  formatValue,
  localizeAspectLabel,
  localizeAstroLabel,
} from "./format";
import { V2GlossaryTerm } from "./V2GlossaryText";
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

export function V2AspectNetwork({ network }: V2AspectNetworkProps) {
  const nodes = positionNodes(network.nodes);
  const nodeById = new Map(nodes.map((node) => [node.id.toLowerCase(), node]));
  const edges = network.edges.filter(
    (edge) =>
      nodeById.has(edge.source.toLowerCase()) &&
      nodeById.has(edge.target.toLowerCase()),
  );

  return (
    <section
      data-v2-calculation-block="aspect_network"
      className="w-full rounded-[22px] border border-border-default [background:var(--hero-background)] p-5 shadow-elevated"
    >
      <h3 className="mb-[14px] text-[21px] font-semibold leading-tight text-text-primary">
        <V2GlossaryTerm term="Сеть ключевых аспектов" />
      </h3>
      <div
        data-aspect-legend
        className="mb-3 flex flex-wrap gap-x-5 gap-y-2 text-[12px] text-text-secondary"
        aria-label="Легенда типов аспектов"
      >
        <LegendItem tone="resource" label="Ресурсная связь" />
        <LegendItem tone="tension" label="Напряжённая связь" />
        <span>Толщина линии показывает силу связи</span>
      </div>
      <div className="flex items-center justify-center">
        <div className="w-full max-w-[420px]">
          <svg
            className="h-auto w-full"
            width="420"
            height="420"
            viewBox="0 0 420 420"
            role="group"
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
                  floodColor="var(--scrim)"
                  floodOpacity="0.35"
                />
              </filter>
            </defs>
            <circle
              cx={CENTER}
              cy={CENTER}
              r={RADIUS}
              fill="none"
              stroke="var(--border-default)"
              strokeWidth="1.5"
            />
            <circle
              cx={CENTER}
              cy={CENTER}
              r="106"
              fill="none"
              stroke="var(--surface)"
              strokeDasharray="4 8"
            />
            {edges.map((edge) => {
              const source = nodeById.get(edge.source.toLowerCase());
              const target = nodeById.get(edge.target.toLowerCase());
              if (!source || !target) return null;
              const tone = aspectTone(edge.aspectCode);
              const edgeLabel = `${source.label} — ${target.label}: ${localizeAspectLabel(edge.aspectCode)}, ${tone === "resource" ? "ресурс" : "напряжение"}, сила ${formatValue(edge.strength)}, орб ${formatValue(edge.orbDegrees)}°`;
              return (
                <g
                  key={`${edge.source}-${edge.target}-${edge.aspectCode}`}
                  data-aspect-edge={`${edge.source}|${edge.target}|${edge.aspectCode}`}
                  role="img"
                  aria-label={edgeLabel}
                >
                  <title>{edgeLabel}</title>
                  <line
                    x1={source.x}
                    y1={source.y}
                    x2={target.x}
                    y2={target.y}
                    className={
                      tone === "resource" ? "asp-resource" : "asp-tension"
                    }
                    stroke={
                      tone === "resource"
                        ? "var(--chart-fill-resource)"
                        : "var(--chart-fill-tension)"
                    }
                    strokeDasharray={tone === "resource" ? undefined : "9 5"}
                    strokeLinecap="round"
                    strokeOpacity="0.9"
                    strokeWidth={strokeWidth(edge.strength)}
                  />
                </g>
              );
            })}
            {nodes.map((node) => (
              <g
                key={node.id}
                className="node outline-none focus-visible:[filter:drop-shadow(0_0_8px_var(--focus-ring))]"
                filter="url(#v2-aspect-node-shadow)"
                tabIndex={0}
                role="img"
                aria-label={`${node.label}${node.sign ? `, знак ${node.sign}` : ""}${node.houseNumber ? `, ${node.houseNumber} дом` : ""}`}
              >
                <title>{node.label}</title>
                <circle
                  cx={node.x}
                  cy={node.y}
                  r="22"
                  fill="var(--chart-fill-node)"
                  stroke="var(--chart-fill-bar-end)"
                  strokeOpacity="0.9"
                />
                <text
                  x={node.x}
                  y={node.y + 4}
                  textAnchor="middle"
                  fill="var(--text-inverse)"
                  className="pointer-events-none text-[12px] font-semibold"
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

function LegendItem({
  tone,
  label,
}: {
  tone: "resource" | "tension";
  label: string;
}) {
  return (
    <span className="inline-flex items-center gap-2">
      <span
        aria-hidden="true"
        className="inline-block h-0 w-8 rounded-full border-t-[3px]"
        style={{
          borderColor:
            tone === "resource"
              ? "var(--chart-fill-resource)"
              : "var(--chart-fill-tension)",
          borderStyle: tone === "resource" ? "solid" : "dashed",
        }}
      />
      {label}
    </span>
  );
}

function strokeWidth(strength: number | null): number {
  const value = strength ?? 0.5;
  return round(2.2 + Math.max(0, Math.min(1, value)) * 3.2);
}

function shortBodyLabel(body: string): string {
  const label = localizeAstroLabel(body);
  if (label === "MC") return "MC";
  return label.slice(0, 3);
}

function round(value: number): number {
  return Number(value.toFixed(1));
}
