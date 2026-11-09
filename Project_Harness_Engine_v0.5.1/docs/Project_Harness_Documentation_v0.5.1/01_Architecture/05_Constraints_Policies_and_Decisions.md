# Ограничения, инварианты, политики и решения

**Документ:** Project Harness  
**Версия:** 0.5.0  
**Дата:** 2026-08-18  
**Статус:** PROPOSED IMPLEMENTATION BASELINE — готов к реализации после подтверждения

## 1. Почему ограничения являются first-class

Свободная фраза «учесть ограничения проекта» недостаточна. Ограничение должно иметь ID, source, scope, силу, статус, precedence, механизм применения и evidence соблюдения.

## 2. Разделение понятий

| Понятие | Вопрос |
|---|---|
| Requirement | Что должно быть создано или обеспечено? |
| Constraint | В каких пределах допустимо решение? |
| Invariant | Что должно оставаться истинным всегда? |
| Policy | Как разрешается действие или выбирается вариант? |
| Preference | Что желательно, но может быть уступлено? |
| Assumption | На каком неподтверждённом основании временно движемся? |
| Decision | Какой материальный вариант принят и кем? |
| Waiver | Какое ограниченное исключение разрешено? |

## 3. Категории constraints

```text
PRODUCT
BUSINESS
SCOPE
TECHNOLOGY
ARCHITECTURE
PLATFORM
DEPLOYMENT
SECURITY
PRIVACY
DATA
LEGAL
LICENSING
INTEGRATION
COMPATIBILITY
PERFORMANCE
RELIABILITY
ACCESSIBILITY
LOCALIZATION
TEAM
TIMELINE
OPERATIONS
```

Количественные resource или timeline limits могут быть обычными project constraints. Harness при этом не моделирует оплату model calls и не ведёт token-expense accounting.

## 4. Scope и наследование

```text
Harness Baseline
  → Organization
    → Project
      → Environment
        → Repository
          → Track
            → Task
              → Run
```

Более локальное правило может ужесточить effective constraint. Ослабление hard constraint разрешается только через допустимый waiver и authority policy.

## 5. Constraint contract

```yaml
constraint:
  id: CST-DATA-001
  statement: "Исходный код нельзя передавать внешним исполнителям"
  category: DATA
  strength: HARD
  epistemic_status: CONFIRMED
  scope:
    project: project-example
    environments: [development, ci]
    repositories: [backend]
  source:
    type: USER_DECISION
    ref: DEC-014
    hash: sha256:...
  status: ACTIVE
  precedence: 900
  enforcement:
    phases: [ARCHITECTURE, COMPILE, ROUTE, PRE_WRITE, RUNTIME, RELEASE]
    evaluator: policy:data-egress-v1
    violation_action: BLOCK
  evidence_required:
    - CHK-DATA-EGRESS
  waiver_policy_ref: PLC-WAIVER-001
```

## 6. Enforcement phases

- **INTAKE:** классификация и выявление конфликтов.
- **ARCHITECTURE:** исключение недопустимых options.
- **PLANNING:** добавление gates, ownership и verification.
- **COMPILE:** включение effective rules в Prompt Plan.
- **ROUTE:** выбор только совместимых adapters/tools.
- **PRE_WRITE:** проверка конкретного scope и capability grant.
- **RUNTIME:** техническое блокирование запрещённого действия.
- **VERIFICATION/RELEASE:** evidence соблюдения.

## 7. Конфликты и precedence

При конфликте kernel сохраняет обе source statements и создаёт conflict object. Нельзя молча выбирать правило по порядку файлов.

Разрешение учитывает:

1. immutable safety baseline;
2. применимую authority и role;
3. explicit accepted decision;
4. scope specificity;
5. precedence;
6. recency только среди равноправных sources.

Обычный conversational request не отменяет ADR или security policy. Для supersession создаётся decision event.

## 8. Waiver

```yaml
waiver:
  id: WVR-003
  target_ref: CST-NET-004
  allowed_by: PLC-WAIVER-001
  scope:
    task: TSK-OPS-018
  reason: "Однократная загрузка проверенного dependency mirror"
  approver:
    role: SECURITY_APPROVER
    actor: user-123
  valid_until: 2026-08-09T00:00:00Z
  compensating_controls: []
  status: ACTIVE
```

Waiver не удаляет constraint и автоматически прекращает действовать по expiry или scope completion.

## 9. Traceability

Каждое материальное решение должно ссылаться на goals, requirements, constraints, alternatives и risks. Task и Run фиксируют effective constraint set и результаты enforcement checks.

## 10. Materiality and ambiguity mode

Project policy declares `STRICT` or `PRAGMATIC` ambiguity handling. Material uncertainty always stops the affected route; non-material reversible details may use a transparent default in `PRAGMATIC` mode. Assumptions require owner and review trigger. Full protocol: [`../12_Implementation_Specifications/09_Ambiguity_and_Clarification_Policy.md`](../12_Implementation_Specifications/09_Ambiguity_and_Clarification_Policy.md).

## 11. ADR boundary

Only material long-lived decisions create ADR/Decision Records. Ordinary implementation, local refactoring, documentation and test maintenance are recorded in Task Contract, Task Report, Evidence and Events. Full policy: [`../12_Implementation_Specifications/06_ADR_and_Decision_Policy.md`](../12_Implementation_Specifications/06_ADR_and_Decision_Policy.md).

## 12. No dead-end policy

A hard constraint can make the original approach impossible, but every blocked result must expose safe routes such as changing approach, scope, dependency, environment, deferral or cancellation. A hard constraint is never silently weakened. See [`../12_Implementation_Specifications/10_Blockers_Recovery_and_Progression.md`](../12_Implementation_Specifications/10_Blockers_Recovery_and_Progression.md).
