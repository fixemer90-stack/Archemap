import { TermHelp } from "@/components/glossary/term-help";
import type { ReportGlossaryTerm } from "@/lib/glossary/report-glossary";

const V2_INLINE_TERMS: ReportGlossaryTerm[] = [
  "Натальная карта",
  "Управитель ASC",
  "Профиль аспектов",
  "Сеть ключевых аспектов",
  "Сеть аспектов",
  "Тип домов",
  "Ориентация карты",
  "Ретроградность",
  "Асцендент",
  "Модальность",
  "Стихия",
  "Планета",
  "Аспект",
  "Квадрант",
  "Градус",
  "Знак",
  "Дом",
  "Орб",
  "MC",
];

const TERM_PATTERN = new RegExp(
  `(${V2_INLINE_TERMS.map(escapeRegExp).join("|")})`,
  "giu",
);

interface V2GlossaryTextProps {
  text: string;
}

export function V2GlossaryText({ text }: V2GlossaryTextProps) {
  const parts = splitGlossaryText(text);
  return (
    <>
      {parts.map((part, index) => renderPart(part, `${index}:${String(part)}`))}
    </>
  );
}

export function V2GlossaryTerm({ term }: { term: ReportGlossaryTerm }) {
  return <TermHelp term={term} variant="v2" />;
}

export function v2GlossaryTermFor(text: string): ReportGlossaryTerm | null {
  const normalized = text.toLocaleLowerCase("ru-RU");
  return (
    V2_INLINE_TERMS.find(
      (term) => term.toLocaleLowerCase("ru-RU") === normalized,
    ) ?? null
  );
}

function splitGlossaryText(text: string): Array<string | ReportGlossaryTerm> {
  const parts: Array<string | ReportGlossaryTerm> = [];
  let lastIndex = 0;
  for (const match of text.matchAll(TERM_PATTERN)) {
    const matched = match[0];
    const index = match.index ?? 0;
    if (index > lastIndex) {
      parts.push(text.slice(lastIndex, index));
    }
    const term = v2GlossaryTermFor(matched);
    parts.push(term ?? matched);
    lastIndex = index + matched.length;
  }
  if (lastIndex < text.length) {
    parts.push(text.slice(lastIndex));
  }
  return parts;
}

function renderPart(part: string | ReportGlossaryTerm, key: string) {
  const term = v2GlossaryTermFor(part);
  if (!term) {
    return part;
  }
  return <V2GlossaryTerm key={key} term={term} />;
}

function escapeRegExp(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}
