# Основа документации и проектные предположения

**Документ:** Project Harness  
**Версия:** 0.5.0  
**Дата:** 2026-08-18  
**Статус:** PROPOSED IMPLEMENTATION BASELINE — готов к реализации после подтверждения

## 1. Основа версии 0.3

Документация v0.3 сформирована из:

- архитектурной документации Project Harness v0.2;
- полного аудита сквозного user-to-result lifecycle;
- принципов единой естественно-языковой точки входа;
- требования к небольшому числу конкретных task-oriented prompts;
- причинного DAG и безопасной параллельности;
- обязательной фиксации результата, evidence и документационного impact;
- требований к greenfield questionnaire;
- требований к подключению brownfield проекта;
- решения изолировать Harness maintenance от product development;
- решения не учитывать provider billing и фактический token usage.

Ни один конкретный создаваемый проект не используется как методологический baseline. Harness остаётся project-agnostic.

## 2. Сохранённые решения v0.2

Сохранены и развиты:

- repository-resident control plane;
- canonical model and generated artifacts;
- Project Definition и Architecture Decision Gate;
- first-class constraints, policies, waivers and decisions;
- DAG/tasks/ownership;
- Context Planning и cold-start recovery;
- capability enforcement;
- evidence/state/update/Git discipline;
- secure archive/repository intake;
- Change Packs and migrations.

## 3. Новые нормативные решения v0.3

- Request Class, Request Mode и internal Operation разделены;
- введены Request и Request Plan contracts/lifecycles;
- введён единый Result Envelope;
- Request декомпозируется в Work Package и atomic Tasks;
- prompts компилируются JIT только для READY task/run;
- Task содержит exact documentation references and impact;
- ADR создаётся только для material decisions;
- dependencies связываются с produced/required artifacts;
- parallelism использует read/write resource sets;
- material ambiguity останавливает affected task, non-material регулируется policy;
- blocker всегда имеет recovery options and next route;
- Verification Profile заменяет универсальное требование «тест на всё»;
- определена reusable pre-migrated test environment policy;
- Request Trace связывает весь lifecycle;
- введены Technology Baseline и Skill Registry/lifecycle;
- Codex оформлен как executor adapter, а не governance kernel;
- maintenance разделён на PRODUCT, PROJECT_CONTROL и HARNESS_DISTRIBUTION planes;
- создан versioned Profile/ID/Status Registry;
- brownfield onboarding создаёт continuation/fix/improvement/stabilization routes;
- каждый старт проекта начинается с bounded adaptive questionnaire.

## 4. Рабочие assumptions

До pilot implementation предполагается:

- files-first canonical format удобен для первого релиза;
- пользователь или назначенный actor может подтверждать material decisions;
- executor adapters возвращают structured result;
- filesystem/Git/tool operations можно обернуть capability checks;
- repository inventory можно начать read-only;
- project profile extensions имеют namespace and schema;
- SHA-256 достаточен для baseline integrity references;
- локальный single-user deployment допустим как первый walking skeleton;
- semantic documentation validator запускается до release документации и schemas.

Каждый assumption должен быть проверен pilot и может быть изменён через ADR/Change Pack.

## 5. Граница документации

Комплект является implementation-ready specification, но не доказательством готового runtime. YAML examples определяют contract intent; при реализации они должны стать versioned schemas, fixtures и conformance tests.

## 6. Нормативность

При расхождении:

1. machine-readable registry/schema;
2. файл из `12_Implementation_Specifications/`;
3. тематический архитектурный документ;
4. generated aggregate/user guide.

Generated documents пересобираются и не редактируются вручную.
