"use client";

// ── Types ──────────────────────────────────────────────────────────
interface SocionicsType {
  type: string;
  name: string;
  score: number;
  confidence: number;
  functions: string;
  model_a: number;
}

interface FunctionStrengths {
  Se: number;
  Si: number;
  Ne: number;
  Ni: number;
  Fe: number;
  Fi: number;
  Te: number;
  Ti: number;
}

interface SocionicsData {
  top3: SocionicsType[];
  function_strengths: FunctionStrengths;
}

// ── Function names ─────────────────────────────────────────────────
const FUNCTION_NAMES: Record<string, string> = {
  Se: "Экстравертная сенсорика",
  Si: "Интровертная сенсорика",
  Ne: "Экстравертная интуиция",
  Ni: "Интровертная интуиция",
  Fe: "Экстравертная этика",
  Fi: "Интровертная этика",
  Te: "Экстравертная логика",
  Ti: "Интровертная логика",
};

// ── Function colors ────────────────────────────────────────────────
const FUNCTION_COLORS: Record<string, string> = {
  Se: "bg-orange-500",
  Si: "bg-yellow-500",
  Ne: "bg-blue-500",
  Ni: "bg-purple-500",
  Fe: "bg-pink-500",
  Fi: "bg-rose-500",
  Te: "bg-green-500",
  Ti: "bg-emerald-500",
};

// ── Top Types Component ────────────────────────────────────────────
export function SocionicsTopTypes({ types }: { types: SocionicsType[] }) {
  return (
    <div className="rounded-lg border p-4">
      <h3 className="font-medium mb-3">Соционический тип</h3>
      <div className="space-y-3">
        {types.map((t, i) => (
          <div
            key={t.type}
            className={`rounded-md border p-3 ${
              i === 0 ? "border-primary bg-primary/5" : ""
            }`}
          >
            <div className="flex items-center justify-between">
              <div>
                <div className="flex items-center gap-2">
                  {i === 0 && (
                    <span className="text-xs font-medium text-primary">
                      Основной
                    </span>
                  )}
                  <span className="font-bold text-lg">{t.type}</span>
                </div>
                <div className="text-sm text-muted-foreground">{t.name}</div>
                <div className="text-xs text-muted-foreground mt-1">
                  Функции: {t.functions}
                </div>
              </div>
              <div className="text-right">
                <div className="text-2xl font-bold">
                  {(t.score * 100).toFixed(1)}%
                </div>
                <div className="text-xs text-muted-foreground">
                  Model A: {(t.model_a * 100).toFixed(1)}%
                </div>
              </div>
            </div>
            {/* Score bar */}
            <div className="mt-2 h-2 rounded-full bg-muted overflow-hidden">
              <div
                className="h-full rounded-full bg-primary transition-all"
                style={{ width: `${t.score * 100}%` }}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Function Profile Component ─────────────────────────────────────
export function FunctionProfile({
  strengths,
}: {
  strengths: FunctionStrengths;
}) {
  const functions = Object.entries(strengths).sort(([, a], [, b]) => b - a);

  return (
    <div className="rounded-lg border p-4">
      <h3 className="font-medium mb-3">Функциональный профиль</h3>
      <div className="space-y-2">
        {functions.map(([fn, value]) => (
          <div key={fn} className="space-y-1">
            <div className="flex items-center justify-between text-sm">
              <div className="flex items-center gap-2">
                <span className="font-mono font-medium">{fn}</span>
                <span className="text-xs text-muted-foreground">
                  {FUNCTION_NAMES[fn]}
                </span>
              </div>
              <span className="font-mono">{(value * 100).toFixed(1)}%</span>
            </div>
            <div className="h-2 rounded-full bg-muted overflow-hidden">
              <div
                className={`h-full rounded-full ${FUNCTION_COLORS[fn]} transition-all`}
                style={{ width: `${value * 100}%` }}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Radar Chart Component ──────────────────────────────────────────
export function FunctionRadar({ strengths }: { strengths: FunctionStrengths }) {
  const size = 200;
  const center = size / 2;
  const radius = size / 2 - 30;

  const functions = ["Se", "Ne", "Te", "Fe", "Si", "Ni", "Ti", "Fi"];
  const angleStep = (2 * Math.PI) / functions.length;

  // Calculate points
  const points = functions.map((fn, i) => {
    const angle = i * angleStep - Math.PI / 2;
    const value = strengths[fn as keyof FunctionStrengths];
    const r = radius * value;
    return {
      x: center + r * Math.cos(angle),
      y: center + r * Math.sin(angle),
      fn,
      value,
    };
  });

  // Create path
  const path =
    points.map((p, i) => `${i === 0 ? "M" : "L"} ${p.x} ${p.y}`).join(" ") +
    " Z";

  return (
    <div className="rounded-lg border p-4">
      <h3 className="font-medium mb-3">Радар функций</h3>
      <svg
        width={size}
        height={size}
        viewBox={`0 0 ${size} ${size}`}
        className="mx-auto"
      >
        {/* Background circles */}
        {[0.25, 0.5, 0.75, 1].map((scale) => (
          <circle
            key={scale}
            cx={center}
            cy={center}
            r={radius * scale}
            fill="none"
            stroke="currentColor"
            strokeWidth={0.5}
            className="text-border"
          />
        ))}

        {/* Axis lines */}
        {functions.map((_, i) => {
          const angle = i * angleStep - Math.PI / 2;
          return (
            <line
              key={i}
              x1={center}
              y1={center}
              x2={center + radius * Math.cos(angle)}
              y2={center + radius * Math.sin(angle)}
              stroke="currentColor"
              strokeWidth={0.5}
              className="text-border"
            />
          );
        })}

        {/* Data polygon */}
        <path
          d={path}
          fill="hsl(var(--primary))"
          fillOpacity={0.2}
          stroke="hsl(var(--primary))"
          strokeWidth={2}
        />

        {/* Points */}
        {points.map((p) => (
          <circle
            key={p.fn}
            cx={p.x}
            cy={p.y}
            r={4}
            fill="hsl(var(--primary))"
          />
        ))}

        {/* Labels */}
        {functions.map((fn, i) => {
          const angle = i * angleStep - Math.PI / 2;
          const labelR = radius + 20;
          const x = center + labelR * Math.cos(angle);
          const y = center + labelR * Math.sin(angle);
          return (
            <text
              key={fn}
              x={x}
              y={y}
              textAnchor="middle"
              dominantBaseline="central"
              className="text-xs fill-current text-muted-foreground"
            >
              {fn}
            </text>
          );
        })}
      </svg>
    </div>
  );
}

// ── Full Socionics Component ───────────────────────────────────────
export function SocionicsResult({ data }: { data: SocionicsData }) {
  return (
    <div className="space-y-4">
      <SocionicsTopTypes types={data.top3} />
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <FunctionProfile strengths={data.function_strengths} />
        <FunctionRadar strengths={data.function_strengths} />
      </div>
    </div>
  );
}
