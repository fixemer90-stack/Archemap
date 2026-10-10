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
      className="w-full rounded-[22px] border border-border-default bg-[var(--hero-background)] p-5 shadow-elevated md:p-6"
    >
      <h3 className="text-[21px] font-semibold text-text-primary">
        Расчётные акценты карты
      </h3>
      <p className="mt-2 text-[12px] leading-[1.45] text-text-muted">
        Компактная сводка производных расчётов: тип домов, ориентация карты,
        квадранты и профиль аспектной сети.
      </p>
      <div className="mt-4 grid gap-[14px] md:grid-cols-2">
        <div className="rounded-[15px] border border-border-default bg-surface-subtle p-[14px]">
          <h4 className="font-semibold text-warning">
            <V2GlossaryTerm term="Тип домов" />
          </h4>
          <p className="mt-2 text-[12px] leading-[1.45] text-text-muted">
            Типы домов показывают, как тема включается в жизни: быстро
            проявляется, удерживается или постепенно перерабатывается.
          </p>
          <div className="mt-3 space-y-[11px]">
            {houseMode.map(([label, value]) => (
              <HouseModeRow key={label} label={label} value={value} />
            ))}
          </div>
        </div>

        <div className="rounded-[15px] border border-border-default bg-surface-subtle p-[14px]">
          <h4 className="font-semibold text-warning">
            <V2GlossaryTerm term="Квадрант" />
          </h4>
          <div className="mt-3 grid grid-cols-2 gap-[10px]">
            {quadrants.map(([label, value]) => (
              <div
                key={label}
                className="min-h-[82px] rounded-[15px] border border-border-default bg-surface-subtle p-[14px]"
              >
                <b className="text-warning">{label}</b>
                <span className="float-right font-extrabold text-text-secondary">
                  {formatValue(value)}%
                </span>
                <small className="mt-2 block clear-both text-text-muted">
                  {quadrantDescription(label)}
                </small>
              </div>
            ))}
          </div>
        </div>

        <div className="rounded-[15px] border border-border-default bg-surface-subtle p-[14px]">
          <h4 className="font-semibold text-warning">
            <V2GlossaryTerm term="Ориентация карты" />
          </h4>
          <p className="mt-2 text-[12px] leading-[1.45] text-text-muted">
            Это не оценка характера, а распределение планет по половинам карты:
            где сильнее проявляются темы жизни.
          </p>
          <div className="mt-3 space-y-[11px]">
            {hemiTopBottom.map(([label, value]) => (
              <OrientationRow key={label} label={label} value={value} />
            ))}
            <div className="my-[13px] h-px bg-surface-subtle" />
            {hemiEastWest.map(([label, value]) => (
              <OrientationRow key={label} label={label} value={value} />
            ))}
          </div>
        </div>

        <div className="rounded-[15px] border border-border-default bg-surface-subtle p-[14px]">
          <h4 className="font-semibold text-warning">
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
                className="rounded-[12px] border border-border-default bg-surface-subtle px-[10px] py-[9px]"
              >
                <b className="block text-text-primary">
                  {bodyLabel(aspect.bodyA)} — {bodyLabel(aspect.bodyB)}
                </b>
                <span className="block text-[12px] text-text-muted">
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
      <div className="text-[15px] text-text-secondary">{label}</div>
      <div className="h-4 overflow-hidden rounded-[99px] border border-border-default bg-surface-subtle">
        <span
          className="block h-full bg-[var(--hero-background)]"
          style={{ width: `${Math.max(0, Math.min(100, value))}%` }}
        />
      </div>
      <div className="text-right text-[15px] text-text-secondary">{value}%</div>
    </div>
  );
}

function HouseModeRow({ label, value }: { label: string; value: number }) {
  return (
    <div className="space-y-1.5">
      <BarRow label={label} value={value} compact />
      <p className="pl-0 text-[12px] leading-[1.45] text-text-muted md:pl-[116px]">
        {houseModeDescription(label)}
      </p>
    </div>
  );
}

function houseModeDescription(label: string): string {
  return (
    {
      Угловые:
        "То, что сразу заметно и запускает события: инициативы, повороты, точки действия.",
      Последующие:
        "То, что закрепляет результат: устойчивость, ресурс, привычки, накопление опыта.",
      Падающие:
        "То, что осмысляет и перестраивает опыт: адаптация, обучение, переходы, внутренняя переработка.",
    }[label] ?? "Показывает, через какой тип домов чаще проявляются темы карты."
  );
}

function OrientationRow({ label, value }: { label: string; value: number }) {
  return (
    <div className="space-y-1.5">
      <BarRow label={label} value={value} compact />
      <p className="pl-0 text-[12px] leading-[1.45] text-text-muted md:pl-[116px]">
        {orientationDescription(label)}
      </p>
    </div>
  );
}

function orientationDescription(label: string): string {
  return (
    {
      Верхняя:
        "Акцент на внешней реализации: события, роль, видимость, взаимодействие с миром.",
      Нижняя:
        "Акцент на внутренней опоре: личная территория, семья, приватность, накопление ресурса.",
      Восточная:
        "Больше инициативы от себя: человек чаще сам запускает процессы и выбирает направление.",
      Западная:
        "Больше отклика на других: важны партнёры, среда, обратная связь и совместные решения.",
    }[label] ?? "Показывает, в какой зоне карты сосредоточено больше планет."
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
    <div className="min-h-[82px] rounded-[15px] border border-border-default bg-surface-subtle p-[14px]">
      <b className="block text-[30px] leading-none text-warning">{value}</b>
      <span className="mt-[6px] block text-[12px] text-text-muted">
        {label}
      </span>
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
