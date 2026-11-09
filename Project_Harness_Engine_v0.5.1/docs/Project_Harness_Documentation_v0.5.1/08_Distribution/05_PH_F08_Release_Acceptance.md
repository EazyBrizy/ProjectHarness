# PH‑F08 — финальная интеграционная приёмка v0.5.0

**Документ:** Project Harness  
**Версия:** 0.5.0  
**Дата:** 2026-08-18  
**Проверка релиза:** 2026-10-25  
**Статус:** FINAL INTEGRATION ACCEPTANCE — operational note

## 1. Назначение

PH‑F08 — release gate для уже реализованных v0.5.0 маршрутов. Это не новая функция, уровень зрелости, тип approval или исполнитель Codex. Точная 14-сценарная acceptance matrix I-01–I-14 и действительные логи находятся в Engine ZIP: `PH_F08_ACCEPTANCE_MATRIX.md`, `PH_F08_RELEASE_MATRIX.json`, `PH_F08_TEST_REPORT.md`, `PH_F08_LOGS/`.

## 2. Воспроизводимые команды

Из чисто извлечённого Engine root:

```sh
PYTHONDONTWRITEBYTECODE=1 python tests/run_tests.py
PYTHONPATH=src:. python project-harness.py doctor
python project-harness.py --version
python project-harness.py demo --output-dir /tmp/ph-demo --keep-directory
python project-harness.py validate-handoff --project /tmp/ph-demo/harness-demo-codex-handoff.zip
python project-harness.py validate-project --project /tmp/ph-demo/harness-demo-codex-handoff
python project-harness.py next --project /tmp/ph-demo/harness-demo-codex-handoff
```

В Documentation root:

```sh
python tools/validate_documentation.py . --zip ../Project_Harness_Documentation_v0.5.0.zip
```

Команды установочного smoke и полученные exit codes приведены в `PH_F08_TEST_REPORT.md` движка. Для handoff ZIP требуются фактические принимаемые данным Project Instance входы; `demo` — только проверяемый synthetic fixture. Слово `PASS` от `doctor` либо test runner само по себе не означает приемку реального Stage.

## 3. Исполнимый контур и ограничения

Основной цикл: `intake → explicit approvals → prepare → handoff → next/JIT → external implementation → verify → complete → subject-specific Gate proof → prepare-stage-approval → accept-stage → prepare-active-stage-plan → plan-active-stage → next`. Формальное подтверждение пользователя не выводится из теста, без доказанных нужных результатов Stage Gate остаётся незакрытым. Уровни реализации идут последовательно, только active Stage имеет детализированные Tasks.

Установка не включает автоматический Codex Executor, OS sandbox, Git/PR/deployment или удалённый control plane. Эти механизмы относятся к отдельным версиям, не к PH‑F08.
