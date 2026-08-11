import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { V2CalculationLayerViewModel } from "@/lib/report/view-model";

interface V2CalculationLayerProps {
  layer?: V2CalculationLayerViewModel;
}

function valueText(value: unknown): string {
  if (typeof value === "number") {
    return Number.isInteger(value) ? String(value) : value.toFixed(2);
  }
  if (typeof value === "string") {
    return value;
  }
  if (typeof value === "boolean") {
    return value ? "да" : "нет";
  }
  return "—";
}

function hasItems(items: Array<Record<string, unknown>> | undefined): boolean {
  return Boolean(items && items.length > 0);
}

export function V2CalculationLayer({ layer }: V2CalculationLayerProps) {
  if (!layer) {
    return null;
  }

  const indicators = layer.key_indicators;
  const sun = indicators.sun as Record<string, unknown> | undefined;
  const moon = indicators.moon as Record<string, unknown> | undefined;
  const ascendant = indicators.ascendant as Record<string, unknown> | undefined;

  return (
    <section className="space-y-4" aria-labelledby="v2-calculation-layer-title">
      <div>
        <h2 id="v2-calculation-layer-title" className="text-2xl font-semibold">
          Расчётная карта и факты
        </h2>
        <p className="text-sm text-muted-foreground">
          Нижний слой отчёта: ключевые показатели, таблицы положений, балансы,
          акценты домов, аспекты и компактная проверка источников.
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        {[
          ["Солнце", sun],
          ["Луна", moon],
          ["Асцендент", ascendant],
        ].map(([label, item]) => (
          <Card key={label as string}>
            <CardHeader className="pb-2">
              <CardTitle className="text-base">{label as string}</CardTitle>
            </CardHeader>
            <CardContent className="text-sm text-muted-foreground">
              {item ? (
                <>
                  <div>
                    {valueText((item as Record<string, unknown>).degree_label)}
                  </div>
                  <div>
                    Дом:{" "}
                    {valueText((item as Record<string, unknown>).house_number)}
                  </div>
                </>
              ) : (
                "нет данных"
              )}
            </CardContent>
          </Card>
        ))}
      </div>

      {hasItems(layer.planet_positions) && (
        <Card>
          <CardHeader>
            <CardTitle>Положения планет</CardTitle>
          </CardHeader>
          <CardContent className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="text-muted-foreground">
                <tr>
                  <th className="py-2">Тело</th>
                  <th className="py-2">Положение</th>
                  <th className="py-2">Дом</th>
                  <th className="py-2">R</th>
                </tr>
              </thead>
              <tbody>
                {layer.planet_positions.map((position) => (
                  <tr key={String(position.body)} className="border-t">
                    <td className="py-2">{valueText(position.body)}</td>
                    <td className="py-2">{valueText(position.degree_label)}</td>
                    <td className="py-2">{valueText(position.house_number)}</td>
                    <td className="py-2">{position.retrograde ? "R" : "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </CardContent>
        </Card>
      )}

      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Балансы</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            {layer.balance_bars.map((balance) => (
              <div
                key={`${valueText(balance.category)}:${valueText(balance.key)}`}
              >
                <div className="flex justify-between text-muted-foreground">
                  <span>
                    {valueText(balance.category)} / {valueText(balance.key)}
                  </span>
                  <span>{valueText(balance.value)}</span>
                </div>
                <div className="h-2 rounded bg-muted">
                  <div
                    className="h-2 rounded bg-primary"
                    style={{
                      width: `${Math.max(0, Math.min(100, Number(balance.value ?? 0) * 100))}%`,
                    }}
                  />
                </div>
              </div>
            ))}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Акценты домов</CardTitle>
          </CardHeader>
          <CardContent className="grid grid-cols-2 gap-2 text-sm">
            {layer.house_accents.map((house) => (
              <div
                key={String(house.house_number)}
                className="rounded border p-2"
              >
                Дом {valueText(house.house_number)} · {valueText(house.sign)}
                <div className="text-muted-foreground">
                  тел: {valueText(house.body_count)}
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>

      {hasItems(layer.aspect_table) && (
        <Card>
          <CardHeader>
            <CardTitle>Аспекты</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
            <div className="flex flex-wrap gap-2" aria-label="aspect network">
              {layer.aspect_network.map((edge) => (
                <span
                  key={`${valueText(edge.source)}-${valueText(edge.target)}-${valueText(edge.aspect_code)}`}
                  className="rounded-full border px-3 py-1"
                >
                  {valueText(edge.source)} → {valueText(edge.target)} ·{" "}
                  {valueText(edge.aspect_code)}
                </span>
              ))}
            </div>
            <table className="w-full text-left">
              <thead className="text-muted-foreground">
                <tr>
                  <th className="py-2">Пара</th>
                  <th className="py-2">Аспект</th>
                  <th className="py-2">Орб</th>
                </tr>
              </thead>
              <tbody>
                {layer.aspect_table.map((aspect) => (
                  <tr
                    key={`${valueText(aspect.body_a)}-${valueText(aspect.body_b)}-${valueText(aspect.aspect_code)}`}
                    className="border-t"
                  >
                    <td className="py-2">
                      {valueText(aspect.body_a)} / {valueText(aspect.body_b)}
                    </td>
                    <td className="py-2">{valueText(aspect.aspect_code)}</td>
                    <td className="py-2">{valueText(aspect.orb_degrees)}°</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </CardContent>
        </Card>
      )}

      <details className="rounded-lg border p-4">
        <summary className="cursor-pointer font-medium">
          Матрица расчёта и источники
        </summary>
        <div className="mt-4 grid gap-4 text-sm md:grid-cols-2">
          <pre className="overflow-x-auto rounded bg-muted p-3">
            {JSON.stringify(layer.calculation_matrix, null, 2)}
          </pre>
          <div className="space-y-2">
            {layer.evidence_cards.map((card) => (
              <div key={String(card.fact_key)} className="rounded border p-3">
                <div className="font-medium">{valueText(card.title)}</div>
                <div className="text-muted-foreground">
                  {valueText(card.summary)}
                </div>
              </div>
            ))}
          </div>
        </div>
      </details>
    </section>
  );
}
