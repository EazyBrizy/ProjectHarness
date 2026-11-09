# Видение продукта и итоговое определение

**Документ:** Project Harness  
**Версия:** 0.5.0  
**Дата:** 2026-08-18  
**Статус:** PROPOSED IMPLEMENTATION BASELINE — готов к реализации после подтверждения

## 1. Проблема

Разработка с ИИ-агентами часто распадается на множество несвязанных prompts. Агент не всегда знает, зачем выполняет шаг, какой contract является текущим, что можно менять, как доказать результат и какой шаг следует дальше. В больших проектах это приводит к преждевременной реализации, конфликтам параллельных изменений, устаревшим tests/docs и потере состояния.

## 2. Цель

Project Harness создаёт один управляемый контур:

```text
user intent and project evidence
→ accepted project model
→ causal tasks and routes
→ bounded agent execution
→ verification and documentation
→ recoverable state and next route
```

## 3. Итоговая формулировка

> Project Harness — project-agnostic, human-governed движок управления разработкой через единую естественно-языковую точку входа. Он анализирует документацию и существующий код, проводит обязательный адаптивный опрос, формирует Project Definition, architecture and Technology Baseline, подготавливает skills, строит причинный DAG Work Packages and atomic tasks, JIT-компилирует prompts для Codex или другого adapter, контролирует permissions and safe parallelism, сохраняет evidence/docs/state и возвращает каждый результат в едином формате со статусом, изменениями, проверками, blockers и точным следующим маршрутом.

## 4. Что означает «единый движок промтинга»

Harness не является коллекцией статических prompts. Он хранит canonical contracts and reusable Prompt IR, а конкретный prompt создаёт только для READY task.

```text
Task Contract + accepted project context + skill + permissions
→ Prompt Plan
→ Compiled Prompt Bundle
```

## 5. Пользовательская ценность

Пользователь в любой момент видит:

- что понял Harness;
- что сейчас делается и зачем;
- к каким требованиям и документам относится task;
- что разрешено менять;
- какой ожидается результат;
- как он будет проверен;
- что уже сделано;
- почему возник blocker;
- какие варианты позволяют продолжить;
- какой следующий шаг рекомендован.

## 6. Критерий успеха

Harness успешен, если из natural-language запроса воспроизводимо создаётся минимальный набор причинно готовых tasks, Codex выполняет одну bounded task, результат независимо проверяется и фиксируется вместе с документацией, а cold start может продолжить работу без знания предыдущего agent session.

Подробная реализация: [`../12_Implementation_Specifications/00_Implementation_Specifications_Index.md`](../12_Implementation_Specifications/00_Implementation_Specifications_Index.md).
