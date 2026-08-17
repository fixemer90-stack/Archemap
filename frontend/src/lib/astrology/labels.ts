export const PLANET_SYMBOLS: Record<string, string> = {
  Sun: "☉",
  Moon: "☽",
  Mercury: "☿",
  Venus: "♀",
  Mars: "♂",
  Jupiter: "♃",
  Saturn: "♄",
  Uranus: "♅",
  Neptune: "♆",
  Pluto: "♇",
  "North Node": "☊",
  Lilith: "⚸",
  Chiron: "⚷",
};

export const SIGN_SYMBOLS: Record<string, string> = {
  Aries: "♈",
  Taurus: "♉",
  Gemini: "♊",
  Cancer: "♋",
  Leo: "♌",
  Virgo: "♍",
  Libra: "♎",
  Scorpio: "♏",
  Sagittarius: "♐",
  Capricorn: "♑",
  Aquarius: "♒",
  Pisces: "♓",
};

const PLANET_NAMES_RU: Record<string, string> = {
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
  "North Node": "Северный узел",
  Lilith: "Лилит",
  Chiron: "Хирон",
  Unknown: "Неизвестная планета",
};

const SIGN_NAMES_RU: Record<string, string> = {
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
  Unknown: "неизвестном знаке",
};

const ASPECT_TYPES_RU: Record<string, string> = {
  conjunction: "соединение",
  opposition: "оппозиция",
  trine: "трин",
  sextile: "секстиль",
  square: "квадрат",
  quincunx: "квинконс",
  unknown: "неизвестный аспект",
};

export function planetNameRu(name: string | undefined): string {
  if (!name) return PLANET_NAMES_RU.Unknown;
  return PLANET_NAMES_RU[name] ?? name;
}

export function signNameRu(sign: string | undefined): string {
  if (!sign) return SIGN_NAMES_RU.Unknown;
  return SIGN_NAMES_RU[sign] ?? sign;
}

export function aspectTypeRu(aspectType: string | undefined): string {
  if (!aspectType) return ASPECT_TYPES_RU.unknown;
  return ASPECT_TYPES_RU[aspectType] ?? aspectType;
}

export function aspectDirectionRu(isApplying: boolean): string {
  return isApplying ? "сходящийся" : "расходящийся";
}

export function formatPlanetPlacementRu({
  sign,
  degree,
  house,
}: {
  sign: string | undefined;
  degree: number;
  house?: number | null;
}): string {
  const houseText = house ? `, ${house} дом` : "";
  return `${signNameRu(sign)} ${degree.toFixed(1)}°${houseText}`;
}

export function formatAspectRu({
  planetA,
  planetB,
  aspectType,
  orb,
  isApplying,
}: {
  planetA: string | undefined;
  planetB: string | undefined;
  aspectType: string | undefined;
  orb: number;
  isApplying: boolean;
}): string {
  return `${planetNameRu(planetA)} — ${planetNameRu(planetB)}: ${aspectTypeRu(
    aspectType,
  )}, орб ${orb.toFixed(2)}° (${aspectDirectionRu(isApplying)}).`;
}
