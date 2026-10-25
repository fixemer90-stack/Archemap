import Link from "next/link";
import { ApiError } from "@/lib/api-client";

export function childErrorCopy(error: unknown) {
  if (error instanceof ApiError) {
    if (error.status === 401)
      return "Сессия завершилась. Войдите снова — сохранённые данные останутся на месте.";
    if (error.status === 402 || error.status === 403)
      return "Этот раздел доступен с активным Plus. Данные ребёнка не загружены.";
    if (error.status === 404)
      return "Данные недоступны. Проверьте ссылку или выберите ребёнка из своего списка.";
    if (error.status === 503)
      return "Раздел пока недоступен. Мы открываем его поэтапно. Попробуйте позже.";
    if (error.status === 409)
      return "Данные изменились. Обновите страницу и проверьте выбранного ребёнка перед продолжением.";
    if (error.status === 422)
      return "Проверьте введённые данные и обязательные ответы. Не нужно угадывать неизвестное время рождения.";
  }
  return "Не удалось сохранить или загрузить данные. Попробуйте ещё раз; уже сохранённые ответы не потеряются.";
}
export function ChildError({ error }: { error: unknown }) {
  return (
    <div role="alert" className="child-notice">
      <p>{childErrorCopy(error)}</p>
      {error instanceof ApiError && error.status === 401 && (
        <Link href="/login">Войти снова</Link>
      )}
      {error instanceof ApiError && [402, 403].includes(error.status) && (
        <Link href="/subscriptions">Посмотреть Plus</Link>
      )}
    </div>
  );
}
export const timeLabels = {
  exact: "Точное время",
  approximate: "Приблизительное время",
  unknown: "Время неизвестно",
};
export function ChildGenerationCopy({ status }: { status: string }) {
  return (
    <p role="status">
      {status === "ready"
        ? "Отчёт готов."
        : status === "narrative_failed" || status === "child_narrative_disabled"
          ? "Часть пояснений недоступна. Готовая основа отчёта сохранена и доступна для чтения."
          : status === "failed"
            ? "Не удалось подготовить отчёт. Неподтверждённые результаты не показаны."
            : status === "narrative_retry_waiting"
              ? "Пояснения появятся позже. Готовую часть уже можно читать."
              : "Готовим отчёт. Сначала появится основа, затем — пояснения по разделам."}
    </p>
  );
}
