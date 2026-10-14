# S16: Rollout runbook и live evidence

## Статус

⬜ Не начато

## Контекст

Фичу с данными несовершеннолетних нельзя включать только по unit/CI evidence. Нужны точный runbook, stage smoke, canary, rollback и зафиксированные live artifacts.

## Что сделать

1. Подготовить preflight, deploy, feature-flag, smoke, canary и rollback steps.
2. Указать auth/profile/child/report IDs acquisition без публикации PII.
3. Проверить exact и unknown birth time end-to-end.
4. Проверить two-child isolation, locked/foreign access, provider failure и PDF.
5. Зафиксировать deployed SHA, timestamps, metrics, artifact IDs и rollback result.

## Затрагиваемые файлы

| Область                                                               | Действие          |
| --------------------------------------------------------------------- | ----------------- |
| `docs/deployment/child-report-rollout.md`                             | Изменить/добавить |
| `docs/features/E22-child-report/S16-rollout-runbook-live-evidence.md` | Изменить/добавить |
| CI/staging smoke scripts                                              | Изменить/добавить |
| feature flag and observability config                                 | Изменить/добавить |

## Критерии приёмки

- [ ] Runbook исполним новым оператором без скрытых шагов.
- [ ] Staging smoke покрывает все обязательные сценарии.
- [ ] Canary не начинается при safety/access failures.
- [ ] Rollback прекращает generation и сохраняет artifacts.
- [ ] Live evidence содержит exact SHA/IDs/results без child PII.
- [ ] Feature остаётся незакрытой до production/canary evidence по принятой rollout policy.

## Verification

- Добавить targeted unit/integration/frontend tests из критериев Story.
- Запустить repo-native lint/type/test gates только для затронутых областей, затем обязательные более широкие CI gates.
- Записать фактические команды, результаты и runtime evidence в эту Story при реализации.

## Зависимости

См. граф в [`FEATURE.md`](./FEATURE.md). Story не закрывается документацией без code/test/runtime evidence.
