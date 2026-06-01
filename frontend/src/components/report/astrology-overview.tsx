import { TermHelp } from "@/components/glossary/term-help";
import { SectionCard } from "@/components/report/section-card";
import type { ReportViewModel } from "@/lib/report/view-model";

export function AstrologyOverview({
  astrology,
}: {
  astrology: ReportViewModel["astrology"];
}) {
  return (
    <SectionCard
      title="Астрологическая основа"
      description="Сначала разбираем карту: из каких факторов появляются выводы. Архетипы и соционика идут позже."
    >
      <div className="mb-5 leading-7 text-muted-foreground">
        <TermHelp term="Натальная карта" /> — это база расчёта. Ниже не весь
        технический список, а только главные факторы, которые помогают понять
        логику отчёта.
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <div className="rounded-lg border p-4">
          <div className="text-sm text-muted-foreground">
            <TermHelp term="Солнце" />
          </div>
          <div className="mt-2 font-medium">{astrology.sun}</div>
          <p className="mt-2 text-sm leading-6 text-muted-foreground">
            {astrology.sun_meaning}
          </p>
        </div>
        <div className="rounded-lg border p-4">
          <div className="text-sm text-muted-foreground">
            <TermHelp term="Луна" />
          </div>
          <div className="mt-2 font-medium">{astrology.moon}</div>
          <p className="mt-2 text-sm leading-6 text-muted-foreground">
            {astrology.moon_meaning}
          </p>
        </div>
        <div className="rounded-lg border p-4">
          <div className="text-sm text-muted-foreground">
            <TermHelp term="Асцендент" />
          </div>
          <div className="mt-2 font-medium">{astrology.ascendant}</div>
          <p className="mt-2 text-sm leading-6 text-muted-foreground">
            {astrology.ascendant_meaning}
          </p>
        </div>
      </div>

      <div className="mt-4 grid gap-4 md:grid-cols-2">
        <div className="rounded-lg bg-muted p-4 leading-7">
          <div className="font-medium">
            <TermHelp term="Стихия" />
          </div>
          <p className="mt-2 text-sm text-muted-foreground">
            {astrology.dominant_elements}
          </p>
        </div>
        <div className="rounded-lg bg-muted p-4 leading-7">
          <div className="font-medium">
            <TermHelp term="Модальность" />
          </div>
          <p className="mt-2 text-sm text-muted-foreground">
            {astrology.modalities}
          </p>
        </div>
      </div>

      <div className="mt-5 rounded-lg border p-4">
        <div className="font-medium">Ключевые связи карты</div>
        <div className="mt-2 text-sm leading-6 text-muted-foreground">
          <TermHelp term="Аспект" /> показывает связь между факторами, а{" "}
          <TermHelp term="Орб" /> — насколько эта связь точная. Полный список
          находится в technical details.
        </div>
        <ul className="mt-3 grid gap-2">
          {astrology.key_aspects.map((aspect) => (
            <li
              key={aspect}
              className="rounded-md bg-muted p-3 text-sm leading-6"
            >
              {aspect}
            </li>
          ))}
        </ul>
      </div>

      <div className="mt-4 rounded-lg border border-amber-500/30 bg-amber-500/10 p-4 text-sm leading-6">
        {astrology.time_sensitive_note} <TermHelp term="Дом" /> тоже зависит от
        времени рождения, поэтому дома раскрыты в техническом блоке.
      </div>
    </SectionCard>
  );
}
