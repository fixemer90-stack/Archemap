export function formatValue(value: unknown): string {
  if (typeof value === "number") {
    return Number.isInteger(value) ? String(value) : value.toFixed(2);
  }
  if (typeof value === "string" && value.length > 0) {
    return value;
  }
  if (typeof value === "boolean") {
    return value ? "да" : "нет";
  }
  return "—";
}

export function normalizePercent(value: number): number {
  const normalized = value > 0 && value <= 1 ? value * 100 : value;
  return Math.max(0, Math.min(100, normalized));
}

export function percentWidth(value: number): string {
  return `${normalizePercent(value)}%`;
}

export function formatPercent(value: number): string {
  const normalized = normalizePercent(value);
  const rounded = Number(normalized.toFixed(1));
  return `${rounded}%`;
}

export function localizeAstroLabel(value: string): string {
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

export function localizeAspectLabel(aspectCode: string): string {
  return (
    {
      conjunction: "соединение",
      opposition: "оппозиция",
      trine: "трин",
      square: "квадрат",
      sextile: "секстиль",
      quincunx: "квинконс",
    }[aspectCode] ?? aspectCode
  );
}

export function aspectTone(aspectCode: string): "resource" | "tension" {
  return ["trine", "sextile"].includes(aspectCode) ? "resource" : "tension";
}
