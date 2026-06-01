export function confidenceLabel(value: number | undefined): string {
  const confidence =
    typeof value === "number" && Number.isFinite(value) ? value : 0;

  if (confidence >= 0.75) {
    return "высокая уверенность";
  }
  if (confidence >= 0.5) {
    return "средняя уверенность";
  }
  if (confidence > 0) {
    return "низкая уверенность";
  }
  return "уверенность не рассчитана";
}

export function expressionLabel(value: number | undefined): string {
  const score = typeof value === "number" && Number.isFinite(value) ? value : 0;

  if (score >= 0.75) {
    return "сильная выраженность";
  }
  if (score >= 0.45) {
    return "средняя выраженность";
  }
  if (score > 0) {
    return "мягкая выраженность";
  }
  return "нет надёжной оценки";
}
