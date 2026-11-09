# Request routing и skills

**Документ:** Project Harness  
**Версия:** 0.5.0  
**Дата:** 2026-08-18  
**Статус:** PROPOSED IMPLEMENTATION BASELINE — готов к реализации после подтверждения

## 1. Три уровня routing

### Request Class

```text
QUERY
PROJECT_START
DEVELOPMENT_REQUEST
PROJECT_EVOLUTION
PROJECT_CONTROL_MAINTENANCE
HARNESS_DISTRIBUTION_MAINTENANCE
CONTROL_REQUEST
```

### Request Mode

```text
READ_ONLY
PLAN
EXECUTE
```

### Internal Operation

```text
ANSWER, INSPECT_SOURCES, START_INTAKE, ASK_QUESTION_BATCH,
RECONCILE_PROJECT, DEFINE_PROJECT, PROPOSE_ARCHITECTURE,
BUILD_TECHNOLOGY_BASELINE, PREPARE_SKILLS, BOOTSTRAP_PROJECT,
PLAN_WORK, COMPILE_TASK, RUN_TASK, VALIDATE_RESULT,
UPDATE_DOCUMENTATION, RESUME_ROUTE, REPORT_STATUS,
PUBLISH_CHANGE, APPLY_CHANGE_PACK
```

User intent, lifecycle phase and internal operation are never mixed in one enum.

## 2. Request Plan

Every request produces a route DAG with one operation/output per route, gates, dependencies, prohibited operations and expected Result Envelope. `QUERY` normally contains one `ANSWER` route and no task.

## 3. Routing decision before writes

Shows:

- Request Class and Mode;
- objective and project/work package/task;
- requirements/constraints/ADR/docs refs;
- readiness and artifact dependencies;
- in/out/read/write scopes;
- primary skill, Prompt/Context/Verification profile;
- capabilities and side effects;
- expected result and next route.

## 4. Skill policy

```text
REUSE → CONFIGURE → EXTEND → CREATE
```

One-off work remains Task Contract. Every executable task has exactly one primary skill and optional supporting skills.

## 5. Skill lifecycle

```text
DRAFT → VALIDATING → VALIDATED → ACTIVE
ACTIVE → SUSPENDED | DEPRECATED → RETIRED
```

Task cannot become READY with inactive/incompatible primary skill.

## 6. Project-local skills

Project skill lives in `.harness/skills/`, is versioned, evaluated and cannot expand Task permissions. Skill creation is a separate control-plane prerequisite.

## 7. Normative references

- [`../12_Implementation_Specifications/01_Single_Entry_Request_Contract.md`](../12_Implementation_Specifications/01_Single_Entry_Request_Contract.md)
- [`../12_Implementation_Specifications/14_Skill_Registry_and_Lifecycle.md`](../12_Implementation_Specifications/14_Skill_Registry_and_Lifecycle.md)
