import type { AstrotypeV2FullReportResponse } from "@/lib/api/astrotype-v2";

export const CANONICAL_V2_SECTION_ORDER = [
  "core_pattern",
  "perception_and_mind",
  "emotional_regulation",
  "agency_and_desire",
  "relationships_and_intimacy",
  "growth_vector",
] as const;

export type V2ReportLayoutBlock = "hero" | "narrative" | "calculation_layer";

export interface V2ReportHeroViewModel {
  eyebrow: string;
  title: string;
  greeting: string;
  intro: string;
  birthDataItems: Array<{ label: string; value: string }>;
  statusLabel: string;
  calculationLabel: string;
  pdfLabel: string;
}

export interface V2NarrativeSectionViewModel {
  id: string;
  title: string;
  eyebrow: string;
  subtitle: string;
  bodyText: string;
  paragraphs: string[];
  paragraphCount: number;
  asideTitle: string;
  asideBullets: string[];
  evidenceIds: string[];
  coveredThemeIds: string[];
}

export interface V2ChartIndicatorViewModel {
  body?: string;
  planet?: string;
  sign?: string;
  degreeLabel?: string;
  houseNumber?: number | null;
  position?: V2ChartIndicatorViewModel;
}

export interface V2PlanetPositionViewModel {
  body: string;
  sign: string;
  houseNumber: number | null;
  signDegree: number | null;
  degreeLabel: string;
  retrograde: boolean;
  sampledAspects: V2AspectViewModel[];
}

export interface V2BalanceBarViewModel {
  category: string;
  key: string;
  label: string;
  value: number;
  rank: number | null;
}

export interface V2HouseEmphasisBarViewModel {
  houseNumber: number;
  sign: string;
  bodyCount: number;
  accentWeight: number;
}

export interface V2AspectNodeViewModel {
  id: string;
  label: string;
  sign?: string;
  houseNumber?: number | null;
}

export interface V2AspectEdgeViewModel {
  source: string;
  target: string;
  aspectCode: string;
  strength: number | null;
  orbDegrees?: number | null;
  applying?: boolean | null;
}

export interface V2AspectViewModel {
  bodyA: string;
  bodyB: string;
  aspectCode: string;
  orbDegrees: number | null;
  angleDegrees?: number | null;
  applying?: boolean | null;
  strength?: number | null;
}

export interface V2CalculationLayerViewModel {
  readerBlocks: string[];
  keyIndicators: {
    ascendant?: V2ChartIndicatorViewModel;
    mc?: V2ChartIndicatorViewModel;
    ascendantRuler?: V2ChartIndicatorViewModel;
    sun?: V2ChartIndicatorViewModel;
    moon?: V2ChartIndicatorViewModel;
  };
  planetPositions: V2PlanetPositionViewModel[];
  balanceBars: Record<string, V2BalanceBarViewModel[]>;
  houseEmphasis: {
    bars: V2HouseEmphasisBarViewModel[];
    topHouses: V2HouseEmphasisBarViewModel[];
  };
  aspectNetwork: {
    nodes: V2AspectNodeViewModel[];
    edges: V2AspectEdgeViewModel[];
  };
  keyAspects: V2AspectViewModel[];
  calculationMatrix: Record<string, unknown>;
}

export interface V2ReportReaderViewModel {
  reportId: string;
  status: string;
  version: number;
  layoutOrder: V2ReportLayoutBlock[];
  hero: V2ReportHeroViewModel;
  sections: V2NarrativeSectionViewModel[];
  calculationLayer: V2CalculationLayerViewModel;
  progress: AstrotypeV2FullReportResponse["progress"];
}

export function buildV2ReportReaderViewModel(
  payload: AstrotypeV2FullReportResponse,
): V2ReportReaderViewModel {
  const report = payload.report;
  const assembled = asRecord(report.assembled_payload);
  const readerView = asRecord(assembled.reader_view);
  const narrative = asRecord(report.narrative_payload);
  const calculationLayer = asRecord(payload.infographic?.calculation_layer);

  return {
    reportId: report.id,
    status: report.status,
    version: report.version,
    layoutOrder: toLayoutOrder(readerView.layout_order),
    hero: toHeroViewModel(asRecord(readerView.hero), payload.profile),
    sections: toNarrativeSections(narrative),
    calculationLayer: toCalculationLayer(calculationLayer),
    progress: payload.progress,
  };
}

function toHeroViewModel(
  hero: Record<string, unknown>,
  profile: AstrotypeV2FullReportResponse["profile"],
): V2ReportHeroViewModel {
  const displayName = profile?.name?.trim() || "для вас";
  return {
    eyebrow: toPremiumHeroEyebrow(hero.eyebrow),
    title: `Здравствуйте, ${displayName}`,
    greeting: "Ваша натальная карта готова",
    intro:
      "Мы построили её по данным рождения, которые вы указали. Ниже — личный отчёт и аккуратная расчётная основа карты.",
    birthDataItems: toBirthDataItems(profile),
    statusLabel: stringValue(hero.status_label, "Полный отчёт готов"),
    calculationLabel: stringValue(
      hero.calculation_label,
      "Карта и расчёт ниже",
    ),
    pdfLabel: stringValue(hero.pdf_label, "Скачать PDF"),
  };
}

function toPremiumHeroEyebrow(value: unknown): string {
  const raw = stringValue(value, "").trim();
  if (!raw || raw.toLowerCase().includes("v2")) {
    return "Astrotype Signature";
  }
  return raw;
}

function toBirthDataItems(
  profile: AstrotypeV2FullReportResponse["profile"],
): Array<{ label: string; value: string }> {
  if (!profile) return [];
  return [
    { label: "Дата рождения", value: formatDate(profile.birth_date) },
    {
      label: "Время",
      value: formatBirthTime(profile.birth_time, profile.birth_time_accuracy),
    },
    { label: "Место", value: profile.birth_place },
    { label: "Часовой пояс", value: profile.timezone },
  ].filter((item) => item.value.trim().length > 0);
}

function formatDate(value: string): string {
  const parsed = new Date(`${value}T00:00:00`);
  if (Number.isNaN(parsed.getTime())) return value;
  return new Intl.DateTimeFormat("ru-RU", {
    day: "numeric",
    month: "long",
    year: "numeric",
  }).format(parsed);
}

function formatBirthTime(value: string | null, accuracy: string): string {
  if (accuracy === "unknown") return "время не указано, используется 12:00";
  if (!value) return "не указано";
  const [hours, minutes] = value.split(":");
  const label = `${hours}:${minutes}`;
  return accuracy === "approximate" ? `примерно ${label}` : label;
}

function toLayoutOrder(value: unknown): V2ReportLayoutBlock[] {
  const blocks = stringArray(value).filter(
    (block): block is V2ReportLayoutBlock =>
      ["hero", "narrative", "calculation_layer"].includes(block),
  );
  return blocks.length > 0
    ? blocks
    : ["hero", "narrative", "calculation_layer"];
}

function toNarrativeSections(
  narrative: Record<string, unknown>,
): V2NarrativeSectionViewModel[] {
  const sectionsById = new Map(
    recordArray(narrative.sections).map((section) => [
      String(section.section_id),
      section,
    ]),
  );
  const order = stringArray(narrative.section_order);
  const orderedIds = order.length > 0 ? order : [...CANONICAL_V2_SECTION_ORDER];
  return orderedIds
    .map((id) => sectionsById.get(id))
    .filter((section): section is Record<string, unknown> => Boolean(section))
    .map(toNarrativeSection);
}

function toNarrativeSection(
  section: Record<string, unknown>,
): V2NarrativeSectionViewModel {
  const display = asRecord(section.reader_display);
  const bodyText = stringValue(section.body);
  const sectionParagraphs = paragraphs(bodyText);
  return {
    id: stringValue(section.section_id),
    title: stringValue(section.title),
    eyebrow: stringValue(display.eyebrow),
    subtitle: stringValue(display.subtitle),
    bodyText,
    paragraphs: sectionParagraphs,
    paragraphCount: sectionParagraphs.length,
    asideTitle: stringValue(display.aside_title, "В фокусе"),
    asideBullets: stringArray(display.aside_bullets),
    evidenceIds: stringArray(section.evidence_ids),
    coveredThemeIds: stringArray(section.covered_theme_ids),
  };
}

function toCalculationLayer(
  layer: Record<string, unknown>,
): V2CalculationLayerViewModel {
  const keyIndicators = asRecord(layer.key_indicators);
  const houseEmphasis = asRecord(layer.house_emphasis);
  const aspectNetwork = asRecord(layer.aspect_network);
  return {
    readerBlocks: stringArray(layer.reader_blocks),
    keyIndicators: {
      ascendant: toIndicator(keyIndicators.ascendant),
      mc: toIndicator(keyIndicators.mc),
      ascendantRuler: toIndicator(keyIndicators.ascendant_ruler),
      sun: toIndicator(keyIndicators.sun),
      moon: toIndicator(keyIndicators.moon),
    },
    planetPositions: recordArray(layer.planet_positions).map(toPlanetPosition),
    balanceBars: toBalanceBars(layer.balance_bars),
    houseEmphasis: {
      bars: recordArray(houseEmphasis.bars).map(toHouseEmphasisBar),
      topHouses: recordArray(houseEmphasis.top_houses).map(toHouseEmphasisBar),
    },
    aspectNetwork: {
      nodes: recordArray(aspectNetwork.nodes).map(toAspectNode),
      edges: recordArray(aspectNetwork.edges).map(toAspectEdge),
    },
    keyAspects: recordArray(layer.key_aspects).map(toAspect),
    calculationMatrix: toCalculationMatrix(layer.calculation_matrix),
  };
}

function toCalculationMatrix(value: unknown): Record<string, unknown> {
  const matrix = asRecord(value);
  return {
    ...matrix,
    houseMode: asRecord(matrix.house_mode),
    hemispheres: asRecord(matrix.hemispheres),
    quadrants: asRecord(matrix.quadrants),
    aspectProfile: asRecord(matrix.aspect_profile),
  };
}

function toIndicator(value: unknown): V2ChartIndicatorViewModel | undefined {
  const record = asOptionalRecord(value);
  if (!record) return undefined;
  return {
    body: optionalString(record.body),
    planet: optionalLocalizedString(record.planet),
    sign: optionalLocalizedString(record.sign),
    degreeLabel: optionalString(record.degree_label),
    houseNumber: optionalNumber(record.house_number),
    position: toIndicator(record.position),
  };
}

function toPlanetPosition(
  record: Record<string, unknown>,
): V2PlanetPositionViewModel {
  return {
    body: stringValue(record.body),
    sign: localizedAstroLabel(stringValue(record.sign)),
    houseNumber: optionalNumber(record.house_number),
    signDegree: optionalNumber(record.sign_degree),
    degreeLabel: stringValue(record.degree_label),
    retrograde: Boolean(record.retrograde),
    sampledAspects: recordArray(record.sampled_aspects).map(toAspect),
  };
}

function toBalanceBars(
  value: unknown,
): Record<string, V2BalanceBarViewModel[]> {
  const grouped = asRecord(value);
  return Object.fromEntries(
    Object.entries(grouped).map(([category, rows]) => [
      category,
      recordArray(rows).map((row) => toBalanceBar(category, row)),
    ]),
  );
}

function toBalanceBar(
  category: string,
  record: Record<string, unknown>,
): V2BalanceBarViewModel {
  const key = stringValue(record.key);
  return {
    category: stringValue(record.category, category),
    key,
    label: localizedAstroLabel(key),
    value: numberValue(record.value, 0),
    rank: optionalNumber(record.rank),
  };
}

function localizedAstroLabel(value: string): string {
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
      Lilith: "Лилит",
      Ascendant: "Асцендент",
      MC: "MC",
      "North Node": "Северный узел",
      north_node: "Северный узел",
      fire: "Огонь",
      Fire: "Огонь",
      earth: "Земля",
      Earth: "Земля",
      air: "Воздух",
      Air: "Воздух",
      water: "Вода",
      Water: "Вода",
      cardinal: "Кардинальная",
      Cardinal: "Кардинальная",
      fixed: "Фиксированная",
      Fixed: "Фиксированная",
      mutable: "Мутабельная",
      Mutable: "Мутабельная",
      Aries: "Овен",
      aries: "Овен",
      Taurus: "Телец",
      taurus: "Телец",
      Gemini: "Близнецы",
      gemini: "Близнецы",
      Cancer: "Рак",
      cancer: "Рак",
      Leo: "Лев",
      leo: "Лев",
      Virgo: "Дева",
      virgo: "Дева",
      Libra: "Весы",
      libra: "Весы",
      Scorpio: "Скорпион",
      scorpio: "Скорпион",
      Sagittarius: "Стрелец",
      sagittarius: "Стрелец",
      Capricorn: "Козерог",
      capricorn: "Козерог",
      Aquarius: "Водолей",
      aquarius: "Водолей",
      Pisces: "Рыбы",
      pisces: "Рыбы",
    }[value] ?? value
  );
}

function toHouseEmphasisBar(
  record: Record<string, unknown>,
): V2HouseEmphasisBarViewModel {
  return {
    houseNumber: numberValue(record.house_number, 0),
    sign: localizedAstroLabel(stringValue(record.sign)),
    bodyCount: numberValue(record.body_count, 0),
    accentWeight: numberValue(record.accent_weight, 0),
  };
}

function toAspectNode(record: Record<string, unknown>): V2AspectNodeViewModel {
  return {
    id: stringValue(record.id),
    label: localizedAstroLabel(
      stringValue(record.label, stringValue(record.id)),
    ),
    sign: optionalLocalizedString(record.sign),
    houseNumber: optionalNumber(record.house_number),
  };
}

function toAspectEdge(record: Record<string, unknown>): V2AspectEdgeViewModel {
  return {
    source: stringValue(record.source),
    target: stringValue(record.target),
    aspectCode: stringValue(record.aspect_code),
    strength: optionalNumber(record.strength),
    orbDegrees: optionalNumber(record.orb_degrees),
    applying: optionalBoolean(record.applying),
  };
}

function toAspect(record: Record<string, unknown>): V2AspectViewModel {
  return {
    bodyA: stringValue(record.body_a),
    bodyB: stringValue(record.body_b),
    aspectCode: stringValue(record.aspect_code),
    orbDegrees: optionalNumber(record.orb_degrees),
    angleDegrees: optionalNumber(record.angle_degrees),
    applying: optionalBoolean(record.applying),
    strength: optionalNumber(record.strength),
  };
}

function paragraphs(value: unknown): string[] {
  return stringValue(value)
    .split(/\n{2,}/)
    .map((paragraph) => paragraph.trim())
    .filter(Boolean);
}

function asRecord(value: unknown): Record<string, unknown> {
  return asOptionalRecord(value) ?? {};
}

function asOptionalRecord(value: unknown): Record<string, unknown> | undefined {
  if (value && typeof value === "object" && !Array.isArray(value)) {
    return value as Record<string, unknown>;
  }
  return undefined;
}

function recordArray(value: unknown): Array<Record<string, unknown>> {
  return Array.isArray(value) ? value.map(asRecord) : [];
}

function stringArray(value: unknown): string[] {
  return Array.isArray(value)
    ? value.map((item) => String(item)).filter(Boolean)
    : [];
}

function stringValue(value: unknown, fallback = ""): string {
  return typeof value === "string" && value.length > 0 ? value : fallback;
}

function optionalString(value: unknown): string | undefined {
  return typeof value === "string" && value.length > 0 ? value : undefined;
}

function optionalLocalizedString(value: unknown): string | undefined {
  return typeof value === "string" && value.length > 0
    ? localizedAstroLabel(value)
    : undefined;
}

function numberValue(value: unknown, fallback: number): number {
  return typeof value === "number" && Number.isFinite(value) ? value : fallback;
}

function optionalNumber(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function optionalBoolean(value: unknown): boolean | null {
  return typeof value === "boolean" ? value : null;
}
