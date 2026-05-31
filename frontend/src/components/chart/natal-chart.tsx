"use client";

// ── Types ──────────────────────────────────────────────────────────
interface Planet {
  name: string;
  sign: string;
  degree: number;
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

// ── Planet symbols ─────────────────────────────────────────────────
const PLANET_SYMBOLS: Record<string, string> = {
  Sun: "☉",
  Moon: "☽",
  Mercury: "☿",
  Venus: "♀",
  Mars: "♂",
  Jupiter: "♃",
  Saturn: "♄",
  Uranus: "♅",
  Neptune: "♆",
  Pluto: "♇",
  "North Node": "☊",
  Lilith: "⚸",
  Chiron: "⚷",
};

// ── Sign symbols ───────────────────────────────────────────────────
const SIGN_SYMBOLS: Record<string, string> = {
  Aries: "♈",
  Taurus: "♉",
  Gemini: "♊",
  Cancer: "♋",
  Leo: "♌",
  Virgo: "♍",
  Libra: "♎",
  Scorpio: "♏",
  Sagittarius: "♐",
  Capricorn: "♑",
  Aquarius: "♒",
  Pisces: "♓",
};

// ── Aspect colors ──────────────────────────────────────────────────
const ASPECT_COLORS: Record<string, string> = {
  conjunction: "text-red-500",
  opposition: "text-red-400",
  trine: "text-green-500",
  sextile: "text-blue-500",
  square: "text-orange-500",
  quincunx: "text-gray-400",
};

// ── Chart Planets Component ────────────────────────────────────────
export function ChartPlanets({ planets }: { planets: Planet[] }) {
  return (
    <div className="rounded-lg border p-4">
      <h3 className="font-medium mb-3">Планеты</h3>
      <div className="space-y-2">
        {planets.map((planet) => (
          <div
            key={planet.name}
            className="flex items-center justify-between text-sm"
          >
            <div className="flex items-center gap-2">
              <span className="text-lg">
                {PLANET_SYMBOLS[planet.name] || "?"}
              </span>
              <span className="font-medium">{planet.name}</span>
              {planet.is_retrograde && (
                <span className="text-xs text-muted-foreground">℞</span>
              )}
            </div>
            <div className="flex items-center gap-2">
              <span>{SIGN_SYMBOLS[planet.sign] || "?"}</span>
              <span className="text-muted-foreground">{planet.sign}</span>
              <span className="font-mono text-xs">
                {planet.degree.toFixed(2)}°
              </span>
              {planet.house && (
                <span className="text-xs text-muted-foreground">
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
    <div className="rounded-lg border p-4">
      <h3 className="font-medium mb-3">Дома</h3>
      <div className="grid grid-cols-2 gap-2">
        {houses.map((house) => (
          <div
            key={house.number}
            className="flex items-center justify-between text-sm"
          >
            <span className="text-muted-foreground">Дом {house.number}</span>
            <div className="flex items-center gap-1">
              <span>{SIGN_SYMBOLS[house.sign] || "?"}</span>
              <span className="font-mono text-xs">
                {house.longitude.toFixed(2)}°
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
    <div className="rounded-lg border p-4">
      <h3 className="font-medium mb-3">Аспекты</h3>
      <div className="space-y-1">
        {aspects.map((aspect, i) => (
          <div key={i} className="flex items-center justify-between text-sm">
            <div className="flex items-center gap-2">
              <span className="font-medium">{aspect.planet_a}</span>
              <span
                className={ASPECT_COLORS[aspect.aspect_type] || "text-gray-500"}
              >
                {aspect.aspect_type}
              </span>
              <span className="font-medium">{aspect.planet_b}</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="font-mono text-xs text-muted-foreground">
                orb: {aspect.orb.toFixed(2)}°
              </span>
              <span className="text-xs text-muted-foreground">
                {aspect.is_applying ? "App" : "Sep"}
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

  // Calculate house cusps positions (simplified - equal houses)
  const housePositions = chart.houses.map((h, i) => {
    const angle = (i * 30 - 90) * (Math.PI / 180);
    return {
      x: center + radius * Math.cos(angle),
      y: center + radius * Math.sin(angle),
    };
  });

  // Calculate planet positions
  const planetPositions = chart.planets.map((p) => {
    // Simplified: use house number to position
    const houseIndex = (p.house || 1) - 1;
    const baseAngle = houseIndex * 30;
    const offset = p.degree * (30 / 30); // Simplified
    const angle = ((baseAngle + offset - 90) * Math.PI) / 180;
    const r = radius * 0.7; // Inner circle
    return {
      x: center + r * Math.cos(angle),
      y: center + r * Math.sin(angle),
      planet: p,
    };
  });

  return (
    <div className="rounded-lg border p-4">
      <h3 className="font-medium mb-3">Колесо карты</h3>
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
          stroke="currentColor"
          strokeWidth={1}
          className="text-border"
        />

        {/* Inner circle */}
        <circle
          cx={center}
          cy={center}
          r={radius * 0.4}
          fill="none"
          stroke="currentColor"
          strokeWidth={1}
          className="text-border"
        />

        {/* House lines */}
        {housePositions.map((pos, i) => (
          <line
            key={i}
            x1={center}
            y1={center}
            x2={pos.x}
            y2={pos.y}
            stroke="currentColor"
            strokeWidth={0.5}
            className="text-border"
          />
        ))}

        {/* Planets */}
        {planetPositions.map(({ x, y, planet }) => (
          <g key={planet.name}>
            <circle
              cx={x}
              cy={y}
              r={12}
              fill="hsl(var(--background))"
              stroke="hsl(var(--border))"
              strokeWidth={1}
            />
            <text
              x={x}
              y={y}
              textAnchor="middle"
              dominantBaseline="central"
              className="text-xs fill-current"
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

          const colorClass =
            aspect.aspect_type === "trine"
              ? "text-green-500"
              : aspect.aspect_type === "square"
                ? "text-orange-500"
                : aspect.aspect_type === "opposition"
                  ? "text-red-400"
                  : "text-gray-300";

          return (
            <line
              key={i}
              x1={p1.x}
              y1={p1.y}
              x2={p2.x}
              y2={p2.y}
              stroke="currentColor"
              strokeWidth={0.5}
              strokeDasharray={aspect.aspect_type === "dashed" ? "4,4" : "none"}
              className={colorClass}
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
