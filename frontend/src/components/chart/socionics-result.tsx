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

// ── Function colors (Astrotype palette) ─────────────────────────────
const FUNCTION_COLORS: Record<string, string> = {
  Se: "bg-surface-subtle",
  Si: "bg-surface-subtle",
  Ne: "bg-surface-subtle",
  Ni: "bg-surface-subtle",
  Fe: "bg-surface-subtle",
  Fi: "bg-surface-subtle",
  Te: "bg-surface-subtle",
  Ti: "bg-surface-subtle",
};

// ── Confidence label ───────────────────────────────────────────────
function ConfidenceLabel({ value }: { value: number }) {
  const label =
    value >= 0.8
      ? "высокая"
      : value >= 0.6
        ? "средне-высокая"
        : value >= 0.4
          ? "средняя"
          : "низкая";

  return (
    <span className="text-xs text-text-secondary">
      Уверенность: <span className="text-link">{label}</span>
    </span>
  );
}

// ── Top Types Component ────────────────────────────────────────────
export function SocionicsTopTypes({ types }: { types: SocionicsType[] }) {
  return (
    <div className="glass p-4">
      <h3 className="font-[family-name:var(--font-cormorant)] text-lg font-semibold mb-3 text-text-primary">
        Соционический тип
      </h3>
      <div className="space-y-3">
        {types.map((t, i) => (
          <div
            key={t.type}
            className={`rounded-xl border p-4 ${
              i === 0
                ? "border-border-default bg-surface-subtle"
                : "border-border-default bg-surface-subtle"
            }`}
          >
            <div className="flex items-center justify-between">
              <div>
                <div className="flex items-center gap-2">
                  {i === 0 && (
                    <span className="text-xs font-medium text-accent-gold px-2 py-0.5 rounded-full border border-border-default">
                      Основной
                    </span>
                  )}
                  <span className="font-bold text-lg text-text-primary">
                    {t.type}
                  </span>
                </div>
                <div className="text-sm text-text-secondary mt-1">{t.name}</div>
                <div className="text-xs text-text-secondary mt-1">
                  Функции: {t.functions}
                </div>
              </div>
              <div className="text-right">
                <div className="text-2xl font-bold text-text-primary">
                  {((t.score ?? 0) * 100).toFixed(1)}%
                </div>
                <ConfidenceLabel value={t.confidence} />
              </div>
            </div>
            {/* Score bar */}
            <div className="mt-3 h-2 rounded-full bg-surface-subtle overflow-hidden">
              <div
                className="h-full rounded-full bg-gradient-to-r from-control to-accent-gold transition-all"
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
  if (!strengths) {
    return (
      <div className="glass p-4">
        <h3 className="font-[family-name:var(--font-cormorant)] text-lg font-semibold mb-3 text-text-primary">
          Функциональный профиль
        </h3>
        <p className="text-sm text-text-secondary">Данные загружаются...</p>
      </div>
    );
  }

  const functions = Object.entries(strengths).sort(([, a], [, b]) => b - a);

  return (
    <div className="glass p-4">
      <h3 className="font-[family-name:var(--font-cormorant)] text-lg font-semibold mb-3 text-text-primary">
        Функциональный профиль
      </h3>
      <div className="space-y-2">
        {functions.map(([fn, value]) => (
          <div key={fn} className="space-y-1">
            <div className="flex items-center justify-between text-sm">
              <div className="flex items-center gap-2">
                <span className="font-mono font-medium text-accent-gold">
                  {fn}
                </span>
                <span className="text-xs text-text-secondary">
                  {FUNCTION_NAMES[fn]}
                </span>
              </div>
              <span className="font-mono text-text-primary">
                {((value ?? 0) * 100).toFixed(1)}%
              </span>
            </div>
            <div className="h-2 rounded-full bg-surface-subtle overflow-hidden">
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
  if (!strengths) {
    return (
      <div className="glass p-4">
        <h3 className="font-[family-name:var(--font-cormorant)] text-lg font-semibold mb-3 text-text-primary">
          Радар функций
        </h3>
        <p className="text-sm text-text-secondary">Данные загружаются...</p>
      </div>
    );
  }

  const size = 200;
  const center = size / 2;
  const radius = size / 2 - 30;

  const functions = ["Se", "Ne", "Te", "Fe", "Si", "Ni", "Ti", "Fi"];
  const angleStep = (2 * Math.PI) / functions.length;

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

  const path =
    points.map((p, i) => `${i === 0 ? "M" : "L"} ${p.x} ${p.y}`).join(" ") +
    " Z";

  return (
    <div className="glass p-4">
      <h3 className="font-[family-name:var(--font-cormorant)] text-lg font-semibold mb-3 text-text-primary">
        Радар функций
      </h3>
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
            stroke="var(--text-secondary)"
            strokeWidth={0.5}
            opacity={0.15}
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
              stroke="var(--text-secondary)"
              strokeWidth={0.5}
              opacity={0.1}
            />
          );
        })}

        {/* Data polygon */}
        <path
          d={path}
          fill="var(--chart-series-1)"
          fillOpacity={0.2}
          stroke="var(--chart-series-1)"
          strokeWidth={2}
        />

        {/* Points */}
        {points.map((p) => (
          <circle
            key={p.fn}
            cx={p.x}
            cy={p.y}
            r={4}
            fill="var(--chart-series-2)"
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
              className="text-xs"
              fill="var(--text-secondary)"
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
  if (!data) {
    return (
      <div className="space-y-4">
        <div className="glass p-4">
          <p className="text-sm text-text-secondary">Данные загружаются...</p>
        </div>
      </div>
    );
  }

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
