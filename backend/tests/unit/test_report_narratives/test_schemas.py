# ruff: noqa: RUF001, E501
"""Unit tests for report narrative schemas."""

from __future__ import annotations

from pydantic import ValidationError

from app.modules.report_narratives.schemas import HouseScenario, NarrativeInput, SelfNarrative


def make_narrative_input_payload() -> dict[str, object]:
    """Create a valid NarrativeInput payload for tests."""
    return {
        "product": "self",
        "language": "ru",
        "profile": {
            "name": "Алексей",
            "birth_date": "1991-08-29",
            "birth_time_quality": "exact",
            "birth_place": "Москва",
        },
        "calculation_quality": {
            "has_exact_birth_time": True,
            "has_known_birth_time": True,
            "quality_label": "Высокая точность времени рождения",
            "warning": None,
        },
        "key_facts": [
            {
                "id": "mercury_venus_jupiter_leo_8",
                "label": "Меркурий, Венера и Юпитер во Льве в 8 доме",
                "meaning": "Выразительное мышление и эмоциональное влияние.",
            },
            {
                "id": "sun_virgo_house_9",
                "label": "Солнце в Деве в 9 доме",
                "meaning": "Сценарий мировоззрения и личного авторитета.",
            },
        ],
        "key_aspects": [
            {
                "id": "moon_trine_mercury",
                "label": "Луна тригон Меркурий",
                "orb": "0°50′",
                "meaning": "Связь эмоций и речи.",
            }
        ],
        "dominants": [
            {
                "id": "dominant_fire",
                "title": "Доминирующая стихия: Огонь",
                "body": "Огонь задаёт способ быстро включаться через инициативу и выразительность.",
                "evidence_ids": ["mercury_venus_jupiter_leo_8"],
            }
        ],
        "inner_mechanism": {
            "title": "Внутренний механизм личности",
            "summary": "Паттерн разворачивается от импульса к выражению и затем к осмыслению реакции среды.",
            "steps": [
                {
                    "id": "mechanism_notice",
                    "title": "Сначала вы считываете эмоциональный фон",
                    "body": "Вы быстро замечаете настроение и скрытый смысл ситуации.",
                    "evidence_ids": ["moon_trine_mercury"],
                },
                {
                    "id": "mechanism_express",
                    "title": "Затем формулируете образно и заразительно",
                    "body": "Смысл становится заметным через речь, интонацию и образ.",
                    "evidence_ids": ["mercury_venus_jupiter_leo_8"],
                },
                {
                    "id": "mechanism_integrate",
                    "title": "После этого ищете форму для переживания",
                    "body": (
                        "Внутреннее напряжение легче выдерживать, когда оно названо и собрано в понятную историю."
                    ),
                    "evidence_ids": ["moon_trine_mercury"],
                },
            ],
        },
        "house_scenarios": [
            {
                "id": "house_scenario_sun_9",
                "title": "Солнце в 9 доме",
                "placement": "Солнце в Деве в 9 доме",
                "need": "Иметь собственную систему смысла, а не набор разрозненных фактов.",
                "manifestation": "Вы ищете методологии, объяснения и язык, который собирает картину мира.",
                "shadow": "Можно застревать в поиске идеальной системы и откладывать действие.",
                "mature_expression": "Зрелая форма — превращать знание в понятную позицию и практический выбор.",
                "evidence_ids": ["sun_virgo_house_9"],
                "evidence_notes": [
                    {
                        "claim": "Поиск смысла и системы — не абстракция, а базовая потребность самовыражения.",
                        "fact_ids": ["sun_virgo_house_9"],
                        "interpretation": "Солнце в 9 доме усиливает потребность опираться на мировоззрение и собранную картину мира.",
                        "limitation": None,
                        "limitation_fact_ids": [],
                    }
                ],
            }
        ],
        "calibration_questions": [
            {
                "id": "calibration_argument_system",
                "question": "Вам легче объяснить свою позицию через систему аргументов, чем через чистую эмоцию?",
                "evidence_ids": ["sun_virgo_house_9", "moon_trine_mercury"],
                "answer_type": "yes_no",
            },
            {
                "id": "calibration_result_value",
                "question": "Бывает ли, что собственную ценность вы измеряете только через результат?",
                "evidence_ids": ["sun_virgo_house_9"],
                "answer_type": "scale_1_5",
            },
            {
                "id": "calibration_structure_vs_feeling",
                "question": "Вы раздражаетесь, когда в ситуации нет структуры, даже если чувства уже требуют отклика?",
                "evidence_ids": ["moon_trine_mercury", "sun_virgo_house_9"],
                "answer_type": "yes_no",
            },
            {
                "id": "calibration_big_idea",
                "question": "Для вас важно понимать большую идею за задачей, а не только саму задачу?",
                "evidence_ids": ["sun_virgo_house_9"],
                "answer_type": "yes_no",
            },
            {
                "id": "calibration_enough",
                "question": "Знакомо ли вам чувство: «я сделал много, но всё равно недостаточно»?",
                "evidence_ids": ["sun_virgo_house_9", "moon_trine_mercury"],
                "answer_type": "scale_1_5",
            },
        ],
        "contradictions": [
            {
                "id": "contradiction_structure_vs_expression",
                "title": "Структура против выразительности",
                "tension": "Одна часть вас хочет собрать всё в точную систему, а другая — быстро выразить переживание и захватить внимание.",
                "manifestation": "Из-за этого вы можете метаться между точной настройкой формулировки и желанием сказать главное сразу.",
                "mature_expression": "Зрелая форма — сначала находить смысловой каркас, а потом уже усиливать его выразительностью.",
                "evidence_ids": ["sun_virgo_house_9", "moon_trine_mercury"],
                "evidence_notes": [
                    {
                        "claim": "Ось противоречия строится между потребностью в точной системе и живой эмоциональной передачей.",
                        "fact_ids": ["sun_virgo_house_9", "moon_trine_mercury"],
                        "interpretation": "Дева/9 дом тянет к смысловому каркасу, а связка Луны с Меркурием ускоряет эмоциональную подачу.",
                        "limitation": None,
                        "limitation_fact_ids": [],
                    }
                ],
            },
            {
                "id": "contradiction_intensity_vs_clarity",
                "title": "Интенсивность против ясности",
                "tension": "Глубина эмоционального включения повышает ставку переживания, но одновременно может осложнять ясную сборку мысли.",
                "manifestation": "В напряжении сложно понять, что сейчас важнее: прожить чувство или сразу оформить его в понятный смысл.",
                "mature_expression": "Зрелая форма — не обесценивать чувство, но и не позволять ему полностью задавать всю интерпретацию происходящего.",
                "evidence_ids": ["mercury_venus_jupiter_leo_8", "moon_trine_mercury"],
            },
            {
                "id": "contradiction_recognition_vs_patience",
                "title": "Признание против терпения",
                "tension": "Есть потребность быть замеченным за силу идеи, но путь к этому часто требует долгой внутренней настройки и терпения.",
                "manifestation": "Можно раздражаться, когда результат ещё не оформлен так, чтобы его уже можно было уверенно предъявить миру.",
                "mature_expression": "Зрелая форма — выдерживать этап созревания идеи без ощущения, что ценность исчезает до внешнего признания.",
                "evidence_ids": ["sun_virgo_house_9", "mercury_venus_jupiter_leo_8"],
            },
        ],
        "failure_modes": [
            {
                "id": "failure_analysis_overload",
                "title": "Перегрузка анализом",
                "trigger": "Когда слишком многое нужно одновременно понять, объяснить и удержать в хорошем качестве.",
                "manifestation": "Вместо движения возникает цикл уточнений, перепроверки формулировок и внутреннего давления на результат.",
                "supportive_reframe": "Полезно временно снизить планку идеальности и сначала выбрать следующий ясный шаг.",
                "evidence_ids": ["sun_virgo_house_9", "moon_trine_mercury"],
                "evidence_notes": [
                    {
                        "claim": "Сбой запускается там, где потребность всё собрать правильно оказывается сильнее, чем готовность двигаться с неполной ясностью.",
                        "fact_ids": ["sun_virgo_house_9", "moon_trine_mercury"],
                        "interpretation": "Дева усиливает фильтр качества, а аспект Луны/Меркурия добавляет внутренний шум при перегрузке.",
                        "limitation": None,
                        "limitation_fact_ids": [],
                    }
                ],
            },
            {
                "id": "failure_delayed_action",
                "title": "Отложенное действие",
                "trigger": "Когда ещё не найдено ощущение правильной системы или полной смысловой рамки.",
                "manifestation": "Действие переносится вперёд, хотя внутренне решение уже почти созрело.",
                "supportive_reframe": "Иногда опорой становится не идеальная схема, а первый ограниченный эксперимент.",
                "evidence_ids": ["sun_virgo_house_9"],
            },
            {
                "id": "failure_emotional_freeze",
                "title": "Эмоциональная самозаморозка",
                "trigger": "Когда интенсивность переживания кажется слишком большой для прямого контакта или немедленного ответа.",
                "manifestation": "Снаружи это может выглядеть как пауза, уход в контроль или задержка с ясным откликом.",
                "supportive_reframe": "Сначала назвать переживание для себя, а потом возвращаться в разговор уже из большей собранности.",
                "evidence_ids": ["mercury_venus_jupiter_leo_8", "moon_trine_mercury"],
            },
        ],
        "maturity_levels": {
            "low": {
                "title": "Низкий уровень проявления",
                "body": "Перфекционизм, тревога за результат и зависимость от внешнего подтверждения могут делать движение рваным и истощающим.",
                "evidence_ids": ["sun_virgo_house_9", "moon_trine_mercury"],
            },
            "medium": {
                "title": "Средний уровень проявления",
                "body": "Появляется способность собирать устойчивые процессы, объяснять сложное и сохранять рабочую форму даже в эмоционально насыщённых темах.",
                "evidence_ids": ["sun_virgo_house_9", "mercury_venus_jupiter_leo_8"],
            },
            "high": {
                "title": "Высокий уровень проявления",
                "body": "Сильная сторона превращается в собственную методологию: вы не просто чувствуете и понимаете, а умеете передавать смысл другим и держать зрелую устойчивость.",
                "evidence_ids": ["sun_virgo_house_9", "mercury_venus_jupiter_leo_8", "moon_trine_mercury"],
                "evidence_notes": [
                    {
                        "claim": "На высоком уровне паттерн становится передаваемой системой, а не только личной особенностью.",
                        "fact_ids": ["sun_virgo_house_9", "mercury_venus_jupiter_leo_8", "moon_trine_mercury"],
                        "interpretation": "Смысл, выразительность и эмоциональная точность начинают работать как целостная методология.",
                        "limitation": None,
                        "limitation_fact_ids": [],
                    }
                ],
            },
        },
        "socionics": {
            "type": "EIE",
            "type_ru": "ЭИЭ",
            "confidence_label": "средняя",
            "explanation": "Этико-интуитивная выразительность.",
        },
        "archetype": {
            "primary": "Наставник",
            "confidence_label": "высокая",
            "explanation": "Склонность собирать людей вокруг смысла.",
        },
        "strengths": [
            {
                "id": "strength_expression",
                "claim": "Вы умеете заражать идеей.",
                "evidence_ids": ["mercury_venus_jupiter_leo_8", "moon_trine_mercury"],
            }
        ],
        "risks": [
            {
                "id": "risk_overload",
                "claim": "Иногда эмоции перегружают речь.",
                "evidence_ids": ["moon_trine_mercury"],
            }
        ],
        "relationship_patterns": [
            {
                "id": "relationships_depth",
                "claim": "Вам важна эмоциональная интенсивность и глубина доверия.",
                "evidence_ids": ["mercury_venus_jupiter_leo_8"],
            }
        ],
        "sexuality_patterns": [
            {
                "id": "sexuality_intensity",
                "claim": "Близость раскрывается через доверие и внутреннюю вовлечённость.",
                "evidence_ids": ["mercury_venus_jupiter_leo_8"],
            }
        ],
        "development_recommendations": [
            {
                "id": "development_grounding",
                "claim": "Полезно давать себе паузу перед эмоционально важным разговором.",
                "evidence_ids": ["moon_trine_mercury"],
            }
        ],
        "product_boundaries": {
            "career_policy": "В Self-отчёте карьеру затрагивать кратко и завершать CTA на Career.",
            "allowed_sections": [
                "main_formula",
                "world_perception",
                "emotions_and_communication",
                "strengths",
                "vulnerabilities",
                "relationships",
                "sexuality",
                "development",
            ],
        },
    }


def make_self_narrative_payload() -> dict[str, object]:
    """Create a valid SelfNarrative payload for tests."""
    return {
        "title": "Ваш внутренний портрет",
        "hero": {
            "id": "hero",
            "title": "Главное о вас",
            "body": (
                "Вы производите впечатление человека, который соединяет эмоциональную глубину и выразительное мышление."
            ),
            "bullets": [
                "Умеете передавать настроение через слова.",
                "Чувствуете скрытый эмоциональный фон ситуации.",
            ],
            "evidence_notes": [
                {
                    "claim": "Эмоции и речь работают в связке.",
                    "fact_ids": ["moon_trine_mercury"],
                    "interpretation": "Тригон показывает, что эмоции и речь легче соединяются в связное объяснение.",
                    "limitation": "Это не отменяет перегрузку речи в напряжённых ситуациях.",
                    "limitation_fact_ids": ["moon_trine_mercury"],
                }
            ],
        },
        "dominants": [
            {
                "id": "dominant_fire",
                "title": "Доминирующая стихия: Огонь",
                "body": "Огонь задаёт способ быстро включаться через инициативу и выразительность.",
                "evidence_ids": ["mercury_venus_jupiter_leo_8"],
            }
        ],
        "inner_mechanism": {
            "title": "Внутренний механизм личности",
            "summary": "Паттерн разворачивается от импульса к выражению и затем к осмыслению реакции среды.",
            "steps": [
                {
                    "id": "mechanism_notice",
                    "title": "Сначала вы считываете эмоциональный фон",
                    "body": "Вы быстро замечаете настроение и скрытый смысл ситуации.",
                    "evidence_ids": ["moon_trine_mercury"],
                },
                {
                    "id": "mechanism_express",
                    "title": "Затем формулируете образно и заразительно",
                    "body": "Смысл становится заметным через речь, интонацию и образ.",
                    "evidence_ids": ["mercury_venus_jupiter_leo_8"],
                },
                {
                    "id": "mechanism_integrate",
                    "title": "После этого ищете форму для переживания",
                    "body": (
                        "Внутреннее напряжение легче выдерживать, когда оно названо и собрано в понятную историю."
                    ),
                    "evidence_ids": ["moon_trine_mercury"],
                },
            ],
        },
        "house_scenarios": [
            {
                "id": "house_scenario_sun_9",
                "title": "Солнце в 9 доме",
                "placement": "Солнце в Деве в 9 доме",
                "need": "Иметь собственную систему смысла, а не набор разрозненных фактов.",
                "manifestation": "Вы ищете методологии, объяснения и язык, который собирает картину мира.",
                "shadow": "Можно застревать в поиске идеальной системы и откладывать действие.",
                "mature_expression": "Зрелая форма — превращать знание в понятную позицию и практический выбор.",
                "evidence_ids": ["sun_virgo_house_9"],
                "evidence_notes": [
                    {
                        "claim": "Поиск смысла и системы — не абстракция, а базовая потребность самовыражения.",
                        "fact_ids": ["sun_virgo_house_9"],
                        "interpretation": "Солнце в 9 доме усиливает потребность опираться на мировоззрение и собранную картину мира.",
                        "limitation": None,
                        "limitation_fact_ids": [],
                    }
                ],
            }
        ],
        "calibration_questions": [
            {
                "id": "calibration_argument_system",
                "question": "Вам легче объяснить свою позицию через систему аргументов, чем через чистую эмоцию?",
                "evidence_ids": ["sun_virgo_house_9", "moon_trine_mercury"],
                "answer_type": "yes_no",
            },
            {
                "id": "calibration_result_value",
                "question": "Бывает ли, что собственную ценность вы измеряете только через результат?",
                "evidence_ids": ["sun_virgo_house_9"],
                "answer_type": "scale_1_5",
            },
            {
                "id": "calibration_structure_vs_feeling",
                "question": "Вы раздражаетесь, когда в ситуации нет структуры, даже если чувства уже требуют отклика?",
                "evidence_ids": ["moon_trine_mercury", "sun_virgo_house_9"],
                "answer_type": "yes_no",
            },
            {
                "id": "calibration_big_idea",
                "question": "Для вас важно понимать большую идею за задачей, а не только саму задачу?",
                "evidence_ids": ["sun_virgo_house_9"],
                "answer_type": "yes_no",
            },
            {
                "id": "calibration_enough",
                "question": "Знакомо ли вам чувство: «я сделал много, но всё равно недостаточно»?",
                "evidence_ids": ["sun_virgo_house_9", "moon_trine_mercury"],
                "answer_type": "scale_1_5",
            },
        ],
        "contradictions": [
            {
                "id": "contradiction_structure_vs_expression",
                "title": "Структура против выразительности",
                "tension": "Одна часть вас хочет собрать всё в точную систему, а другая — быстро выразить переживание и захватить внимание.",
                "manifestation": "Из-за этого вы можете метаться между точной настройкой формулировки и желанием сказать главное сразу.",
                "mature_expression": "Зрелая форма — сначала находить смысловой каркас, а потом уже усиливать его выразительностью.",
                "evidence_ids": ["sun_virgo_house_9", "moon_trine_mercury"],
                "evidence_notes": [
                    {
                        "claim": "Ось противоречия строится между потребностью в точной системе и живой эмоциональной передачей.",
                        "fact_ids": ["sun_virgo_house_9", "moon_trine_mercury"],
                        "interpretation": "Дева/9 дом тянет к смысловому каркасу, а связка Луны с Меркурием ускоряет эмоциональную подачу.",
                        "limitation": None,
                        "limitation_fact_ids": [],
                    }
                ],
            },
            {
                "id": "contradiction_intensity_vs_clarity",
                "title": "Интенсивность против ясности",
                "tension": "Глубина эмоционального включения повышает ставку переживания, но одновременно может осложнять ясную сборку мысли.",
                "manifestation": "В напряжении сложно понять, что сейчас важнее: прожить чувство или сразу оформить его в понятный смысл.",
                "mature_expression": "Зрелая форма — не обесценивать чувство, но и не позволять ему полностью задавать всю интерпретацию происходящего.",
                "evidence_ids": ["mercury_venus_jupiter_leo_8", "moon_trine_mercury"],
            },
            {
                "id": "contradiction_recognition_vs_patience",
                "title": "Признание против терпения",
                "tension": "Есть потребность быть замеченным за силу идеи, но путь к этому часто требует долгой внутренней настройки и терпения.",
                "manifestation": "Можно раздражаться, когда результат ещё не оформлен так, чтобы его уже можно было уверенно предъявить миру.",
                "mature_expression": "Зрелая форма — выдерживать этап созревания идеи без ощущения, что ценность исчезает до внешнего признания.",
                "evidence_ids": ["sun_virgo_house_9", "mercury_venus_jupiter_leo_8"],
            },
        ],
        "failure_modes": [
            {
                "id": "failure_analysis_overload",
                "title": "Перегрузка анализом",
                "trigger": "Когда слишком многое нужно одновременно понять, объяснить и удержать в хорошем качестве.",
                "manifestation": "Вместо движения возникает цикл уточнений, перепроверки формулировок и внутреннего давления на результат.",
                "supportive_reframe": "Полезно временно снизить планку идеальности и сначала выбрать следующий ясный шаг.",
                "evidence_ids": ["sun_virgo_house_9", "moon_trine_mercury"],
                "evidence_notes": [
                    {
                        "claim": "Сбой запускается там, где потребность всё собрать правильно оказывается сильнее, чем готовность двигаться с неполной ясностью.",
                        "fact_ids": ["sun_virgo_house_9", "moon_trine_mercury"],
                        "interpretation": "Дева усиливает фильтр качества, а аспект Луны/Меркурия добавляет внутренний шум при перегрузке.",
                        "limitation": None,
                        "limitation_fact_ids": [],
                    }
                ],
            },
            {
                "id": "failure_delayed_action",
                "title": "Отложенное действие",
                "trigger": "Когда ещё не найдено ощущение правильной системы или полной смысловой рамки.",
                "manifestation": "Действие переносится вперёд, хотя внутренне решение уже почти созрело.",
                "supportive_reframe": "Иногда опорой становится не идеальная схема, а первый ограниченный эксперимент.",
                "evidence_ids": ["sun_virgo_house_9"],
            },
            {
                "id": "failure_emotional_freeze",
                "title": "Эмоциональная самозаморозка",
                "trigger": "Когда интенсивность переживания кажется слишком большой для прямого контакта или немедленного ответа.",
                "manifestation": "Снаружи это может выглядеть как пауза, уход в контроль или задержка с ясным откликом.",
                "supportive_reframe": "Сначала назвать переживание для себя, а потом возвращаться в разговор уже из большей собранности.",
                "evidence_ids": ["mercury_venus_jupiter_leo_8", "moon_trine_mercury"],
            },
        ],
        "maturity_levels": {
            "low": {
                "title": "Низкий уровень проявления",
                "body": "Перфекционизм, тревога за результат и зависимость от внешнего подтверждения могут делать движение рваным и истощающим.",
                "evidence_ids": ["sun_virgo_house_9", "moon_trine_mercury"],
            },
            "medium": {
                "title": "Средний уровень проявления",
                "body": "Появляется способность собирать устойчивые процессы, объяснять сложное и сохранять рабочую форму даже в эмоционально насыщённых темах.",
                "evidence_ids": ["sun_virgo_house_9", "mercury_venus_jupiter_leo_8"],
            },
            "high": {
                "title": "Высокий уровень проявления",
                "body": "Сильная сторона превращается в собственную методологию: вы не просто чувствуете и понимаете, а умеете передавать смысл другим и держать зрелую устойчивость.",
                "evidence_ids": ["sun_virgo_house_9", "mercury_venus_jupiter_leo_8", "moon_trine_mercury"],
                "evidence_notes": [
                    {
                        "claim": "На высоком уровне паттерн становится передаваемой системой, а не только личной особенностью.",
                        "fact_ids": ["sun_virgo_house_9", "mercury_venus_jupiter_leo_8", "moon_trine_mercury"],
                        "interpretation": "Смысл, выразительность и эмоциональная точность начинают работать как целостная методология.",
                        "limitation": None,
                        "limitation_fact_ids": [],
                    }
                ],
            },
        },
        "sections": [
            {
                "id": "main_formula",
                "title": "Главная формула личности",
                "body": "Вы раскрываетесь через сильное эмоциональное присутствие и образное мышление.",
                "bullets": ["Видите подтекст.", "Умеете влиять через интонацию и формулировку."],
                "evidence_notes": [
                    {
                        "claim": "Выразительное мышление связано с эмоциональной интенсивностью.",
                        "fact_ids": ["mercury_venus_jupiter_leo_8", "moon_trine_mercury"],
                    }
                ],
            },
            {
                "id": "world_perception",
                "title": "Как вы воспринимаете мир",
                "body": "Вы быстро замечаете настроение, смысл и скрытые мотивы происходящего.",
                "bullets": [],
                "evidence_notes": [],
            },
        ],
        "career_cta": {
            "title": "Отдельный отчёт Career",
            "body": (
                "Если захотите глубже разобрать работу и профессиональную роль, "
                "это лучше вынести в отдельный Career-отчёт."
            ),
            "bullets": ["Профроли", "среда", "стратегия роста"],
            "button_label": "Открыть Career",
        },
        "final_summary": "Ваш сильный эффект рождается там, где чувства, речь и смысл собираются в одно целое.",
    }


class TestNarrativeInputSchema:
    """Validate NarrativeInput contract."""

    def test_accepts_self_payload(self) -> None:
        payload = make_narrative_input_payload()

        result = NarrativeInput.model_validate(payload)

        assert result.product == "self"
        assert result.language == "ru"
        assert result.profile.name == "Алексей"
        assert result.product_boundaries.allowed_sections[0] == "main_formula"
        assert result.strengths[0].evidence_ids == ["mercury_venus_jupiter_leo_8", "moon_trine_mercury"]
        assert result.dominants[0].evidence_ids == ["mercury_venus_jupiter_leo_8"]
        assert len(result.inner_mechanism.steps) == 3
        assert result.house_scenarios[0].manifestation.startswith("Вы ищете методологии")
        assert result.house_scenarios[0].evidence_notes[0].fact_ids == ["sun_virgo_house_9"]
        assert len(result.calibration_questions) == 5
        assert len(result.contradictions) == 3
        assert len(result.failure_modes) == 3
        assert result.maturity_levels.high.title == "Высокий уровень проявления"

    def test_rejects_unsupported_product(self) -> None:
        payload = make_narrative_input_payload()
        payload["product"] = "friendship"

        try:
            NarrativeInput.model_validate(payload)
        except ValidationError as exc:
            assert "product" in str(exc)
        else:
            raise AssertionError("NarrativeInput unexpectedly accepted unsupported product")


class TestSelfNarrativeSchema:
    """Validate SelfNarrative contract."""

    def test_accepts_structured_narrative(self) -> None:
        payload = make_self_narrative_payload()

        result = SelfNarrative.model_validate(payload)

        assert result.title == "Ваш внутренний портрет"
        assert result.hero.id == "hero"
        assert result.sections[0].id == "main_formula"
        assert result.sections[1].id == "world_perception"
        assert result.sections[0].evidence_notes[0].fact_ids == [
            "mercury_venus_jupiter_leo_8",
            "moon_trine_mercury",
        ]
        interpretation = result.hero.evidence_notes[0].interpretation
        assert interpretation is not None
        assert interpretation.startswith("Тригон показывает")
        assert result.hero.evidence_notes[0].limitation_fact_ids == ["moon_trine_mercury"]
        assert result.dominants[0].title == "Доминирующая стихия: Огонь"
        assert result.inner_mechanism.steps[0].id == "mechanism_notice"
        assert result.calibration_questions[0].answer_type == "yes_no"
        assert result.contradictions[0].id == "contradiction_structure_vs_expression"
        assert result.contradictions[0].evidence_notes[0].fact_ids == ["sun_virgo_house_9", "moon_trine_mercury"]
        assert result.failure_modes[0].id == "failure_analysis_overload"
        assert result.failure_modes[0].evidence_notes[0].fact_ids == ["sun_virgo_house_9", "moon_trine_mercury"]
        assert result.maturity_levels.low.title == "Низкий уровень проявления"
        assert result.maturity_levels.high.evidence_notes[0].fact_ids == [
            "sun_virgo_house_9",
            "mercury_venus_jupiter_leo_8",
            "moon_trine_mercury",
        ]

    def test_requires_inner_mechanism_with_three_to_five_steps(self) -> None:
        payload = make_self_narrative_payload()
        payload["inner_mechanism"]["steps"] = payload["inner_mechanism"]["steps"][:2]  # type: ignore[index]

        try:
            SelfNarrative.model_validate(payload)
        except ValidationError as exc:
            assert "inner_mechanism.steps" in str(exc)
        else:
            raise AssertionError("SelfNarrative unexpectedly accepted too-short inner_mechanism")

    def test_house_scenario_requires_manifestation_shadow_and_evidence(self) -> None:
        try:
            HouseScenario.model_validate(
                {
                    "id": "house_scenario_sun_9",
                    "title": "Солнце в 9 доме",
                    "placement": "Солнце в Деве в 9 доме",
                    "need": "Иметь мировоззрение.",
                    "manifestation": "Вы ищете систему объяснения.",
                    "shadow": "Можно откладывать действие.",
                    "mature_expression": "Зрелая форма — применять знание.",
                    "evidence_ids": [],
                }
            )
        except ValidationError as exc:
            assert "evidence_ids" in str(exc)
        else:
            raise AssertionError("HouseScenario unexpectedly accepted missing evidence ids")

    def test_rejects_unknown_section_id(self) -> None:
        payload = make_self_narrative_payload()
        payload["sections"][0]["id"] = "career_strategy"  # type: ignore[index]

        try:
            SelfNarrative.model_validate(payload)
        except ValidationError as exc:
            assert "sections.0.id" in str(exc) or "section" in str(exc)
        else:
            raise AssertionError("SelfNarrative unexpectedly accepted unknown section id")

    def test_career_cta_is_optional_for_self_narrative(self) -> None:
        payload = make_self_narrative_payload()
        payload.pop("career_cta")

        narrative = SelfNarrative.model_validate(payload)

        assert narrative.career_cta is None
