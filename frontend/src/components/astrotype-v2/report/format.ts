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

export function percentWidth(value: number): string {
  const normalized = value > 0 && value <= 1 ? value * 100 : value;
  return `${Math.max(0, Math.min(100, normalized))}%`;
}
