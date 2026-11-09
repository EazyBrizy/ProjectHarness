# Обязательный опрос при старте проекта

**Документ:** Project Harness  
**Версия:** 0.5.0  
**Дата:** 2026-08-18  
**Статус:** NORMATIVE IMPLEMENTATION SPECIFICATION

## 1. Назначение

Каждый первоначальный `PROJECT_START` для нового Project Instance начинается с короткого управляемого опроса. Опрос помогает собрать Project Definition, выбрать profile, подготовить architecture/technology decisions, skills, routes and prompt infrastructure.

Опрос обязателен и для greenfield, и для brownfield, но содержание адаптируется к исходным документам и repository evidence.

## 2. Первый обязательный вопрос

Первый вопрос всегда относится к документации проекта:

> Есть ли у проекта документация, техническое задание, требования, схемы, ADR, README или другие материалы, которые нужно принять за исходную основу?

Варианты:

```text
1. Да, приложу/укажу документы.
2. Есть частичная или устаревшая документация.
3. Документации нет — опишу проект ответами.
4. Не уверен, что считать документацией — покажу доступные материалы.
```

Harness объясняет, что документы сначала анализируются как sources, а не автоматически объявляются истинными.

## 3. Adaptive questionnaire flow

```text
Start Session
→ Documentation Question
→ Source Inventory and Analysis
→ Project Mode Detection: GREENFIELD / BROWNFIELD / HYBRID
→ Core Question Batch
→ Adaptive Material Questions
→ Answer Reconciliation
→ Project Definition Draft
→ Readiness Summary and Final Confirmation
→ Architecture/Technology/Skills/Bootstrap preparation
```

Вопросы, уже надёжно отвеченные документацией или repository, не задаются повторно. Harness показывает extracted answer и просит подтверждение только если он material или conflicting.

## 4. Question budget

Чтобы опрос не был избыточным:

- первый batch: 3–5 вопросов;
- следующий batch: только material gaps, обычно 3–5;
- целевой общий объём: 7–12 ответов для типового проекта;
- hard upper bound до первой Project Definition Draft: 15 вопросов без отдельного согласия;
- сложный regulated/multi-repo project может продолжить discovery после draft отдельными этапами;
- dependent/conditional вопросы не показываются заранее.

Количество не является целью: достаточно вопросов, закрывающих readiness dimensions.

## 5. Core question groups

Ниже — типовой bank. Harness выбирает только применимые вопросы.

### 5.1. Цель и результат

**Вопрос:** Какую проблему решает проект и какой результат должен получить пользователь?

Варианты помощи:

- «Опишите одним-двумя предложениями»;
- «Пока есть только идея»;
- «Есть конкретный список функций»;
- «Нужно продолжить существующий продукт».

### 5.2. Пользователи и масштаб

**Вопрос:** Кто будет пользоваться системой и примерно сколько пользователей/операций ожидается?

Понятные варианты:

```text
Личный/локальный инструмент
Небольшая команда или до сотен пользователей
Тысячи пользователей
Высокая нагрузка или пока неизвестно
```

Harness поясняет, что точное число не обязательно; диапазон помогает не переусложнить или недооценить архитектуру.

### 5.3. Online/offline

**Вопрос:** Должна ли система работать без интернета?

```text
Только онлайн
Частично офлайн
Offline-first
Не знаю — предложите baseline
```

### 5.4. Платформы и размещение

**Вопрос:** Где система должна работать?

```text
Web browser
Mobile devices
Desktop
CLI/server
On-premise
Cloud
Несколько вариантов
Пока неизвестно
```

### 5.5. Данные и чувствительность

**Вопрос:** Какие данные хранит система и есть ли чувствительные/персональные/секретные данные?

Harness приводит простые примеры и предлагает `нет / да / не знаю` с последующим уточнением только material details.

### 5.6. Интеграции

**Вопрос:** С какими внешними системами, API, файлами, устройствами или базами нужно работать?

Можно ответить списком или «пока нет/не знаю».

### 5.7. Ограничения и обязательный stack

**Вопрос:** Есть ли технологии, платформы, лицензии, сроки или правила, которые обязательно использовать или нельзя использовать?

Для brownfield Harness сначала показывает обнаруженный stack и спрашивает, можно ли его менять.

### 5.8. Критерии успеха

**Вопрос:** Как понять, что первый рабочий результат готов?

Предлагаются варианты:

- конкретный пользовательский сценарий;
- набор функций;
- performance/reliability target;
- demo/prototype;
- release/production readiness;
- «помогите сформулировать».

### 5.9. Команда и эксплуатация

**Вопрос:** Кто будет разрабатывать и поддерживать проект и есть ли предпочтения по сложности эксплуатации?

Задаётся только когда влияет на technology/architecture selection.

### 5.10. Приоритет

**Вопрос:** Что важнее на первом этапе: быстрее получить рабочий минимум, обеспечить масштабирование, строгую безопасность, offline или совместимость с существующей системой?

Пользователь может выбрать несколько приоритетов, Harness выявляет conflicts.

## 6. Questions derived from documentation

После анализа sources Harness создаёт:

```yaml
documentation_findings:
  confirmed_answers: []
  assumptions_to_confirm: []
  conflicts: []
  missing_material_dimensions: []
  adaptive_questions: []
```

Adaptive question создаётся, если:

- разные документы противоречат;
- важное значение отсутствует;
- формулировка неоднозначна;
- решение materially влияет на architecture/stack;
- source authority/revision непонятна;
- существующий code не соответствует docs.

## 7. Questionnaire Session Contract

```yaml
questionnaire_session:
  id: QNS-20260806-001
  intake_session_ref: SES-20260806-0006
  project_mode: GREENFIELD
  profile_candidates: [WEB_APPLICATION, API_SERVICE]

  source_inventory_ref: SIV-20260806-001
  question_budget:
    target: 10
    hard_limit_before_draft: 15
    asked: 4
    answered: 4

  dimensions:
    documentation: CONFIRMED
    purpose: CONFIRMED
    users_and_scale: ASSUMED_WITH_OWNER_AND_REVIEW_TRIGGER
    connectivity: CONFIRMED
    platforms: CONFIRMED
    data_and_security: UNKNOWN_WITH_DECISION_PLAN
    integrations: CONFIRMED
    constraints: CONFIRMED
    success_criteria: CONFIRMED

  open_question_refs: [QST-DATA-001]
  status: QUESTIONING
```

## 8. Answer Contract

```yaml
answer:
  id: ANS-QST-SCALE-001
  question_ref: QST-SCALE-001
  actor_ref: ACT-USER-001
  value: SMALL_TEAM
  free_text: "До 50 сотрудников"
  confidence: MEDIUM
  source_refs: []
  accepted_assumption: true
  review_trigger: "Перед внешним запуском"
  answered_at: 2026-08-06T15:00:00Z
```

Пользователь может исправить ответ; новая revision создаёт impact analysis, если baseline уже принят.

## 9. Понятное представление вопросов

Каждый вопрос содержит:

```text
Вопрос
Почему он важен
Короткие варианты
Рекомендуемый вариант, если есть evidence
Поле «не знаю / предложите вариант»
Пример ответа
```

Пример:

```text
Нужно ли приложению работать без интернета?
Это определит, потребуется ли локальное хранение и синхронизация.
A. Только онлайн — проще и быстрее для первого релиза.
B. Частично офлайн — часть данных доступна без сети.
C. Offline-first — большинство функций работает без сети.
D. Не знаю — используйте online-first как обратимый baseline.
Пример ответа: «A для первого релиза, offline рассмотрим позже».
```

## 10. Readiness summary

После ответов Harness не начинает реализацию молча. Он показывает draft:

- что понял о проекте;
- users and outcomes;
- in/out scope;
- assumptions and unknowns;
- profile candidate;
- material constraints;
- recommended architecture direction;
- decisions, которые нужны позже;
- что будет создано после подтверждения.

Пользователь подтверждает Project Definition Gate или корректирует ответы.

## 11. Автоматическая подготовка после опроса

После accepted Project Definition запускается последовательность:

```text
Requirements and Constraints normalization
→ Architecture options
→ Technology Baseline proposal
→ Material Decision Gate
→ Skill Gap Analysis
→ ACTIVE skill resolution and project configuration
→ Bootstrap Plan
→ Work Packages and causal DAG
→ Context/Verification policies
→ first READY task
→ JIT prompt infrastructure
```

«Подготовка промтов» означает создание reusable specs/modules and task routes; compiled prompts создаются JIT только для READY tasks.

## 12. Greenfield and brownfield differences

| Область | Greenfield | Brownfield |
|---|---|---|
| Documentation | Intent/docs are proposal sources | Docs reconcile with code/tests. |
| Stack | Candidate options | Existing stack inventory first. |
| Architecture | Designed from requirements | Actual architecture extracted and accepted/changed explicitly. |
| Questions | Core bank + source-derived | Conflicts/unknowns + user priorities. |
| Bootstrap | Create handoff skeleton | Build control plane in output handoff without modifying source repository. |
| First routes | Build foundation/features | Continue/improve/fix/stabilize. |

## 13. Ошибки и остановки

- Если пользователь не предоставил документы, опрос продолжается по типовым вопросам.
- Если documents unreadable, Harness объясняет проблему и предлагает другой формат или manual answers.
- Если ответ material conflict, Project Definition Gate остаётся `WAITING_DECISION`.
- Если пользователь не знает ответа, создаётся bounded assumption and review trigger, если безопасно.
- Нельзя бесконечно задавать вопросы до полной определённости; unknowns допускаются с owner and plan.

## 14. Initial-only lifecycle rule

Полный Project Start Questionnaire выполняется при первоначальном создании или подключении нового Project Instance.

При повторном запуске процесса Harness:

```text
reads PROJECT_LOCK
→ restores Session and current state
→ validates active revisions
→ returns exact current route
```

Questionnaire не начинается заново. Targeted questions создаются только при material gap, conflict, stale baseline или Project Evolution. Повторная отправка того же answer bundle является идемпотентной и не создаёт дубликаты Session, Questionnaire или Baseline.

Browser GPT обязан различать отсутствие ответа и уже принятый canonical answer. Он не должен повторять вопрос, на который отвечает normative source или accepted project entity.

## 15. Критерии приёмки

1. Каждый project start создаёт Questionnaire Session.
2. Первый вопрос всегда о документации.
3. Documents анализируются до adaptive questions.
4. Core bank покрывает purpose, users/scale, online/offline, platform, data, integrations, constraints and success.
5. Вопросы понятны, имеют варианты, explanation and `UNKNOWN` path.
6. Typical intake укладывается в 7–12 ответов и не превышает 15 до draft без согласия.
7. Answers создают Project Definition Draft and readiness summary.
8. Product prompts не создаются до Definition/Architecture/Technology readiness.
9. После gate разрешаются ACTIVE skills, routes, Work Packages and first READY task.
10. Brownfield questionnaire использует repository evidence и не повторяет известное.

## 19. v0.4.1 sensitivity rule

Questionnaire может предложить ответ «не знаю», но accepted `PROJECT_INPUT.data.sensitivity` не может оставаться `UNKNOWN`. До выбора `PUBLIC`, `INTERNAL`, `CONFIDENTIAL`, `RESTRICTED`, `SECRET` или `REGULATED` readiness остаётся `WAITING_INPUT`.
