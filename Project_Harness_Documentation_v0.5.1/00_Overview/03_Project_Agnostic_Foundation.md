# Project-agnostic foundation

**Документ:** Project Harness  
**Версия:** 0.5.0  
**Дата:** 2026-08-18  
**Статус:** PROPOSED IMPLEMENTATION BASELINE — готов к реализации после подтверждения

## 1. Базовое правило

Universal kernel не выводится из конкретного проекта, включая ранее существующие проекты пользователя. Project-specific knowledge хранится только в Project Instance, profile extension, project skill, adapter configuration or source evidence.

## 2. Равноправные стартовые режимы

```text
GREENFIELD
BROWNFIELD
HYBRID
```

- `GREENFIELD` начинается с intent/documents and questionnaire.
- `BROWNFIELD` начинается с read-only inventory and reconciliation.
- `HYBRID` связывает перенос существующих assets с новой target architecture.

## 3. Единый Profile Registry

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

Profiles добавляют defaults/checklists/templates, но не утверждают stack и не ослабляют global constraints.

## 4. Запрет скрытых предположений

Profile, prompt or model preference не может автоматически стать project decision. Неизвестность сохраняется как unknown/assumption с owner and review trigger.

## 5. Независимая полнота

Completeness оценивается по dimensions Project Definition, requirements, constraints, architecture, technology, delivery, verification, security, operations and documentation. Наличие исходного документа само по себе не доказывает полноту.

## 6. Расширение домена

Новый domain добавляется versioned profile/extension with schemas, skills, tools and evaluations. Universal IDs/lifecycles/permissions остаются неизменными.

Нормативный registry: [`../12_Implementation_Specifications/18_Registries_Lifecycles_and_Contract_Normalization.md`](../12_Implementation_Specifications/18_Registries_Lifecycles_and_Contract_Normalization.md).
