# Story E1.S02: Frontend scaffolding: Next.js 15, shadcn/ui, Tailwind 4

**Feature:** [Foundation](FEATURE.md)
**Статус:** ✅ Готово

## Контекст

Создание frontend-скелета: Next.js 15 с App Router, shadcn/ui компоненты, Tailwind CSS 4.

## Что сделать

1. Next.js 15 с App Router
2. shadcn/ui + Tailwind CSS 4
3. Структура: app/(auth)/, app/(dashboard)/, components/, stores/, hooks/
4. Zustand store для auth
5. API client с httpx-style fetch wrapper

## Затрагиваемые файлы

| Файл | Действие |
|---|---|
| `frontend/src/app/layout.tsx` | Создан — root layout |
| `frontend/src/app/page.tsx` | Создан — landing page |
| `frontend/src/stores/auth-store.ts` | Создан — Zustand auth store |
| `frontend/src/hooks/use-auth.ts` | Создан — auth hook |
| `frontend/src/lib/api-client.ts` | Создан — API client |
| `frontend/package.json` | Создан |

## Критерии приёмки

- [x] Next.js 15 App Router
- [x] shadcn/ui компоненты
- [x] Tailwind CSS 4
- [x] Zustand auth store
- [x] API client

## Примечания

Часть начального scaffolding.
