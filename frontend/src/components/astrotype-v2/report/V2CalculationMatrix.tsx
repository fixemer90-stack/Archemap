import type {
  V2AspectViewModel,
  V2CalculationLayerViewModel,
} from "@/lib/astrotype-v2/report-view-model";
import { formatValue } from "./format";
import { V2GlossaryTerm } from "./V2GlossaryText";

interface V2CalculationMatrixProps {
  matrix: V2CalculationLayerViewModel["calculationMatrix"];
  aspects: V2AspectViewModel[];
}

function entries(value: unknown): Array<[string, unknown]> {
  return value && typeof value === "object" && !Array.isArray(value)
    ? Object.entries(value as Record<string, unknown>)
    : [];
}

export function V2CalculationMatrix({
  matrix,
  aspects,
}: V2CalculationMatrixProps) {
  const houseMode = normalizeGroup(matrix.houseMode, {
    angular: "Угловые",
    succedent: "Последующие",
    cadent: "Падающие",
  });
  const hemiTopBottom = normalizeGroup(matrix.hemispheres, {
    upper: "Верхняя",
    lower: "Нижняя",
  });
  const hemiEastWest = normalizeGroup(matrix.hemispheres, {
    eastern: "Восточная",
    western: "Западная",
  });
  const quadrants = normalizeGroup(matrix.quadrants, {
    q1: "Q1",
    q2: "Q2",
    q3: "Q3",
    q4: "Q4",
  });
  const aspectProfile =
    typeof matrix.aspectProfile === "object" && matrix.aspectProfile
      ? (matrix.aspectProfile as Record<string, unknown>)
      : {};
  const aspectCounts =
    typeof aspectProfile.counts === "object" && aspectProfile.counts
      ? (aspectProfile.counts as Record<string, unknown>)
      : {};
  const exactAspects = [...aspects]
    .sort((a, b) => (a.orbDegrees ?? 999) - (b.orbDegrees ?? 999))
    .slice(0, 3);

  return (
    <section
      data-v2-calculation-block="calculation_matrix"
      className="w-full rounded-[22px] border border-white/10 bg-[linear-gradient(180deg,rgba(255,255,255,0.055),rgba(255,255,255,0.025))] p-5 shadow-[0_20px_70px_rgba(0,0,0,0.3)] md:p-6"
    >
      <h3 className="text-[21px] font-semibold text-[#F4EADB]">
        Расчётные акценты карты
      </h3>
      <p className="mt-2 text-[12px] leading-[1.45] text-[#9FB0CC]">
        Компактная сводка производных расчётов: тип домов, ориентация карты,
        квадранты и профиль аспектной сети.
      </p>
      <div className="mt-4 grid gap-[14px] md:grid-cols-2">
        <div className="rounded-[15px] border border-[#263046] bg-[#101622] p-[14px]">
          <h4 className="font-semibold text-[#FFE2A1]">
            <V2GlossaryTerm term="Тип домов" />
          </h4>
          <div className="mt-3 space-y-[11px]">
            {houseMode.map(([label, value]) => (
              <BarRow key={label} label={label} value={value} compact />
            ))}
          </div>
          <small className="mt-3 block text-[12px] text-[#9FB0CC]">
            оси действия · закрепление · переосмысление
          </small>
        </div>

        <div className="rounded-[15px] border border-[#263046] bg-[#101622] p-[14px]">
          <h4 className="font-semibold text-[#FFE2A1]">
            <V2GlossaryTerm term="Ориентация карты" />
          </h4>
          <div className="mt-3 space-y-[11px]">
            {hemiTopBottom.map(([label, value]) => (
              <BarRow key={label} label={label} value={value} compact />
            ))}
            <div className="my-[13px] h-px bg-[#263046]" />
            {hemiEastWest.map(([label, value]) => (
              <BarRow key={label} label={label} value={value} compact />
            ))}
          </div>
        </div>

        <div className="rounded-[15px] border border-[#263046] bg-[#101622] p-[14px]">
          <h4 className="font-semibold text-[#FFE2A1]">
            <V2GlossaryTerm term="Квадрант" />
          </h4>
          <div className="mt-3 grid grid-cols-2 gap-[10px]">
            {quadrants.map(([label, value]) => (
              <div
                key={label}
                className="min-h-[82px] rounded-[15px] border border-[#263046] bg-[#101622] p-[14px]"
              >
                <b className="text-[#FFE2A1]">{label}</b>
                <span className="float-right font-extrabold text-white">
                  {formatValue(value)}%
                </span>
                <small className="mt-2 block clear-both text-[#9FB0CC]">
                  {quadrantDescription(label)}
                </small>
              </div>
            ))}
          </div>
        </div>

        <div className="rounded-[15px] border border-[#263046] bg-[#101622] p-[14px]">
          <h4 className="font-semibold text-[#FFE2A1]">
            <V2GlossaryTerm term="Профиль аспектов" />
          </h4>
          <div className="mt-3 grid grid-cols-3 gap-[10px]">
            <CountCard
              value={numericValue(aspectCounts.resource)}
              label="ресурс"
            />
            <CountCard
              value={numericValue(aspectCounts.tension)}
              label="напряжение"
            />
            <CountCard
              value={numericValue(aspectCounts.conjunction)}
              label="соединения"
            />
          </div>
          <ul className="mt-4 grid gap-2">
            {exactAspects.map((aspect) => (
              <li
                key={`${aspect.bodyA}-${aspect.bodyB}-${aspect.aspectCode}`}
                className="rounded-[12px] border border-[#263046] bg-[#101622] px-[10px] py-[9px]"
              >
                <b className="block text-[#fff2d6]">
                  {bodyLabel(aspect.bodyA)} — {bodyLabel(aspect.bodyB)}
                </b>
                <span className="block text-[12px] text-[#9FB0CC]">
                  {aspectLabel(aspect.aspectCode)}, orb{" "}
                  {formatValue(aspect.orbDegrees)}°
                </span>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </section>
  );
}

function normalizeGroup(
  value: unknown,
  labels: Record<string, string>,
): Array<[string, number]> {
  const rows = entries(value)
    .filter(([key, item]) => key in labels && typeof item === "number")
    .map(([key, item]) => [labels[key], Number(item)] as [string, number]);
  const total = rows.reduce((sum, [, item]) => sum + item, 0);
  return rows.map(([label, item]) => [
    label,
    total > 0 ? Math.round((item / total) * 100) : 0,
  ]);
}

function BarRow({
  label,
  value,
  compact,
}: {
  label: string;
  value: number;
  compact?: boolean;
}) {
  return (
    <div
      className={
        compact
          ? "grid grid-cols-[116px_minmax(0,1fr)_44px] items-center gap-3"
          : "grid grid-cols-[128px_minmax(0,1fr)_46px] items-center gap-3"
      }
    >
      <div className="text-[15px] text-[#DCE4F3]">{label}</div>
      <div className="h-4 overflow-hidden rounded-[99px] border border-[#2c3548] bg-[#0b1019]">
        <span
          className="block h-full bg-[linear-gradient(90deg,#d9b86f,#f2d991)]"
          style={{ width: `${Math.max(0, Math.min(100, value))}%` }}
        />
      </div>
      <div className="text-right text-[15px] text-[#AEB6C7]">{value}%</div>
    </div>
  );
}

function quadrantDescription(label: string): string {
  return (
    {
      Q1: "личная база",
      Q2: "частная опора",
      Q3: "отношения и горизонт",
      Q4: "публичность и вклад",
    }[label] ?? "—"
  );
}

function CountCard({ value, label }: { value: number; label: string }) {
  return (
    <div className="min-h-[82px] rounded-[15px] border border-[#263046] bg-[#101622] p-[14px]">
      <b className="block text-[30px] leading-none text-[#FFE2A1]">{value}</b>
      <span className="mt-[6px] block text-[12px] text-[#9FB0CC]">{label}</span>
    </div>
  );
}

function numericValue(value: unknown): number {
  return typeof value === "number" && Number.isFinite(value) ? value : 0;
}

function aspectLabel(aspectCode: string): string {
  return (
    {
      conjunction: "соединение",
      opposition: "оппозиция",
      trine: "трин",
      square: "квадрат",
      sextile: "секстиль",
      quincunx: "квинконс",
    }[aspectCode] ?? aspectCode
  );
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
    }[body] ?? body
  );
}
