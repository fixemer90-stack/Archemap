"use client";

import {
  aspectDirectionRu,
  aspectTypeRu,
  PLANET_SYMBOLS,
  planetNameRu,
  SIGN_SYMBOLS,
  signNameRu,
} from "@/lib/astrology/labels";

// ── Types ──────────────────────────────────────────────────────────
interface Planet {
  name: string;
  sign: string;
  degree: number;
  sign_degree?: number;
  longitude?: number;
  house: number | null;
  is_retrograde: boolean;
}

interface House {
  number: number;
  sign: string;
  longitude: number;
}

interface Aspect {
  planet_a: string;
  aspect_type: string;
  planet_b: string;
  orb: number;
  is_applying: boolean;
}

interface ChartData {
  planets: Planet[];
  houses: House[];
  aspects: Aspect[];
}

// ── Aspect colors ──────────────────────────────────────────────────
const ASPECT_COLORS: Record<string, string> = {
  conjunction: "text-error",
  opposition: "text-error",
  trine: "text-product-child",
  sextile: "text-link",
  square: "text-accent-gold",
  quincunx: "text-text-secondary",
};

// ── Chart Planets Component ────────────────────────────────────────
export function ChartPlanets({ planets }: { planets: Planet[] }) {
  return (
    <div className="glass p-4">
      <h3 className="font-[family-name:var(--font-cormorant)] text-lg font-semibold mb-3 text-text-primary">
        Планеты
      </h3>
      <div className="space-y-2">
        {planets.map((planet) => (
          <div
            key={planet.name}
            className="flex items-center justify-between text-sm"
          >
            <div className="flex items-center gap-2">
              <span className="text-lg text-accent-gold">
                {PLANET_SYMBOLS[planet.name] || "?"}
              </span>
              <span className="font-medium text-text-primary">
                {planetNameRu(planet.name)}
              </span>
              {planet.is_retrograde && (
                <span className="text-xs text-error">℞</span>
              )}
            </div>
            <div className="flex items-center gap-2">
              <span className="text-link">
                {SIGN_SYMBOLS[planet.sign] || "?"}
              </span>
              <span className="text-text-secondary">
                {signNameRu(planet.sign)}
              </span>
              <span className="font-mono text-xs text-text-secondary">
                {(planet.degree ?? planet.sign_degree ?? 0).toFixed(2)}°
              </span>
              {planet.house && (
                <span className="text-xs text-text-secondary">
                  Дом {planet.house}
                </span>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Chart Houses Component ─────────────────────────────────────────
export function ChartHouses({ houses }: { houses: House[] }) {
  return (
    <div className="glass p-4">
      <h3 className="font-[family-name:var(--font-cormorant)] text-lg font-semibold mb-3 text-text-primary">
        Дома
      </h3>
      <div className="grid grid-cols-2 gap-2">
        {houses.map((house) => (
          <div
            key={house.number}
            className="flex items-center justify-between text-sm"
          >
            <span className="text-text-secondary">Дом {house.number}</span>
            <div className="flex items-center gap-1">
              <span className="text-link">
                {SIGN_SYMBOLS[house.sign] || "?"}
              </span>
              <span className="font-mono text-xs text-text-secondary">
                {(house.longitude ?? 0).toFixed(2)}°
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Chart Aspects Component ────────────────────────────────────────
export function ChartAspects({ aspects }: { aspects: Aspect[] }) {
  return (
    <div className="glass p-4">
      <h3 className="font-[family-name:var(--font-cormorant)] text-lg font-semibold mb-3 text-text-primary">
        Аспекты
      </h3>
      <div className="space-y-1">
        {aspects.map((aspect, i) => (
          <div key={i} className="flex items-center justify-between text-sm">
            <div className="flex items-center gap-2">
              <span className="font-medium text-text-primary">
                {planetNameRu(aspect.planet_a)}
              </span>
              <span
                className={
                  ASPECT_COLORS[aspect.aspect_type] || "text-text-secondary"
                }
              >
                {aspectTypeRu(aspect.aspect_type)}
              </span>
              <span className="font-medium text-text-primary">
                {planetNameRu(aspect.planet_b)}
              </span>
            </div>
            <div className="flex items-center gap-2">
              <span className="font-mono text-xs text-text-secondary">
                орб: {(aspect.orb ?? 0).toFixed(2)}°
              </span>
              <span className="text-xs text-text-secondary">
                {aspectDirectionRu(aspect.is_applying)}
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Chart Wheel (SVG) ──────────────────────────────────────────────
export function ChartWheel({ chart }: { chart: ChartData }) {
  const size = 300;
  const center = size / 2;
  const radius = size / 2 - 20;

  // Use actual house longitudes for positioning
  const housePositions = chart.houses.map((h) => {
    const angle = ((h.longitude - 90) * Math.PI) / 180;
    return {
      x: center + radius * Math.cos(angle),
      y: center + radius * Math.sin(angle),
    };
  });

  // Zodiac sign to angle mapping
  const SIGN_ANGLES: Record<string, number> = {
    Aries: 0,
    Taurus: 30,
    Gemini: 60,
    Cancer: 90,
    Leo: 120,
    Virgo: 150,
    Libra: 180,
    Scorpio: 210,
    Sagittarius: 240,
    Capricorn: 270,
    Aquarius: 300,
    Pisces: 330,
  };

  const planetPositions = chart.planets.map((p) => {
    // Use longitude if available, otherwise compute from sign + degree
    const deg = p.degree ?? p.sign_degree ?? 0;
    const signAngle = SIGN_ANGLES[p.sign] ?? 0;
    const totalAngle = p.longitude ?? signAngle + deg;
    const angle = ((totalAngle - 90) * Math.PI) / 180;
    const r = radius * 0.7;
    return {
      x: center + r * Math.cos(angle),
      y: center + r * Math.sin(angle),
      planet: p,
    };
  });

  return (
    <div className="glass p-4">
      <h3 className="font-[family-name:var(--font-cormorant)] text-lg font-semibold mb-3 text-text-primary">
        Колесо карты
      </h3>
      <svg
        width={size}
        height={size}
        viewBox={`0 0 ${size} ${size}`}
        className="mx-auto"
      >
        {/* Outer circle */}
        <circle
          cx={center}
          cy={center}
          r={radius}
          fill="none"
          stroke="var(--text-secondary)"
          strokeWidth={0.5}
          opacity={0.3}
        />
        {/* Inner circle */}
        <circle
          cx={center}
          cy={center}
          r={radius * 0.4}
          fill="none"
          stroke="var(--text-secondary)"
          strokeWidth={0.5}
          opacity={0.2}
        />

        {/* House lines */}
        {housePositions.map((pos, i) => (
          <line
            key={i}
            x1={center}
            y1={center}
            x2={pos.x}
            y2={pos.y}
            stroke="var(--text-secondary)"
            strokeWidth={0.5}
            opacity={0.15}
          />
        ))}

        {/* Planets */}
        {planetPositions.map(({ x, y, planet }) => (
          <g key={planet.name}>
            <circle
              cx={x}
              cy={y}
              r={12}
              fill="var(--text-inverse)"
              stroke="var(--chart-grid)"
              strokeWidth={1}
            />
            <text
              x={x}
              y={y}
              textAnchor="middle"
              dominantBaseline="central"
              className="text-xs"
              fill="var(--chart-series-2)"
            >
              {PLANET_SYMBOLS[planet.name] || "?"}
            </text>
          </g>
        ))}

        {/* Aspect lines */}
        {chart.aspects.map((aspect, i) => {
          const p1 = planetPositions.find(
            (pp) => pp.planet.name === aspect.planet_a,
          );
          const p2 = planetPositions.find(
            (pp) => pp.planet.name === aspect.planet_b,
          );
          if (!p1 || !p2) return null;

          const color =
            aspect.aspect_type === "trine"
              ? "var(--chart-series-3)"
              : aspect.aspect_type === "square"
                ? "var(--chart-series-2)"
                : aspect.aspect_type === "opposition"
                  ? "var(--chart-highlight)"
                  : "var(--chart-grid)";

          return (
            <line
              key={i}
              x1={p1.x}
              y1={p1.y}
              x2={p2.x}
              y2={p2.y}
              stroke={color}
              strokeWidth={0.5}
              strokeDasharray={aspect.aspect_type === "dashed" ? "4,4" : "none"}
              opacity={0.5}
            />
          );
        })}
      </svg>
    </div>
  );
}

// ── Full Chart Component ───────────────────────────────────────────
export function NatalChart({ chart }: { chart: ChartData }) {
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <ChartPlanets planets={chart.planets} />
        <ChartHouses houses={chart.houses} />
      </div>
      <ChartAspects aspects={chart.aspects} />
      <ChartWheel chart={chart} />
    </div>
  );
}
