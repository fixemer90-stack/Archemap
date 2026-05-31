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

// ── Function colors (Archemap palette) ─────────────────────────────
const FUNCTION_COLORS: Record<string, string> = {
  Se: "bg-[#C28A2E]",
  Si: "bg-[#D8B45A]",
  Ne: "bg-[#8DA8FF]",
  Ni: "bg-[#5B3FD6]",
  Fe: "bg-[#B84A6B]",
  Fi: "bg-[#E57A7A]",
  Te: "bg-[#6BAFBD]",
  Ti: "bg-[#4A8A9A]",
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
    <span className="text-xs text-[#D8DCE8]">
      Уверенность: <span className="text-[#8DA8FF]">{label}</span>
    </span>
  );
}

// ── Top Types Component ────────────────────────────────────────────
export function SocionicsTopTypes({ types }: { types: SocionicsType[] }) {
  return (
    <div className="glass p-4">
      <h3 className="font-[family-name:var(--font-cormorant)] text-lg font-semibold mb-3 text-[#F6F1E8]">
        Соционический тип
      </h3>
      <div className="space-y-3">
        {types.map((t, i) => (
          <div
            key={t.type}
            className={`rounded-xl border p-4 ${
              i === 0
                ? "border-[rgba(91,63,214,0.40)] bg-[rgba(91,63,214,0.08)]"
                : "border-[rgba(216,220,232,0.10)] bg-[rgba(255,255,255,0.02)]"
            }`}
          >
            <div className="flex items-center justify-between">
              <div>
                <div className="flex items-center gap-2">
                  {i === 0 && (
                    <span className="text-xs font-medium text-[#D8B45A] px-2 py-0.5 rounded-full border border-[rgba(216,180,90,0.30)]">
                      Основной
                    </span>
                  )}
                  <span className="font-bold text-lg text-[#F6F1E8]">
                    {t.type}
                  </span>
                </div>
                <div className="text-sm text-[#D8DCE8] mt-1">{t.name}</div>
                <div className="text-xs text-[rgba(216,220,232,0.50)] mt-1">
                  Функции: {t.functions}
                </div>
              </div>
              <div className="text-right">
                <div className="text-2xl font-bold text-[#F6F1E8]">
                  {(t.score * 100).toFixed(1)}%
                </div>
                <ConfidenceLabel value={t.confidence} />
              </div>
            </div>
            {/* Score bar */}
            <div className="mt-3 h-2 rounded-full bg-[rgba(216,220,232,0.08)] overflow-hidden">
              <div
                className="h-full rounded-full bg-gradient-to-r from-[#5B3FD6] to-[#D8B45A] transition-all"
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
    <div className="glass p-4">
      <h3 className="font-[family-name:var(--font-cormorant)] text-lg font-semibold mb-3 text-[#F6F1E8]">
        Функциональный профиль
      </h3>
      <div className="space-y-2">
        {functions.map(([fn, value]) => (
          <div key={fn} className="space-y-1">
            <div className="flex items-center justify-between text-sm">
              <div className="flex items-center gap-2">
                <span className="font-mono font-medium text-[#D8B45A]">
                  {fn}
                </span>
                <span className="text-xs text-[rgba(216,220,232,0.50)]">
                  {FUNCTION_NAMES[fn]}
                </span>
              </div>
              <span className="font-mono text-[#F6F1E8]">
                {(value * 100).toFixed(1)}%
              </span>
            </div>
            <div className="h-2 rounded-full bg-[rgba(216,220,232,0.08)] overflow-hidden">
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
      <h3 className="font-[family-name:var(--font-cormorant)] text-lg font-semibold mb-3 text-[#F6F1E8]">
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
            stroke="#D8DCE8"
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
              stroke="#D8DCE8"
              strokeWidth={0.5}
              opacity={0.1}
            />
          );
        })}

        {/* Data polygon */}
        <path
          d={path}
          fill="#5B3FD6"
          fillOpacity={0.2}
          stroke="#5B3FD6"
          strokeWidth={2}
        />

        {/* Points */}
        {points.map((p) => (
          <circle key={p.fn} cx={p.x} cy={p.y} r={4} fill="#D8B45A" />
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
              fill="#D8DCE8"
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
