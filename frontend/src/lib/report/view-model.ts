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
}

export interface ReportViewModel {
  chart: ReportChartData;
  socionics: ReportSocionicsData;
  profile: {
    name: string;
    birth_date: string;
    birth_time: string | null;
    birth_time_accuracy: string;
    birth_place: string;
  };
  summary: string[];
  astrology: {
    sun: string;
    moon: string;
    ascendant: string;
    dominant_elements: string;
    modalities: string;
    key_aspects: string[];
  };
  manifestations: Array<{
    title: string;
    text: string;
    advice: string;
  }>;
  recommendations: string[];
  archetype: {
    name: string;
    confidence_label: string;
    text: string;
    light: string;
    shadow: string;
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

function normalizeSocionics(snapshot: ChartSnapshotApiResponse): ReportSocionicsData {
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

function findPlanet(chart: ReportChartData, name: string): ReportPlanet | undefined {
  return chart.planets.find((planet) => planet.name === name);
}

function formatPlanetMeaning(
  planet: ReportPlanet | undefined,
  fallback: string,
): string {
  if (!planet) {
    return fallback;
  }
  const house = planet.house ? `, дом ${planet.house}` : "";
  return `${planet.sign} ${planet.degree.toFixed(2)}°${house}`;
}

function buildSummary(profile: ProfileApiResponse, chart: ReportChartData): string[] {
  const sun = findPlanet(chart, "Sun");
  const moon = findPlanet(chart, "Moon");
  const aspectCount = chart.aspects.length;

  return [
    `Отчёт построен по реальным данным профиля «${profile.name || "Ваш отчёт"}» и текущему snapshot натальной карты.`,
    sun
      ? `Солнце в ${sun.sign} задаёт главный фокус интерпретации; детали карты доступны ниже в техническом блоке.`
      : "Солнце не найдено в snapshot карты, поэтому главный фокус интерпретации показан осторожно.",
    moon
      ? `Луна в ${moon.sign} помогает описать эмоциональный ритм и восстановление.`
      : "Луна не найдена в snapshot карты, поэтому эмоциональный блок требует уточнения данных.",
    aspectCount > 0
      ? `В карте найдено ${aspectCount} аспектов; в основном отчёте используются только ключевые связи, полный список скрыт в technical details.`
      : "Аспекты отсутствуют в snapshot: отчёт остаётся читаемым, но evidence по связям карты ограничен.",
  ];
}

function buildKeyAspects(chart: ReportChartData): string[] {
  const keyAspects = chart.aspects.slice(0, 4).map((aspect) => {
    const direction = aspect.is_applying ? "сходящийся" : "расходящийся";
    return `${aspect.planet_a} — ${aspect.planet_b}: ${aspect.aspect_type}, орб ${aspect.orb.toFixed(2)}° (${direction}).`;
  });

  if (keyAspects.length > 0) {
    return keyAspects;
  }

  return ["В snapshot нет аспектов: подробное evidence по связям карты пока недоступно."];
}

function birthTimeWarning(accuracy: string): string {
  if (accuracy === "exact") {
    return "Время рождения точное: дома и Ascendant можно читать как полноценную часть отчёта.";
  }
  if (accuracy === "approximate") {
    return "Время рождения приблизительное: дома и Ascendant читаются как гипотеза, а не как жёсткий вывод.";
  }
  return "Время рождения неизвестно: выводы по домам и Ascendant ограничены, основной упор стоит делать на планеты и аспекты.";
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

  return {
    chart,
    socionics,
    profile: {
      name: data.profile.name || "Ваш отчёт",
      birth_date: data.profile.birth_date,
      birth_time: data.profile.birth_time,
      birth_time_accuracy: data.profile.birth_time_accuracy,
      birth_place: data.profile.birth_place,
    },
    summary: buildSummary(data.profile, chart),
    astrology: {
      sun: formatPlanetMeaning(
        sun,
        "Солнце отсутствует в snapshot карты — требуется проверить расчёт.",
      ),
      moon: formatPlanetMeaning(
        moon,
        "Луна отсутствует в snapshot карты — требуется проверить расчёт.",
      ),
      ascendant: ascendant
        ? `${ascendant.sign} ${ascendant.longitude.toFixed(2)}°. ${birthTimeWarning(data.profile.birth_time_accuracy)}`
        : birthTimeWarning(data.profile.birth_time_accuracy),
      dominant_elements:
        "Агрегация стихий будет подключена отдельной UX-story; сейчас основной блок использует реальные планеты snapshot без mock-данных.",
      modalities:
        "Агрегация модальностей будет подключена отдельной UX-story; технические исходные данные сохранены ниже.",
      key_aspects: buildKeyAspects(chart),
    },
    manifestations: [
      {
        title: "Мышление и решения",
        text: "Первый слой выводов строится на реальных факторах карты. Если часть данных отсутствует, отчёт явно показывает ограничение вместо подстановки mock-текста.",
        advice: "Смотреть на summary как на стартовую гипотезу и при необходимости раскрывать technical details.",
      },
      {
        title: "Эмоции и восстановление",
        text: moon
          ? `Луна в ${moon.sign} используется как базовый маркер эмоционального ритма.`
          : "Эмоциональный блок ограничен: в snapshot нет Луны.",
        advice: "Уточнить данные рождения, если эмоциональные выводы выглядят слишком общими.",
      },
      {
        title: "Коммуникация и отношения",
        text: hasSocionics
          ? "Соционический слой доступен как дополнительная линза и не подменяет астрологическую основу."
          : "Соционический слой пока не пришёл из API; страница остаётся рабочей и показывает fallback без падения.",
        advice: "Читать типологию после астрологической основы и практических выводов.",
      },
      {
        title: "Работа и фокус",
        text: "Практические выводы будут расширены отдельной story на рекомендации; текущий слой гарантирует real-data contract.",
        advice: "Использовать technical details для проверки исходных факторов карты.",
      },
    ],
    recommendations: [
      "Проверьте, что дата, время и место рождения в header совпадают с ожидаемыми данными профиля.",
      "Если время рождения неизвестно или приблизительно, осторожнее читайте дома и Ascendant.",
      "Открывайте technical details только когда нужно проверить исходные планеты, дома, аспекты, scores или evidence.",
    ],
    archetype: {
      name: hasSocionics ? socionics.top3[0].name : "Будет рассчитан после подключения report API",
      confidence_label: hasSocionics
        ? `уверенность ${(socionics.top3[0].confidence * 100).toFixed(0)}%`
        : "нет данных API",
      text: hasSocionics
        ? `Доступен реальный типологический слой: ${socionics.top3[0].type}. Архетипический текст будет расширен в отдельной story.`
        : "Backend ещё не вернул archetype/socionics output для этого snapshot. Вместо mock-данных показан честный fallback.",
      light: "Страница больше не подставляет выдуманные данные: пользователь видит только то, что пришло из API, плюс явно помеченные fallback-и.",
      shadow: "Часть смысловых формулировок останется общей до подключения полноценного report/archetype API.",
    },
  };
}
