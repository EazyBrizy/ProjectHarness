# Жизненный цикл проекта и project profiles

**Документ:** Project Harness  
**Версия:** 0.5.0  
**Дата:** 2026-08-18  
**Статус:** PROPOSED IMPLEMENTATION BASELINE — готов к реализации после подтверждения

## 1. Фазы жизненного цикла

| Фаза | Основной результат |
|---|---|
| Session/Request | User input classified and traced. |
| Questionnaire/Inventory | Documents analyzed; greenfield or brownfield facts gathered. |
| Definition | Project Definition accepted. |
| Architecture/Technology | Material options, ADR and Technology Baseline accepted. |
| Skills/Bootstrap | Required skills active; repository/test/docs baseline ready. |
| Planning | Work Packages, artifact DAG, tasks and verification profiles ready. |
| Execution | JIT bundle and governed Run. |
| Integration/Release | Cross-track acceptance and release evidence. |
| Evolution | Product or control-plane Change Packs. |
| Archive | Immutable handoff/export and retained history. |

## 2. Обязательные gates

```text
Documentation/Questionnaire Readiness
Project Definition Gate
Brownfield Baseline Gate (when applicable)
Architecture and Technology Decision Gate
Skill Readiness Gate
Bootstrap Readiness Gate
Task Readiness Gate
Prompt/Context/Capability Gate
Side-effect Approval Gate
Integration/Release Gate
Change Pack Approval Gate
```

## 3. Profile Registry

```text
BASE_SOFTWARE
WEB_APPLICATION
API_SERVICE
MOBILE_APPLICATION
DESKTOP_APPLICATION
CLI_TOOL
LIBRARY
DATA_PIPELINE
ML_SYSTEM
INFRASTRUCTURE
EMBEDDED_SYSTEM
AUTOMATION
MULTI_SERVICE_SYSTEM
CUSTOM
```

Profile выбирается после первичного discovery and remains `PROPOSED` до decision. Допустимы extensions and composition.

## 4. Definition completeness

Для mandatory dimension используется один статус:

```text
CONFIRMED
ASSUMED_WITH_OWNER_AND_REVIEW_TRIGGER
UNKNOWN_WITH_DECISION_PLAN
OUT_OF_SCOPE_BY_DECISION
NOT_APPLICABLE_WITH_RATIONALE
```

Пустое поле не считается обработанным.

## 5. Причинный порядок

Фазы не разрешают implementation task, пока её конкретные prerequisites не готовы. Delivery использует DAG и parallel causal layers, а не один глобальный линейный список.

Подробности: [`../12_Implementation_Specifications/07_Causal_Development_Sequence.md`](../12_Implementation_Specifications/07_Causal_Development_Sequence.md).
