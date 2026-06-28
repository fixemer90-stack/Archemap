import { CalculationParameters } from "@/components/report/calculation-parameters";
import { CalibrationQuestionsSection } from "@/components/report/calibration-questions-section";
import { CareerCTA } from "@/components/report/career-cta";
import { HouseScenariosSection } from "@/components/report/house-scenarios-section";
import {
  NarrativeHero,
  NarrativeSection,
} from "@/components/report/narrative-section";
import { PatternTensionsSection } from "@/components/report/pattern-tensions-section";
import { ReportPdfActions } from "@/components/report/report-pdf-actions";
import { TechnicalDetailsAccordion } from "@/components/report/technical-details-accordion";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { TermHelp } from "@/components/glossary/term-help";
import {
  allowedSelfSectionIds,
  type ReportViewModel,
  type SelfNarrativeSectionId,
} from "@/lib/report/view-model";

interface ReportNarrativePageProps {
  data: ReportViewModel;
  isDownloadingPdf: boolean;
  onDownloadPdf: () => void | Promise<void>;
  profileId: string;
}

const NARRATIVE_RENDER_ORDER = [
  "<NarrativeHero",
  "<HouseScenariosSection",
  "<CalibrationQuestionsSection",
  "<PatternTensionsSection",
  "main_formula",
  "world_perception",
  "emotions_and_communication",
  "strengths",
  "vulnerabilities",
  "relationships",
  "sexuality",
  "development",
  "<CareerCTA",
  "<FinalSummary",
  "<ReportPdfActions",
  "<CalculationParameters",
  "<TechnicalDetailsAccordion",
] as const;

const SELF_SECTION_ORDER: SelfNarrativeSectionId[] =
  NARRATIVE_RENDER_ORDER.filter((marker): marker is SelfNarrativeSectionId =>
    allowedSelfSectionIds.includes(marker as SelfNarrativeSectionId),
  );

function FinalSummary({ text }: { text: string }) {
  if (!text) {
    return null;
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Финальное резюме</CardTitle>
      </CardHeader>
      <CardContent className="text-sm leading-6 text-muted-foreground">
        {text}
      </CardContent>
    </Card>
  );
}

function GlossaryHelpStrip() {
  return (
    <Card className="bg-muted/20">
      <CardContent className="flex flex-wrap gap-3 p-4 text-sm text-muted-foreground">
        <span>Помощь по терминам:</span>
        <TermHelp term="Натальная карта" />
        <TermHelp term="Архетип" />
        <TermHelp term="Соционический тип" />
        <TermHelp term="Цепочка доказательств" />
      </CardContent>
    </Card>
  );
}

export function ReportNarrativePage({
  data,
  isDownloadingPdf,
  onDownloadPdf,
  profileId,
}: ReportNarrativePageProps) {
  const narrative = data.narrative;
  if (!narrative) {
    return <TechnicalDetailsAccordion data={data} />;
  }

  const sectionsById = new Map(
    narrative.sections.map((section) => [section.id, section]),
  );
  const orderedSections = SELF_SECTION_ORDER.flatMap((sectionId) => {
    const section = sectionsById.get(sectionId);
    return section ? [section] : [];
  });

  return (
    <div className="mx-auto grid max-w-5xl grid-cols-1 gap-6">
      <NarrativeHero hero={narrative.hero} />
      <GlossaryHelpStrip />
      <HouseScenariosSection scenarios={narrative.house_scenarios} />
      <CalibrationQuestionsSection
        questions={narrative.calibration_questions}
      />
      <PatternTensionsSection
        contradictions={narrative.contradictions}
        failureModes={narrative.failure_modes}
        maturityLevels={narrative.maturity_levels}
      />
      {orderedSections.map((section) => (
        <NarrativeSection key={section.id} section={section} />
      ))}
      {narrative.career_cta && (
        <CareerCTA cta={narrative.career_cta} profileId={profileId} />
      )}
      <FinalSummary text={narrative.final_summary} />
      <ReportPdfActions
        isDownloading={isDownloadingPdf}
        onDownload={onDownloadPdf}
      />
      <CalculationParameters params={data.calculation_params} />
      <TechnicalDetailsAccordion data={data} />
      <span className="sr-only">{allowedSelfSectionIds.join(",")}</span>
    </div>
  );
}
