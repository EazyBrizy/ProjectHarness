# PH-051-02 — минимальный Executor Protocol и fake Codex CLI (v0.5.1 WIP)

**Документ:** Project Harness — Executor Protocol PH-051-02.  
**Версия:** 0.5.1-WIP  
**Дата:** 2026-10-25  
**Статус:** IMPLEMENTED PROTOCOL SLICE / **AUTOMATIC EXECUTION NOT RELEASED**.  
**Нормативная база:** `03_Project_Harness_v0.5.1_Local_Executor_and_Sandbox.md` §§4–5, 23.1–23.2.  
**Зависимость:** принятый PH-051-01 (`PROJECT_INPUT@4`, ADP/SBX, schema7).

## Граница пакета

Добавлен **один** `CODEX_CLI_LOCAL` executor adapter как Python-only интерфейс,
без отдельного публичного provider, без новых CLI-команд и без runtime mutation.
В `src/project_harness/executors/` доступны:

```python
from project_harness.executors import ExecutorAdapter, CodexCliLocalAdapter

adapter = CodexCliLocalAdapter()          # production sandbox runner ещё отсутствует
health = adapter.doctor(profile)         # всегда BLOCKED в PH-051-02
argv = adapter.prepare_invocation(run_context)
result = adapter.execute(argv, sandbox_request)
preliminary = adapter.normalize_result(process_result, output_dir)
```

Контракт `ExecutorAdapter`: `doctor(dict) -> dict`, `prepare_invocation(dict) -> list[str]`,
`execute(list[str], dict) -> dict`, `normalize_result(dict, Path) -> dict`.
Это **не** публичные `project-harness executor-doctor` / `execute-current` (их
реализация — PH-051-09). `prepare` с `LOCAL_AUTOMATIC` продолжает fail-closed
`AUTOMATIC_EXECUTOR_NOT_IMPLEMENTED`; рабочий маршрут пока только manual handoff.

## Argv policy и граница доверия

`run_context` содержит `adapter_profile` (активный strict `ADP` профиль
`CODEX_CLI_LOCAL`) и только перечисленные ниже bindings. Для проверки допускается
`agent_adapter_profile` envelope либо уже разобранный профиль.

`argv_template` — **список аргументов**, первый элемент строго равен
`profile.executable` (имя binary либо абсолютный путь *в контейнере*).
Никаких command strings, `shell=True`, pipe/redirect, command substitution,
переменных окружения, `--api-key` literal или относительных binary paths.
Kernel не фиксирует флаги установленной Codex CLI версии.

Ровно шесть полных аргументов-плейсхолдеров:

| Placeholder | Допустимое значение |
|---|---|
| `{prompt_bundle_path}` | `/workspace/control/<file>` — read-only projection |
| `{context_packet_path}` | `/workspace/control/<file>` — read-only projection |
| `{agent_result_path}` | `/output/agent-result.json` — exact destination |
| `{workspace_path}` | `/workspace/product` — disposable worktree |
| `{run_id}` | canonical `RUN-*` (возможно `@revision`) |
| `{task_id}` | canonical `TSK-*` (возможно `@revision`) |

Placeholder должен занимать **целый** элемент списка: `"{prompt_bundle_path}"`
разрешён, `"--prompt={prompt_bundle_path}"` и неизвестные placeholders запрещены.
Запрещены дополнительные `run_context` ключи (raw prompt/user input,
raw secrets, host `env`) и дополнительные поля профиля. Профиль содержит
только `environment_allowlist` имён и `secret_environment_refs` вида `ENV:NAME`;
фактические секреты передавать в этом пакете **некуда**. Незащищённое
совпадение обычного allowlist с secret ref запрещено. Наличие строковых
ссылок **не** гарантирует будущую проверку разрешений/environment.

## Исполнение: только sandbox dispatch

`CodexCliLocalAdapter.execute()` заново получает ожидаемый argv из `run_context`
и запрещает произвольную подмену. В production поставке PH-051-02 доверенный
`ROOTLESS_PODMAN` runner не подключён: вызов возвращает
`{"status":"BLOCKED", "reason_code":"SANDBOX_UNAVAILABLE"}`. Даже если
статическая проверка профиля успешна, `doctor()` сообщает `BLOCKED`, а не
выдаёт фиктивный `PASS` изоляции. Нет fallback через `subprocess`, `os.system`
или host Codex CLI.

Для будущей интеграции предусмотрен **инъецируемый** `SandboxTransport` с
`doctor(profile)`/`run(request)`: dispatch возможен лишь при подтверждении
`backend=ROOTLESS_PODMAN`, `status=PASS`, `isolation_verified=true` от runner.
**Объявленный флаг не является доказательством**: PH-051-03 должен технически
реализовать и проверить OS-границы; настоящий production runner должен
устанавливаться только из доверенного runtime. Stub в unit-тестах исключительно
записывает полученный запрос и не запускает процессы. Tests на stub **не**
подтверждают безопасность Podman.

## Предварительная классификация результата

`normalize_result` оценивает только ограниченный process envelope и начальную
синтаксическую доступность `agent-result.json`. Отказы `EXIT_NONZERO`, `TIMED_OUT`,
`OUTPUT_LIMIT_EXCEEDED`, `RESULT_MISSING`, `RESULT_INVALID`, `SANDBOX_UNAVAILABLE`
и переданные валидные reason codes отображаются детерминированно.
Даже `exit_code=0` вместе с JSON `status=COMPLETED` даёт только
`PENDING_RESULT_VALIDATION`, `result_validated=false`, **никогда PASS**.
Exact ownership/permissions/size/path/schema validation, secret scanning,
normalized ART records и независимая verification относятся к PH-051-06/07;
atomic apply — к PH-051-08. Нельзя использовать этот предварительный результат
для Stage Gate или `complete`.

## Fake CLI scenarios (test double, не второй adapter)

`tests/fixtures/fake_codex_cli.py` — единственный deterministic fake CLI;
`PH_051_02_FAKE_CODEX_CASES.json` описывает 13 сценариев: success, nonzero,
timeout, missing/invalid output, output flood, child process, control write,
wrong paths, secret echo/product/result, baseline drift.
В PH-051-02 fake `success` проверяется **только в том же Python-процессе**;
внешний fake CLI нельзя запускать как автоматический agent на host.
В будущих integration tests его процесс должен запускаться **в rootless Podman**.
Сценарий baseline drift требует изменения canonical дерева **тестовым оркестратором**,
а не агентом. Fake не выполняет security controls: в PH-051-03/06/08 следует
доказать соответствующие блокировки.

## Сохранённые гарантии и отложенное

Никаких изменений в Stage/Gate/maintenance/Brownfield/migration runtime,
`PROJECT_INPUT@4`, schemas/registries или accepted history. Manual workflow
работает без Podman. Не добавлены HTTP providers, Docker/VM, Git/PR, deploy,
network egress и host agent execution. Следующий пакет PH-051-03 обязан
реализовать **настоящий** rootless runner и OS self-tests; до полного PH-051-12
вся v0.5.1 — **WIP / не принят для автоматического исполнения**.
