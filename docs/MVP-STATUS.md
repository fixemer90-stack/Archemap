# Astrotype — MVP Status

> Когда я смогу вбить дату рождения и получить результат?

**Ответ:** после завершения E4 (Rules) + E5.S01 (Self Report). Сейчас E3 готова — карта считается, но интерпретации нет.

---

## Что сделано и зачем

### E1: Foundation ✅
**Бизнес-смысл:** без инфраструктуры ничего не работает. CI, Docker, миграции — это фундамент для быстрой итерации.

### E2: Identity ✅ (7/9 stories)
**Бизнес-смысл:** пользователь может зарегистрироваться, войти, подтвердить email. Без этого нет доступа к продукту. OAuth (Yandex) позволяет входить без пароля.

### E3: Chart Engine ✅ (6/6 stories)
**Бизнес-смысл:** ядро продукта. По дате/времени/месту рождения вычисляется натальная карта (позиции планет, дома, аспекты) и нормализованный вектор признаков. Это детерминированная, воспроизводимая основа для всех четырёх вертикалей (Self, Love, Child, Career).

**Что уже работает:**
- `POST /profiles` — создать профиль с данными рождения
- `POST /profiles/{id}/chart` — вычислить натальную карту
- `GET /profiles/geocode?q=Москва` — найти координаты места
- Chart engine считает 12 планет, 12 домов, аспекты
- Feature extraction: стихии, модальности, дома, аспекты

**Что НЕ работает (пока):**
- Нет интерпретации — карта есть, но текстового отчёта нет
- Нет frontend-страницы для ввода данных
- Нет PDF-отчёта

### E4: Rules & Content 🟡 (Model A layer готов)
**Бизнес-смысл:** интерпретация карты в текст. Сейчас socionics.py содержит:
- MODEL_A — 16 типов, 8 функций (base/creative/role/pain/suggestive/activation/restrictive/background)
- _model_a_fit() — структурное соответствие Model A (не TYPE_PRIOR)
- Weighted scoring: W_FUNCTION_SCORE=0.68, W_MODEL_A_SCORE=0.22
- Calibration: 4/4 контрольных кейсов в топ-3 (EIE#1, LSI#2, LIE#1, ESI#1)

**Что нужно:**
- YAML-правила для интерпретации (текст, не только scoring)
- Jinja2-шаблоны для отчётов
- Content Resolver (правила → текст)
- Локализация RU/EN

---

## Путь до MVP: "Ввёл дату → увидел результат"

```mermaid
sequenceDiagram
    actor User as Пользователь
    participant S as Система

    User->>S: Регистрация / вход (E2 ✅)
    User->>S: Вводит дату, время, место (E3 ✅)
    Note right of S: Профиль + карта вычислена

    rect rgb(255, 200, 200)
        Note right of S: E4 ⬜ — Rule engine интерпретирует карту
        Note right of S: YAML-правила → текст
    end

    rect rgb(255, 200, 200)
        Note right of S: E5.S01 ⬜ — Рендерит Self-отчёт
        Note right of S: Jinja2 шаблоны → HTML/PDF
    end

    S-->>User: "Вот твой архетипический портрет: Стратег, 78/100"
```

---

## Что нужно для первого кликабельного демо

| # | Что сделать | Зачем | Статус |
|---|-------------|-------|--------|
| 1 | **E9.S01: Auth Screens** | Регистрация с birth data + OAuth | 🟡 В процессе |
| 2 | **E9.S02: Chart Visualization** | Визуализация натальной карты | ✅ Готово |
| 3 | **E9.S03: Socionics Result** | Топ-3 типа, Model A, функциональный профиль | ✅ Готово |
| 4 | **E9.S04: Report Page** | Сборка страницы отчёта | 🟡 В процессе |
| 5 | **E4.S03: Rule engine** | Правила интерпретируют карту в текст | ⬜ Не начато |
| 6 | **E4.S01-02: Rules + Templates** | YAML-правила + Jinja2 шаблоны | ⬜ Не начато |
| 7 | **E5.S01: Self report** | Сборка отчёта из правил + шаблонов | ⬜ Не начато |

**Итого: ~3-4 недели до кликабельного демо (E9 почти готова).**

---

## MVP (полный запуск)

| Эпик | Статус | Что нужно |
|------|--------|-----------|
| E1 Foundation | ✅ | — |
| E2 Identity | ✅ | JWT + OAuth Яндекс |
| E3 Chart Engine | ✅ | — |
| E4 Rules & Content | 🟡 | Model A готов, нужны YAML-правила и шаблоны |
| E5 Self Report | ⬜ | Отчёт, PDF, API |
| E6 Billing | ⬜ | 1 план, 1 PSP (YooKassa) |
| E7 Notifications | ⬜ | Email-уведомления |
| E8 Production | ⬜ | Rate limiting, observability |
| E9 Frontend Self Report | 🟡 | S02/S03 готовы, S01/S04 в процессе |

**MVP-estimate:** 12-16 недель от текущего состояния (ROADMAP.md).

---

## Как проверить прямо сейчас (без frontend)

```bash
# 1. Зарегистрироваться
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password123"}'

# 2. Войти (после верификации email)
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password123"}'

# 3. Найти координаты места
curl "http://localhost:8000/api/v1/profiles/geocode?q=Москва" \
  -H "Authorization: Bearer <token>"

# 4. Создать профиль
curl -X POST http://localhost:8000/api/v1/profiles \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"name":"Тест","birth_date":"1990-05-15","birth_time":"14:30",
       "birth_time_accuracy":"exact","birth_place":"Москва",
       "latitude":55.7558,"longitude":37.6173,"timezone":"Europe/Moscow"}'

# 5. Вычислить карту
curl -X POST http://localhost:8000/api/v1/profiles/<profile_id>/chart \
  -H "Authorization: Bearer <token>"
```

**Результат:** JSON с позициями 12 планет, 12 домов, аспектами. Но без текстовой интерпретации — это следующий шаг (E4).
