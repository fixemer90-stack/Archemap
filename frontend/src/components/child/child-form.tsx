"use client";

import { useEffect, useRef, useState } from "react";
import { apiClient } from "@/lib/api-client";
import { newChildKey } from "@/lib/api/child";
import {
  searchBirthPlaces,
  type GeocodeSuggestion,
} from "@/lib/api/birth-data-refinement";
import type { BirthTimeConfidence, ChildRecord } from "@/types/child";
import { ChildError, timeLabels } from "./child-shared";

export function ChildForm({
  child,
  onSaved,
  onCancel,
}: {
  child?: ChildRecord;
  onSaved: (child: ChildRecord) => void;
  onCancel: () => void;
}) {
  const [name, setName] = useState(child?.display_name ?? "");
  const [date, setDate] = useState(child?.birth_date ?? "");
  const [time, setTime] = useState(child?.birth_time?.slice(0, 5) ?? "");
  const [confidence, setConfidence] = useState<BirthTimeConfidence>(
    child?.birth_time_confidence ?? "unknown",
  );
  const [relationship, setRelationship] = useState(
    child?.relationship_type ?? "parent",
  );
  const [place, setPlace] = useState(child?.birth_place ?? null);
  const [query, setQuery] = useState(child?.birth_place.label ?? "");
  const [suggestions, setSuggestions] = useState<GeocodeSuggestion[]>([]);
  const [placeLoading, setPlaceLoading] = useState(false);
  const [context, setContext] = useState(
    child?.caregiver_context ?? {
      primary_caregiver: true,
      daily_contact: "high",
      boundary_role: "shared",
      soothing_role: "shared",
    },
  );
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);
  const key = useRef<string | null>(null);
  const heading = useRef<HTMLHeadingElement>(null);
  useEffect(() => {
    heading.current?.focus();
  }, []);
  useEffect(() => {
    if (place || query.trim().length < 2) return;
    let active = true;
    const timer = setTimeout(() => {
      setPlaceLoading(true);
      searchBirthPlaces(query)
        .then((data) => {
          if (active) setSuggestions(data.items);
        })
        .catch((e) => {
          if (active) setError(e);
        })
        .finally(() => {
          if (active) setPlaceLoading(false);
        });
    }, 350);
    return () => {
      active = false;
      clearTimeout(timer);
    };
  }, [query, place]);
  async function save(event: React.FormEvent) {
    event.preventDefault();
    if (!place || busy) return;
    setBusy(true);
    setError(null);
    try {
      key.current ??= newChildKey(child ? "edit" : "create");
      const body = {
        display_name: name.trim(),
        relationship_type: relationship,
        birth_date: date,
        birth_time: confidence === "unknown" ? null : time,
        birth_time_confidence: confidence,
        birth_place: place,
        caregiver_context: context,
      };
      const saved = await apiClient<ChildRecord>(
        `/api/v1/child/children${child ? `/${encodeURIComponent(child.id)}` : ""}`,
        {
          method: child ? "PATCH" : "POST",
          body,
          headers: { "Idempotency-Key": key.current },
        },
      );
      // Read the exact record back before replacing selected context.
      const confirmed = await apiClient<ChildRecord>(
        `/api/v1/child/children/${encodeURIComponent(saved.id)}`,
      );
      onSaved(confirmed);
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  }
  return (
    <section
      className="child-panel child-stack"
      aria-labelledby="child-form-title"
    >
      <h2 id="child-form-title" ref={heading} tabIndex={-1}>
        {child ? `Данные ребёнка: ${child.display_name}` : "Добавить ребёнка"}
      </h2>
      {child && (
        <p className="child-notice">
          Вы меняете данные ребёнка {child.display_name}. Исправление даты,
          времени или места создаст новую версию карты и новую основу будущего
          отчёта. Предыдущие отчёты и возрастные снимки сохранятся без
          изменений.
        </p>
      )}
      {error != null && <ChildError error={error} />}
      <form className="child-form child-stack" onSubmit={(e) => void save(e)}>
        <div className="child-grid">
          <label>
            Имя или псевдоним
            <input
              required
              maxLength={120}
              value={name}
              onChange={(e) => setName(e.target.value)}
              autoComplete="off"
            />
          </label>
          <label>
            Дата рождения
            <input
              type="date"
              required
              value={date}
              onChange={(e) => setDate(e.target.value)}
            />
          </label>
        </div>
        <fieldset className="child-fieldset">
          <legend>Насколько известно время рождения?</legend>
          {(["unknown", "approximate", "exact"] as const).map((value) => (
            <label className="child-choice" key={value}>
              <input
                type="radio"
                name="time-confidence"
                checked={confidence === value}
                onChange={() => setConfidence(value)}
              />
              <span>{timeLabels[value]}</span>
            </label>
          ))}
        </fieldset>
        <p id="child-time-help" className="child-notice">
          {confidence === "unknown"
            ? "Не нужно угадывать время. Мы исключим дома, асцендент и чувствительные ко времени детали. Отчёт всё равно можно подготовить по устойчивым данным и вашим наблюдениям."
            : confidence === "approximate"
              ? "Укажите известное вам приблизительное местное время. Сервер оставит только детали, устойчивые во временном окне; часть выводов будет недоступна."
              : "Укажите местное время рождения из надёжного источника. Оно позволяет учитывать больше деталей, но не делает выводы о ребёнке окончательными."}
        </p>
        {confidence !== "unknown" && (
          <label>
            Время рождения
            <input
              type="time"
              required
              value={time}
              onChange={(e) => setTime(e.target.value)}
              aria-describedby="child-time-help"
            />
          </label>
        )}
        <div className="child-stack">
          <label>
            Место рождения
            <input
              required
              autoComplete="off"
              value={query}
              onChange={(e) => {
                setQuery(e.target.value);
                setPlace(null);
                setSuggestions([]);
              }}
              aria-describedby="child-place-help"
            />
          </label>
          <p id="child-place-help" className="child-muted">
            Выберите населённый пункт из подсказок: координаты и часовой пояс
            сохранятся вместе с ним.
          </p>
          {placeLoading && <p role="status">Ищем место…</p>}
          {!place && suggestions.length > 0 && (
            <ul aria-label="Найденные места">
              {suggestions.map((s) => (
                <li key={`${s.latitude}:${s.longitude}`}>
                  <button
                    className="child-secondary"
                    type="button"
                    onClick={() => {
                      setPlace({
                        label: s.display_name,
                        latitude: s.latitude,
                        longitude: s.longitude,
                        timezone: s.timezone,
                      });
                      setQuery(s.display_name);
                      setSuggestions([]);
                    }}
                  >
                    {s.display_name}
                  </button>
                </li>
              ))}
            </ul>
          )}
          {place && (
            <p className="child-muted">
              Место выбрано: {place.label} · Часовой пояс: {place.timezone}
            </p>
          )}
        </div>
        <fieldset className="child-fieldset child-stack">
          <legend>Ваша роль рядом с ребёнком</legend>
          <label>
            Кем вы приходитесь ребёнку?
            <select
              value={relationship}
              onChange={(e) => setRelationship(e.target.value)}
            >
              <option value="parent">Родитель</option>
              <option value="guardian">Опекун</option>
              <option value="grandparent">Бабушка или дедушка</option>
              <option value="caregiver">Другой близкий взрослый</option>
            </select>
          </label>
          <label className="child-choice">
            <input
              type="checkbox"
              checked={Boolean(context.primary_caregiver)}
              onChange={(e) =>
                setContext({ ...context, primary_caregiver: e.target.checked })
              }
            />
            <span>Я регулярно забочусь о ребёнке</span>
          </label>
          <label>
            Как часто вы общаетесь?
            <select
              value={String(context.daily_contact ?? "high")}
              onChange={(e) =>
                setContext({ ...context, daily_contact: e.target.value })
              }
            >
              <option value="high">Каждый день, много времени вместе</option>
              <option value="medium">Регулярно, но не весь день</option>
              <option value="low">Встречаемся время от времени</option>
            </select>
          </label>
          {(
            [
              ["boundary_role", "Кто чаще договаривается о правилах?"],
              ["soothing_role", "Кто чаще помогает успокоиться?"],
            ] as const
          ).map(([field, label]) => (
            <label key={field}>
              {label}
              <select
                value={String(context[field] ?? "shared")}
                onChange={(e) =>
                  setContext({ ...context, [field]: e.target.value })
                }
              >
                <option value="mostly_me">Чаще я</option>
                <option value="shared">Разделяем эту роль</option>
                <option value="mostly_other">Чаще другой взрослый</option>
              </select>
            </label>
          ))}
        </fieldset>
        <div className="child-actions">
          <button
            type="button"
            className="child-secondary"
            disabled={busy}
            onClick={onCancel}
          >
            Отмена
          </button>
          <button
            className="child-primary"
            disabled={busy || !place || !name.trim()}
          >
            {busy
              ? "Сохраняем…"
              : child
                ? `Сохранить изменения: ${child.display_name}`
                : "Сохранить ребёнка"}
          </button>
        </div>
      </form>
    </section>
  );
}
