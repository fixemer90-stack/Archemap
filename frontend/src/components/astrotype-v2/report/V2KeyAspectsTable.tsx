import type { V2AspectViewModel } from "@/lib/astrotype-v2/report-view-model";
import {
  aspectTone,
  formatValue,
  localizeAspectLabel,
  localizeAstroLabel,
} from "./format";
import { V2GlossaryTerm } from "./V2GlossaryText";

interface V2KeyAspectsTableProps {
  selectedAspects: V2AspectViewModel[];
  remainingAspects: V2AspectViewModel[];
}

export function V2KeyAspectsTable({
  selectedAspects,
  remainingAspects,
}: V2KeyAspectsTableProps) {
  return (
    <section data-v2-calculation-block="key_aspects" className="space-y-4">
      <h3 className="text-[21px] font-semibold text-text-primary">
        Ключевые аспекты
      </h3>
      <div className="overflow-x-auto rounded-[22px] border border-border-default [background:var(--hero-background)] shadow-elevated">
        <table className="w-full min-w-[640px] text-left text-sm">
          <AspectTableHead />
          <tbody className="divide-y divide-[var(--border-default)] text-text-secondary">
            <AspectRows aspects={selectedAspects} />
          </tbody>
        </table>
      </div>
      {remainingAspects.length > 0 && (
        <details className="rounded-[18px] border border-border-default bg-surface-subtle p-4">
          <summary className="cursor-pointer font-semibold text-text-primary focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-[var(--focus-ring)]">
            Показать все аспекты ({remainingAspects.length})
          </summary>
          <div className="mt-4 overflow-x-auto">
            <table className="w-full min-w-[640px] text-left text-sm">
              <AspectTableHead />
              <tbody className="divide-y divide-[var(--border-default)] text-text-secondary">
                <AspectRows aspects={remainingAspects} />
              </tbody>
            </table>
          </div>
        </details>
      )}
    </section>
  );
}

function AspectTableHead() {
  return (
    <thead className="text-text-secondary">
      <tr>
        <th className="px-4 py-3">Связка</th>
        <th className="px-4 py-3">
          <V2GlossaryTerm term="Аспект" />
        </th>
        <th className="px-4 py-3">
          <V2GlossaryTerm term="Орб" />
        </th>
        <th className="px-4 py-3">Тип</th>
      </tr>
    </thead>
  );
}

function AspectRows({ aspects }: { aspects: V2AspectViewModel[] }) {
  return aspects.map((aspect) => {
    const tone = aspectTone(aspect.aspectCode);
    const key = `${aspect.bodyA}|${aspect.bodyB}|${aspect.aspectCode}`;
    return (
      <tr key={key} data-aspect-row={key}>
        <td className="px-4 py-3 text-text-primary">
          {localizeAstroLabel(aspect.bodyA)} —{" "}
          {localizeAstroLabel(aspect.bodyB)}
        </td>
        <td className="px-4 py-3">{localizeAspectLabel(aspect.aspectCode)}</td>
        <td className="px-4 py-3">{formatValue(aspect.orbDegrees)}°</td>
        <td className="px-4 py-3">
          <span
            className={
              tone === "resource"
                ? "rounded-full bg-surface-subtle px-3 py-1 text-xs text-info"
                : "rounded-full bg-surface-subtle px-3 py-1 text-xs text-text-secondary"
            }
          >
            {tone === "resource" ? "ресурс" : "напряжение"}
          </span>
        </td>
      </tr>
    );
  });
}
