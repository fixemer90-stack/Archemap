import type { CalculationParametersViewModel } from "@/lib/report/view-model";

interface CalculationParametersProps {
  params: CalculationParametersViewModel;
}

const ITEMS: Array<{
  label: string;
  key: keyof CalculationParametersViewModel;
}> = [
  { label: "Дата и время рождения", key: "birthDateTime" },
  { label: "Место", key: "birthPlace" },
  { label: "Часовой пояс", key: "timezone" },
  { label: "UTC-время расчёта", key: "utcCalculationTime" },
  { label: "Система домов", key: "houseSystem" },
  { label: "Зодиак", key: "zodiac" },
];

export function CalculationParameters({ params }: CalculationParametersProps) {
  return (
    <section className="rounded-lg border border-[#D8B45A]/25 bg-[#D8B45A]/5 p-4 text-sm">
      <h3 className="mb-3 font-semibold text-[#D8B45A]">Расчётные параметры</h3>
      <dl className="grid gap-2 sm:grid-cols-2">
        {ITEMS.map((item) => (
          <div key={item.key} className="rounded-md bg-background/30 p-3">
            <dt className="text-xs text-muted-foreground">{item.label}</dt>
            <dd className="mt-1 font-medium">{params[item.key]}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}
