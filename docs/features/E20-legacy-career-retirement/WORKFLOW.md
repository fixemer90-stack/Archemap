# E20 Workflow: target Career и legacy compatibility

## Зачем нужен этот документ

Документ разделяет новый E19 Career Report, grandfathered доступ и старые generic reports. Совпадение значения `career` не означает общий payload или общий lifecycle.

## Текущие контуры

### Target E19

Пользователь открывает `/products/career`, проходит questionnaire и создаёт отчёт через `/api/v1/career/*`. Результат открывается на `/products/career/report/{reportId}`. Target storage, sections, versions и PDF не используют `reports.report_data`.

### Grandfathered access

Проверка target E19 допускает:

- активный Plus entitlement `product="self"`;
- активный ранее выданный Career entitlement `product="career"`.

Это access grant, а не указатель на legacy report row. Он должен сохраниться после отключения Career v1.

### Legacy Career v1

Существующие rows хранятся в generic `reports` с `product="career"`. Их обслуживают `/api/v1/reports/{id}`, `/api/v1/reports/{id}/pdf` и старый reader `/report/{profileId}?product=career`. Generic generate endpoint также способен запустить ruleset `career/v1`; именно этот write path должен быть отключён.

## Целевой пользовательский сценарий

1. Пользователь выбирает Career в dashboard/sidebar/CTA.
2. Клиент открывает `/products/career`.
3. Backend проверяет Plus или grandfathered Career entitlement.
4. Новый отчёт всегда создаётся через target E19 API.
5. Новый отчёт открывается только target reader и экспортируется target PDF.
6. Legacy row не используется как fallback и не конвертируется неявно.

## Сценарий исторического отчёта

1. Пользователь открывает сохранённую старую ссылку.
2. Backend проверяет ownership legacy row.
3. Если row существует, возвращается неизменённый persisted payload или PDF.
4. Чтение не запускает chart recompute, ruleset, version increment или regeneration.
5. UI явно обозначает архивный отчёт и предлагает перейти в новый Career flow.
6. Если row отсутствует, UI не создаёт Career v1 и направляет в `/products/career`.

## Запрещённый сценарий

Запрос `POST /api/v1/reports/generate` с `product="career"`:

- не создаёт row;
- не обновляет существующий row;
- не архивирует новую version;
- не запускает `career/v1` rules;
- возвращает стабильный retirement response (`410 Gone`) с machine-readable code и target entrypoint.

## Что не считается миграцией

- сохранение одинакового entitlement literal;
- отображение старого payload новым компонентом без schema mapping;
- принятие legacy report ID target API;
- повторная генерация legacy row новым ruleset;
- удаление row после отсутствия ссылок в текущем UI.

## Removal gate

Compatibility reader/PDF можно предлагать к удалению только когда одновременно подтверждены:

1. production census существующих rows и владельцев;
2. выбранная стратегия: retain, export, explicit migration или deletion;
3. отсутствие compatibility reads в согласованное observation window;
4. отсутствие активных deep links/clients по telemetry;
5. customer-support и legal/data-retention решение;
6. backup/restore rehearsal;
7. отдельное явное одобрение destructive migration.

До этого E20 сохраняет read-only archive и удаляет только возможность создавать новые legacy Career отчёты.
