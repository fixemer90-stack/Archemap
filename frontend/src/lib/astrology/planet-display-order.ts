// Presentation only: never reorder stored chart data or change body labels.
const BODY_ALIASES = [
  ["Sun", "Солнце"],
  ["Moon", "Луна"],
  ["Mercury", "Меркурий"],
  ["Venus", "Венера"],
  ["Mars", "Марс"],
  ["Jupiter", "Юпитер"],
  ["Saturn", "Сатурн"],
  ["Uranus", "Уран"],
  ["Neptune", "Нептун"],
  ["Pluto", "Плутон"],
  ["Chiron", "Хирон"],
  ["North Node", "Северный узел", "Восходящий узел", "Раху"],
  ["South Node", "Южный узел", "Нисходящий узел", "Кету"],
  ["Lilith", "Лилит", "Черная Луна", "Чёрная Луна"],
  ["Part of Fortune", "Pars Fortuna", "Парс Фортуны", "Колесо Фортуны"],
  ["Vertex", "Вертекс"],
  ["Ascendant", "ASC", "Асцендент"],
  ["MC", "Midheaven", "Середина неба", "МС"],
];

function normalizeBody(body: string): string {
  return body
    .trim()
    .toLowerCase()
    .replace(/[_\s-]+/g, " ");
}

const BODY_RANK = new Map(
  BODY_ALIASES.flatMap((aliases, rank) =>
    aliases.map((alias) => [normalizeBody(alias), rank] as const),
  ),
);

/** Main ten, then known points; equal ranks and unknowns retain input order.
 * Returns a new array, preserving the original objects and all their fields.
 */
export function orderPlanetPositions<T>(
  positions: readonly T[],
  bodyOf: (position: T) => string,
): T[] {
  const rank = (position: T) =>
    BODY_RANK.get(normalizeBody(bodyOf(position))) ?? BODY_ALIASES.length;
  return [...positions].sort((left, right) => rank(left) - rank(right));
}
