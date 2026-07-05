import { EvidenceNotes } from "@/components/report/evidence-notes";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import type {
  NarrativeHeroViewModel,
  NarrativeSectionViewModel,
} from "@/lib/report/view-model";

const SECTION_KICKERS: Record<NarrativeSectionViewModel["id"], string> = {
  main_formula: "Главная формула",
  world_perception: "Восприятие мира",
  emotions_and_communication: "Эмоции и коммуникация",
  strengths: "Сильные стороны",
  vulnerabilities: "Уязвимости",
  relationships: "Отношения",
  sexuality: "Сексуальность",
  development: "Развитие",
};

interface NarrativeHeroProps {
  hero: NarrativeHeroViewModel;
}

export function renderNarrativeParagraphs(paragraphs: string[]) {
  return paragraphs.map((paragraph) => (
    <p key={paragraph} className="whitespace-pre-line">
      {paragraph}
    </p>
  ));
}

export function NarrativeHero({ hero }: NarrativeHeroProps) {
  return (
    <Card className="border-[#C28A2E]/30 bg-[#C28A2E]/5">
      <CardHeader>
        <CardDescription>Мягкое начало отчёта</CardDescription>
        <CardTitle className="text-3xl leading-tight">{hero.title}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4 text-base leading-7">
        <div className="space-y-4">
          {renderNarrativeParagraphs(hero.body_paragraphs)}
        </div>
        {hero.bullets.length > 0 && (
          <ul className="grid grid-cols-1 gap-2 text-sm text-muted-foreground">
            {hero.bullets.map((bullet) => (
              <li key={bullet} className="rounded-lg bg-background/70 p-3">
                {bullet}
              </li>
            ))}
          </ul>
        )}
        <EvidenceNotes notes={hero.evidence_notes} />
      </CardContent>
    </Card>
  );
}

interface NarrativeSectionProps {
  section: NarrativeSectionViewModel;
}

export function NarrativeSection({ section }: NarrativeSectionProps) {
  return (
    <Card>
      <CardHeader>
        <CardDescription>{SECTION_KICKERS[section.id]}</CardDescription>
        <CardTitle>{section.title}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4 text-sm leading-6 text-muted-foreground">
        <div className="space-y-4">
          {renderNarrativeParagraphs(section.body_paragraphs)}
        </div>
        {section.bullets.length > 0 && (
          <ul className="grid grid-cols-1 gap-2 sm:grid-cols-2">
            {section.bullets.map((bullet) => (
              <li key={bullet} className="rounded-lg border bg-background p-3">
                {bullet}
              </li>
            ))}
          </ul>
        )}
        <EvidenceNotes notes={section.evidence_notes} />
      </CardContent>
    </Card>
  );
}
