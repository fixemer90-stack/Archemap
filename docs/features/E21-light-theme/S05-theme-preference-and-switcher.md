# E21.S05: Выбор light/dark/system и инициализация без вспышки

**Feature:** [E21 Цельная светлая тема Astrotype](./FEATURE.md)

**Статус:** ⬜ Не начато

## Контекст

Переключатель был удалён, потому что предлагал пользователю незавершённую тему. Его можно вернуть только после миграции обязательных поверхностей S01–S04.

## Что сделать

1. Снять `forcedTheme="dark"` только после прохождения coverage check.
2. Вернуть режимы `light`, `dark`, `system` через `next-themes`.
3. Обеспечить применение сохранённого/system режима до первого paint без FOUC и hydration mismatch.
4. Разместить control в понятном месте; не использовать один неоднозначный icon-only toggle для трёх режимов.
5. Использовать русские названия: «Светлая», «Тёмная», «Как в системе».
6. Сохранять preference локально; theme preference не является sensitive data.
7. Обеспечить keyboard navigation, accessible name и current-state indication.

## Затрагиваемые файлы

| Файл                                                               | Действие                                                 |
| ------------------------------------------------------------------ | -------------------------------------------------------- |
| `frontend/src/app/layout.tsx`                                      | Убрать временный forced lock после gate                  |
| `frontend/src/providers/theme-provider.tsx`                        | Финализировать provider contract                         |
| `frontend/src/components/layout/header.tsx` или settings component | Добавить понятный selector                               |
| `frontend/src/app/(dashboard)/settings/page.tsx`                   | При необходимости разместить preference control          |
| `frontend/scripts/check-dashboard-shell-ux.mjs`                    | Заменить dark-lock assertions на completeness assertions |
| `frontend/tests/e2e/theme.spec.ts`                                 | Добавить browser behavior tests                          |

## Поведение

| Режим         | Ожидаемое поведение                                         |
| ------------- | ----------------------------------------------------------- |
| Светлая       | Всегда light вне зависимости от OS                          |
| Тёмная        | Всегда dark вне зависимости от OS                           |
| Как в системе | Следует `prefers-color-scheme` и реагирует на его изменение |

## Критерии приёмки

- [ ] Switcher недоступен, если coverage gate не проходит.
- [ ] Три режима имеют явные русские labels и current-state indication.
- [ ] Выбор сохраняется после reload и перехода между маршрутами.
- [ ] System mode следует OS preference.
- [ ] До hydration нет вспышки неверной темы.
- [ ] Нет hydration warnings.
- [ ] Control доступен с клавиатуры и screen reader.
- [ ] Theme change не сбрасывает форму, query state или navigation state.

## Проверка

```bash
cd frontend
npx playwright test tests/e2e/theme.spec.ts
npm test
npx tsc --noEmit --pretty false
npm run build
```
