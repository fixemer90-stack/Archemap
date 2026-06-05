import {
  formatAspectRu,
  formatPlanetPlacementRu,
  signNameRu,
} from "@/lib/astrology/labels";
import type { GeneratedReportApiResponse } from "@/lib/api/report";
import { confidenceLabel } from "@/lib/report/score-labels";

export interface ReportPlanet {
  name: string;
  sign: string;
  degree: number;
  house: number | null;
  is_retrograde: boolean;
}

export interface ReportHouse {
  number: number;
  sign: string;
  longitude: number;
}

export interface ReportAspect {
  planet_a: string;
  aspect_type: string;
  planet_b: string;
  orb: number;
  is_applying: boolean;
}

export interface ReportChartData {
  planets: ReportPlanet[];
  houses: ReportHouse[];
  aspects: ReportAspect[];
}

export interface SocionicsType {
  type: string;
  name: string;
  score: number;
  confidence: number;
  functions: string;
  model_a: number;
}

export interface FunctionStrengths {
  Se: number;
  Si: number;
  Ne: number;
  Ni: number;
  Fe: number;
  Fi: number;
  Te: number;
  Ti: number;
}

export interface ReportSocionicsData {
  top3: SocionicsType[];
  function_strengths: FunctionStrengths;
}

export interface ProfileApiResponse {
  id: string;
  user_id?: string;
  name: string;
  birth_date: string;
  birth_time: string | null;
  birth_time_accuracy: "exact" | "approximate" | "unknown" | string;
  birth_place: string;
  latitude?: number;
  longitude?: number;
  timezone?: string;
}

interface RawPlanet {
  name?: string;
  sign?: string;
  degree?: number;
  sign_degree?: number;
  house?: number | null;
  is_retrograde?: boolean;
}

interface RawHouse {
  number?: number;
  sign?: string;
  longitude?: number;
}

interface RawAspect {
  planet_a?: string;
  aspect_type?: string;
  planet_b?: string;
  orb?: number;
  is_applying?: boolean;
}

interface RawChartData {
  planets?: RawPlanet[];
  houses?: RawHouse[];
  aspects?: RawAspect[];
  socionics?: Partial<ReportSocionicsData>;
  function_strengths?: Partial<FunctionStrengths>;
}

export interface ChartSnapshotApiResponse {
  id: string;
  profile_id: string;
  engine_version?: string;
  chart_data: RawChartData;
  socionics?: Partial<ReportSocionicsData>;
  function_strengths?: Partial<FunctionStrengths>;
  created_at?: string;
}

export interface ReportApiData {
  profile: ProfileApiResponse;
  chartSnapshot: ChartSnapshotApiResponse;
  requestedProduct?: string;
  generatedReport?: GeneratedReportApiResponse;
}

export interface ReportViewModel {
  product: string;
  generated_report?: {
    id: string;
    archetype: string;
    score: number;
    confidence_label: string;
    claims: NonNullable<GeneratedReportApiResponse["report_data"]["claims"]>;
    all_archetype_scores: Record<string, number>;
    quality_warning: string | null;
  };
  chart: ReportChartData;
  socionics: ReportSocionicsData;
  profile: {
    name: string;
    birth_date: string;
    birth_time: string | null;
    birth_time_accuracy: string;
    birth_place: string;
    quality_label: string;
    quality_notice: string;
  };
  summary: {
    main_theme: string;
    strength: string;
    attention: string;
    bullets: string[];
  };
  astrology: {
    sun: string;
    sun_meaning: string;
    moon: string;
    moon_meaning: string;
    ascendant: string;
    ascendant_meaning: string;
    dominant_elements: string;
    modalities: string;
    key_aspects: string[];
    time_sensitive_note: string;
  };
  manifestations: Array<{
    title: string;
    manifestation: string;
    support: string;
    risk?: string;
  }>;
  recommendations: {
    strengthen: string[];
    protect: string[];
    do_not_force: string[];
    environment: string[];
    weekly_checklist: string[];
  };
  archetype: {
    name: string;
    confidence_label: string;
    text: string;
    manifestations: string[];
    light: string;
    shadow: string;
  };
  socionics_summary: {
    type: string;
    name: string;
    confidence_label: string;
    explanation: string;
    insights: string[];
  };
}

export const emptyFunctionStrengths: FunctionStrengths = {
  Se: 0,
  Si: 0,
  Ne: 0,
  Ni: 0,
  Fe: 0,
  Fi: 0,
  Te: 0,
  Ti: 0,
};

const ELEMENT_BY_SIGN: Record<string, string> = {
  Aries: "огонь",
  Leo: "огонь",
  Sagittarius: "огонь",
  Taurus: "земля",
  Virgo: "земля",
  Capricorn: "земля",
  Gemini: "воздух",
  Libra: "воздух",
  Aquarius: "воздух",
  Cancer: "вода",
  Scorpio: "вода",
  Pisces: "вода",
};

const MODALITY_BY_SIGN: Record<string, string> = {
  Aries: "кардинальная",
  Cancer: "кардинальная",
  Libra: "кардинальная",
  Capricorn: "кардинальная",
  Taurus: "фиксированная",
  Leo: "фиксированная",
  Scorpio: "фиксированная",
  Aquarius: "фиксированная",
  Gemini: "мутабельная",
  Virgo: "мутабельная",
  Sagittarius: "мутабельная",
  Pisces: "мутабельная",
};

function toNumber(value: number | undefined, fallback = 0): number {
  return typeof value === "number" && Number.isFinite(value) ? value : fallback;
}

function normalizePlanets(planets: RawPlanet[] | undefined): ReportPlanet[] {
  return (planets ?? []).map((planet) => ({
    name: planet.name ?? "Unknown",
    sign: planet.sign ?? "Unknown",
    degree: toNumber(planet.degree ?? planet.sign_degree),
    house: planet.house ?? null,
    is_retrograde: Boolean(planet.is_retrograde),
  }));
}

function normalizeHouses(houses: RawHouse[] | undefined): ReportHouse[] {
  return (houses ?? []).map((house, index) => ({
    number: house.number ?? index + 1,
    sign: house.sign ?? "Unknown",
    longitude: toNumber(house.longitude),
  }));
}

function normalizeAspects(aspects: RawAspect[] | undefined): ReportAspect[] {
  return (aspects ?? []).map((aspect) => ({
    planet_a: aspect.planet_a ?? "Unknown",
    aspect_type: aspect.aspect_type ?? "unknown",
    planet_b: aspect.planet_b ?? "Unknown",
    orb: toNumber(aspect.orb),
    is_applying: Boolean(aspect.is_applying),
  }));
}

function normalizeFunctionStrengths(
  strengths: Partial<FunctionStrengths> | undefined,
): FunctionStrengths {
  return {
    Se: toNumber(strengths?.Se),
    Si: toNumber(strengths?.Si),
    Ne: toNumber(strengths?.Ne),
    Ni: toNumber(strengths?.Ni),
    Fe: toNumber(strengths?.Fe),
    Fi: toNumber(strengths?.Fi),
    Te: toNumber(strengths?.Te),
    Ti: toNumber(strengths?.Ti),
  };
}

function normalizeSocionics(
  snapshot: ChartSnapshotApiResponse,
): ReportSocionicsData {
  const source = snapshot.socionics ?? snapshot.chart_data.socionics;
  return {
    top3: source?.top3 ?? [],
    function_strengths: normalizeFunctionStrengths(
      source?.function_strengths ??
        snapshot.function_strengths ??
        snapshot.chart_data.function_strengths ??
        emptyFunctionStrengths,
    ),
  };
}

function findPlanet(
  chart: ReportChartData,
  name: string,
): ReportPlanet | undefined {
  return chart.planets.find((planet) => planet.name === name);
}

function formatPlanet(
  planet: ReportPlanet | undefined,
  fallback: string,
): string {
  if (!planet) {
    return fallback;
  }
  return formatPlanetPlacementRu({
    sign: planet.sign,
    degree: planet.degree,
    house: planet.house,
  });
}

function signElement(sign: string | undefined): string | undefined {
  return sign ? ELEMENT_BY_SIGN[sign] : undefined;
}

function dominantLabel(
  counts: Record<string, number>,
  fallback: string,
): string {
  const sorted = Object.entries(counts).sort((a, b) => b[1] - a[1]);
  const [first, firstCount] = sorted[0] ?? [fallback, 0];
  const second = sorted[1];
  if (firstCount === 0) {
    return fallback;
  }
  if (second && second[1] === firstCount) {
    return `${first} и ${second[0]}`;
  }
  return first;
}

function buildElementSummary(chart: ReportChartData): string {
  const counts = { огонь: 0, земля: 0, воздух: 0, вода: 0 };
  for (const planet of chart.planets) {
    const element = signElement(planet.sign);
    if (element) {
      counts[element as keyof typeof counts] += 1;
    }
  }
  const dominant = dominantLabel(counts, "смешанный баланс");
  return `Главная стихия по планетам: ${dominant}. Это показывает базовый стиль энергии: действие, практика, идеи или эмоциональная настройка.`;
}

function buildModalitySummary(chart: ReportChartData): string {
  const counts = { кардинальная: 0, фиксированная: 0, мутабельная: 0 };
  for (const planet of chart.planets) {
    const modality = MODALITY_BY_SIGN[planet.sign];
    if (modality) {
      counts[modality as keyof typeof counts] += 1;
    }
  }
  const dominant = dominantLabel(counts, "смешанная модальность");
  return `Главная модальность: ${dominant}. Она описывает, как легче двигаться: начинать, удерживать курс или адаптироваться.`;
}

function buildKeyAspects(chart: ReportChartData): string[] {
  const keyAspects = chart.aspects
    .slice()
    .sort((a, b) => a.orb - b.orb)
    .slice(0, 4)
    .map((aspect) => {
      return formatAspectRu({
        planetA: aspect.planet_a,
        planetB: aspect.planet_b,
        aspectType: aspect.aspect_type,
        orb: aspect.orb,
        isApplying: aspect.is_applying,
      });
    });

  return keyAspects.length > 0
    ? keyAspects
    : [
        "В snapshot нет аспектов: отчёт честно ограничивает evidence по связям карты.",
      ];
}

function qualityLabel(accuracy: string): string {
  if (accuracy === "exact") {
    return "точное время рождения";
  }
  if (accuracy === "approximate") {
    return "приблизительное время рождения";
  }
  return "время рождения неизвестно";
}

function birthTimeWarning(accuracy: string): string {
  if (accuracy === "exact") {
    return "Время рождения точное: дома и Асцендент можно читать как полноценную часть отчёта.";
  }
  if (accuracy === "approximate") {
    return "Время рождения приблизительное: дома и Асцендент читаются как гипотеза, а не как жёсткий вывод.";
  }
  return "Время рождения неизвестно: выводы по домам и Асценденту ограничены, основной упор стоит делать на планеты и аспекты.";
}

function buildArchetypeName(chart: ReportChartData): string {
  const element = dominantLabel(
    chart.planets.reduce(
      (acc, planet) => {
        const current = signElement(planet.sign);
        if (current) {
          acc[current] += 1;
        }
        return acc;
      },
      { огонь: 0, земля: 0, воздух: 0, вода: 0 } as Record<string, number>,
    ),
    "смешанный профиль",
  );

  if (element.includes("огонь")) return "Инициатор";
  if (element.includes("земля")) return "Практик";
  if (element.includes("воздух")) return "Связующий";
  if (element.includes("вода")) return "Настройщик";
  return "Интегратор";
}

function buildSocionicsSummary(
  socionics: ReportSocionicsData,
): ReportViewModel["socionics_summary"] {
  const primary = socionics.top3[0];
  if (!primary) {
    return {
      type: "не рассчитан",
      name: "Соционический слой недоступен",
      confidence_label: "уверенность не рассчитана",
      explanation:
        "API не вернул top types для этого snapshot, поэтому основной отчёт не подставляет выдуманный тип.",
      insights: [
        "Сначала читайте астрологическую основу и практические рекомендации.",
        "Технический блок ниже покажет, что именно пришло из API.",
        "Типологическую гипотезу стоит добавить только после появления данных.",
      ],
    };
  }

  return {
    type: primary.type,
    name: primary.name,
    confidence_label: confidenceLabel(primary.confidence),
    explanation: `${primary.name} (${primary.type}) читается как гипотеза о способе обработки информации, решений и взаимодействия с людьми.`,
    insights: [
      "Используйте тип как язык наблюдения, а не как ярлык личности.",
      "Сравните вывод с блоками про мышление, эмоции, отношения и работу.",
      "Если уверенность не высокая, читайте тип мягко и проверяйте по жизненным примерам.",
      "Полная Model A и Top-3 оставлены в технических деталях.",
    ],
  };
}

export function toReportViewModel(data: ReportApiData): ReportViewModel {
  const chart: ReportChartData = {
    planets: normalizePlanets(data.chartSnapshot.chart_data.planets),
    houses: normalizeHouses(data.chartSnapshot.chart_data.houses),
    aspects: normalizeAspects(data.chartSnapshot.chart_data.aspects),
  };
  const socionics = normalizeSocionics(data.chartSnapshot);
  const sun = findPlanet(chart, "Sun");
  const moon = findPlanet(chart, "Moon");
  const ascendant = chart.houses[0];
  const hasSocionics = socionics.top3.length > 0;
  const archetypeName = buildArchetypeName(chart);
  const profileName = data.profile.name || "Ваш отчёт";
  const timeNotice = birthTimeWarning(data.profile.birth_time_accuracy);
  const generatedArchetype = data.generatedReport?.report_data.archetype;
  const generatedReport = data.generatedReport
    ? {
        id: data.generatedReport.id,
        archetype:
          generatedArchetype?.primary ??
          data.generatedReport.archetype ??
          "Карьерный профиль",
        score: generatedArchetype?.score ?? data.generatedReport.score ?? 0,
        confidence_label:
          generatedArchetype?.confidence?.label ??
          confidenceLabel(data.generatedReport.confidence ?? 0),
        claims: data.generatedReport.report_data.claims ?? [],
        all_archetype_scores:
          data.generatedReport.report_data.all_archetype_scores ?? {},
        quality_warning:
          data.generatedReport.report_data.quality_warning ?? null,
      }
    : undefined;
  const sunSign = signNameRu(sun?.sign);
  const moonSign = signNameRu(moon?.sign);
  const ascendantSign = signNameRu(ascendant?.sign);

  return {
    product: generatedReport
      ? (data.generatedReport?.product ?? "self")
      : "self",
    generated_report: generatedReport,
    chart,
    socionics,
    profile: {
      name: profileName,
      birth_date: data.profile.birth_date,
      birth_time: data.profile.birth_time,
      birth_time_accuracy: data.profile.birth_time_accuracy,
      birth_place: data.profile.birth_place,
      quality_label: qualityLabel(data.profile.birth_time_accuracy),
      quality_notice: timeNotice,
    },
    summary: {
      main_theme: sun
        ? `Главная тема карты — проявлять ${sunSign} через реальные решения, выборы и личную инициативу.`
        : "Главная тема карты читается осторожно: в snapshot нет Солнца.",
      strength: moon
        ? `Сильная опора — понимать свой эмоциональный ритм: Луна в ${moonSign} показывает, как возвращаться в ресурс.`
        : "Сильная опора пока описана общо: в snapshot нет Луны.",
      attention:
        data.profile.birth_time_accuracy === "exact"
          ? "Зона внимания — сверять смысловые выводы с техническими деталями только когда нужна проверка расчёта."
          : "Зона внимания — не переоценивать дома и Асцендент, потому что время рождения не полностью надёжно.",
      bullets: [
        `Отчёт построен по реальным данным профиля «${profileName}» и текущему snapshot карты.`,
        sun
          ? `Солнце в ${sunSign} задаёт главный фокус интерпретации.`
          : "Солнце не найдено — нужен повторный расчёт карты.",
        moon
          ? `Луна в ${moonSign} помогает описать эмоции и восстановление.`
          : "Луна не найдена — эмоциональный блок читается осторожно.",
        `Качество времени рождения: ${qualityLabel(data.profile.birth_time_accuracy)}.`,
      ],
    },
    astrology: {
      sun: formatPlanet(
        sun,
        "Солнце отсутствует в snapshot карты — требуется проверить расчёт.",
      ),
      sun_meaning: sun
        ? "Показывает главный способ проявлять себя, выбирать направление и чувствовать авторство."
        : "Без Солнца главный фокус отчёта нельзя считать полным.",
      moon: formatPlanet(
        moon,
        "Луна отсутствует в snapshot карты — требуется проверить расчёт.",
      ),
      moon_meaning: moon
        ? "Описывает восстановление, эмоциональные реакции и базовую потребность в безопасности."
        : "Без Луны эмоциональные выводы остаются ограниченными.",
      ascendant: ascendant
        ? `${ascendantSign} ${ascendant.longitude.toFixed(1)}°`
        : "Асцендент недоступен",
      ascendant_meaning: ascendant
        ? `Показывает стиль входа в ситуации и самопрезентации. ${timeNotice}`
        : timeNotice,
      dominant_elements: buildElementSummary(chart),
      modalities: buildModalitySummary(chart),
      key_aspects: buildKeyAspects(chart),
      time_sensitive_note: timeNotice,
    },
    manifestations: [
      {
        title: "Мышление и решения",
        manifestation: sun
          ? `Солнце в ${sunSign} подсказывает, что решения лучше принимать через ясную личную позицию и проверку “зачем мне это”.`
          : "Главный стиль решений описан осторожно, потому что в snapshot нет Солнца.",
        support:
          "Перед важным выбором формулировать критерии успеха и отделять свои цели от ожиданий окружения.",
        risk: "Риск — уходить в чужие сценарии, если нет понятного личного фокуса.",
      },
      {
        title: "Эмоции и восстановление",
        manifestation: moon
          ? `Луна в ${moonSign} показывает, что ресурс возвращается через подходящий эмоциональный ритм и безопасную среду.`
          : "Эмоциональный блок ограничен: в snapshot нет Луны.",
        support:
          "Планировать восстановление заранее, а не ждать полного истощения.",
        risk: "Риск — считать усталость слабостью и игнорировать сигналы тела/эмоций.",
      },
      {
        title: "Общение и отношения",
        manifestation: hasSocionics
          ? "Соционический слой добавляет гипотезу о коммуникации, но читается после астрологической основы."
          : "Коммуникационный блок опирается на карту; соционический тип не подставляется без API-данных.",
        support:
          "Проговаривать ожидания и формат взаимодействия: темп, границы, обратную связь.",
        risk: "Риск — путать типологическую гипотезу с живым человеком и реальным контекстом.",
      },
      {
        title: "Работа и фокус",
        manifestation:
          "Доминирующие стихии и модальности показывают, где легче держать внимание: через действие, структуру, идеи или эмоциональный смысл.",
        support:
          "Собирать неделю вокруг 1–2 главных задач и оставлять место для восстановления.",
        risk: "Риск — пытаться работать через силу в ритме, который противоречит собственному паттерну энергии.",
      },
    ],
    recommendations: {
      strengthen: [
        "Усиливать главный фокус карты: выбирать задачи, где есть личный смысл и понятный результат.",
        "Регулярно сверять решения с тем, что даёт энергию, а не только с внешней полезностью.",
      ],
      protect: [
        "Беречь восстановление: эмоциональный ритм влияет на качество решений сильнее, чем кажется.",
        "Беречь точность данных: при неточном времени не делать жёстких выводов по домам и ASC.",
      ],
      do_not_force: [
        "Не заставлять себя жить по типологическому ярлыку — это инструмент наблюдения, а не приговор.",
        "Не читать проценты как абсолютную истину; confidence показывает качество гипотезы.",
      ],
      environment: [
        "Выбирать среду, где можно проговаривать ожидания и получать ясную обратную связь.",
        "Держать рядом простой ритуал проверки: что важно, что забирает ресурс, какой следующий шаг.",
      ],
      weekly_checklist: [
        "Выбрать одну главную тему недели и записать ожидаемый результат.",
        "Запланировать два окна восстановления без задач и переговоров.",
        "Проверить один вывод отчёта на реальном примере из жизни.",
        "Открыть technical details только для проверки спорного вывода, не для первого чтения.",
      ],
    },
    archetype: {
      name: archetypeName,
      confidence_label: hasSocionics
        ? confidenceLabel(socionics.top3[0].confidence)
        : "средняя уверенность",
      text: `Архетип «${archetypeName}» — короткое имя для ведущего паттерна карты. Он помогает запомнить стиль, но не заменяет подробные выводы выше.`,
      manifestations: [
        "быстрее замечать ситуации, где естественная стратегия уже работает",
        "выделять условия, в которых сильная сторона раскрывается без чрезмерного напряжения",
        "видеть тень паттерна и вовремя смягчать её через осознанный выбор",
      ],
      light:
        "Сильная сторона — использовать естественный стиль как опору для решений, работы и отношений.",
      shadow:
        "Тень — превращать полезный паттерн в жёсткий сценарий и игнорировать контекст.",
    },
    socionics_summary: buildSocionicsSummary(socionics),
  };
}
