import { CalculationParameters } from "@/components/report/calculation-parameters";
import { CareerCTA } from "@/components/report/career-cta";
import { HouseScenariosSection } from "@/components/report/house-scenarios-section";
import {
  NarrativeHero,
  NarrativeSection,
  renderNarrativeParagraphs,
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

function FinalSummary({ paragraphs }: { paragraphs: string[] }) {
  if (paragraphs.length === 0) {
    return null;
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Финальное резюме</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4 text-sm leading-6 text-muted-foreground">
        {renderNarrativeParagraphs(paragraphs)}
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

function StagedPipelineSummary({
  totalStages,
  completedStages,
  completedStageLabels,
}: {
  totalStages: number;
  completedStages: number;
  completedStageLabels: string[];
}) {
  if (totalStages <= 0 || completedStages <= 0) {
    return null;
  }

  return (
    <Card className="border-primary/20 bg-primary/5">
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-base">
          Этот текст собран поэтапно
          <span className="rounded-full bg-muted px-2 py-0.5 text-xs font-medium text-muted-foreground">
            {completedStages}/{totalStages}
          </span>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3 text-sm text-muted-foreground">
        <p>
          Сначала система собирает план и смысловые блоки, затем проходит
          финальную сборку без показа технических промежуточных артефактов.
        </p>
        {completedStageLabels.length > 0 && (
          <div className="flex flex-wrap gap-2">
            {completedStageLabels.map((label) => (
              <span
                key={label}
                className="rounded-full border border-border bg-background px-2 py-1 text-xs text-foreground"
              >
                {label}
              </span>
            ))}
          </div>
        )}
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
      {narrative.stage_summary?.ready && (
        <StagedPipelineSummary
          completedStageLabels={narrative.stage_summary.completed_stage_labels}
          completedStages={narrative.stage_summary.completed_stages}
          totalStages={narrative.stage_summary.total_stages}
        />
      )}
      <HouseScenariosSection scenarios={narrative.house_scenarios} />
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
      <FinalSummary paragraphs={narrative.final_summary_paragraphs} />
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
