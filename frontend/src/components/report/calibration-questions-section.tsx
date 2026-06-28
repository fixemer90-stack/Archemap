import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { CalibrationQuestionViewModel } from "@/lib/report/view-model";

interface CalibrationQuestionsSectionProps {
  questions: CalibrationQuestionViewModel[];
}

const ANSWER_TYPE_LABELS: Record<
  CalibrationQuestionViewModel["answer_type"],
  string
> = {
  yes_no: "Да / нет",
  scale_1_5: "Шкала 1–5",
  free_text: "Свободный ответ",
};

export function CalibrationQuestionsSection({
  questions,
}: CalibrationQuestionsSectionProps) {
  if (questions.length === 0) {
    return null;
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Калибровочные вопросы</CardTitle>
      </CardHeader>
      <CardContent className="grid gap-4 text-sm leading-6 text-muted-foreground">
        {questions.map((question, index) => (
          <article key={question.id} className="rounded-lg border p-4">
            <p className="font-medium text-foreground">
              {index + 1}. {question.question}
            </p>
            <p className="mt-2 text-xs uppercase tracking-wide text-muted-foreground">
              Формат ответа: {ANSWER_TYPE_LABELS[question.answer_type]}
            </p>
            <p className="mt-2 text-xs text-muted-foreground">
              Основания: {question.evidence_ids.join(", ")}
            </p>
          </article>
        ))}
      </CardContent>
    </Card>
  );
}
