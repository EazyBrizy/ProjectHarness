# PH-051-06 — Exact Agent Result, bounded logs и ENV secret refs (v0.5.1 WIP)

**Документ:** Project Harness — Exact Result Channel PH-051-06.  
**Версия:** 0.5.1-WIP  
**Дата:** 2026-10-25 (серия v0.5.1 WIP).  
**День реализации:** 2026-10-26.  
**Состояние:** implementation slice; **NOT RELEASED**, `execute-current`/`executor-doctor` **не являются публичными командами** до PH-051-09. Без настоящего PASS от rootless Podman doctor запуск запрещён. Тесты с подменённым runner не являются проверкой OS isolation.

**Нормативная база:** `03_Project_Harness_v0.5.1_Local_Executor_and_Sandbox.md`, §§ 9, 11, 19, 23.1–23.2. Подготовленные PH-051-01–05 contracts/Task/JIT/Podman не изменяют принятый Stage Gate.

## Что делает Kernel

`CodexCliLocalAdapter.from_project(root).prepare_current_run(runtime_root)` привязывает текущие Run/Task/JIT и существующие exact `ADP-…@n` / `SBX-…@n` к disposable product/control/output. `execute(invocation, prepared_request)` при **успешном реальном rootless doctor** создаёт **единственный** файл `<disposable-execution-root>/output/agent-result.json` (mode `0600`, `O_EXCL`, host UID, без symlink). В контейнере он виден **только** как `/output/agent-result.json`. Другие файлы в `/output` не принимаются. Логи Kernel собирает из ограниченных stdout/stderr pipes; agent не выбирает пути сохранения логов.

После process exit `normalize_result(process_result, output_dir)` использует sealed instance/Run binding (не случайный sandbox dict) и:

1. проверяет причину завершения, ненулевой exit/timeout/flood, `backend=ROOTLESS_PODMAN`, действительную attestation и фактические UTC timestamps;
2. проверяет `output` path и все родительские компоненты, exact имя, UID/mode `0600` или `0400`, regular file, `nlink=1`, inode до/после `O_NOFOLLOW`, размер **1 MiB максимум**, UTF-8, JSON без duplicate keys или nonfinite numbers;
3. валидирует прежний строгий контракт `SCHEMA-AGENT-TASK-RESULT@1`, включая обязательные ключи, enum, массивы и **exact active `run_ref`/`task_ref`**; JSON никогда не интерпретируется как shell;
4. проверяет exact secret values в **полном bounded** stdout/stderr, raw agent JSON и разобранных JSON строках; при совпадении `SECRET_LEAK_DETECTED` и **никакой публикации**, даже при `exit_code=0`;
5. сохраняет нормализованный Agent Result под kernel-owned `.harness/runtime/AGENT_RESULTS/<текущий Run>.json`, bounded logs в `.harness/runtime/EXECUTION_LOGS/ART-STDOUT-…/ART-STDERR-….log`, а immutable ART envelope в `.harness/runtime/EXECUTION_RESULTS/ART-EXECUTION-….yaml`; записывает новую authenticated control-plane boundary, но **не изменяет продукт**. Запись с конфликтующим immutable ID запрещена; точный replay идентичных bytes не создаёт дубликатов. Недописанная при crash запись считается конфликтом, а не успехом (quarantine/recovery — PH-051-10).

**Важный контракт совместимости:** текущий v0.5.0 runtime может хранить unrevisioned `RUN-…`, тогда Agent JSON и `AGENT_RESULTS/<RUN>.json` сохраняют **точно его ID**, но новый `execution_result.run_ref` получает ревизионное представление `<RUN>@1` (нормативная `SCHEMA-EXECUTION-RESULT@1`). Принятые historical Runs и immutable input не переписываются. Для новой ревизионной Run ссылки эта нормализация не требуется.

Нормализованный ответ `PENDING_INDEPENDENT_VERIFICATION` означает **только** валидную декларацию Agent Task Result, **не** `SUCCEEDED`/PASS Task, семантический Gate PASS или Stage acceptance. `AGENT_REPORTED_BLOCKED/FAILED` также не равны результату independent verifier. Проверка `SANDBOXED`, product diff/path fence, secret scan фактически changed files, journaled apply и completion принадлежат **PH-051-07–09**, не этому этапу. В `safety.py` имеется read-only `scan_changed_product_secrets()` для следующего diff gate, но он **пока не вызывается перед apply**, поскольку apply ещё не существует.

## Environment и secrets

Профиль ADP содержит **только** имена в `environment_allowlist` и строки `ENV:NAME` в `secret_environment_refs`; literal credentials запрещены и в schema, и в Project Input/Lock. Только эти names разрешаются из host environment; `HOME`, `PATH`, SSH sockets, dynamic-loader переменные и credential-like ordinary allowlist не передаются. Отсутствующий required `ENV:NAME` выдаёт `BLOCKED / SECRET_REFERENCE_MISSING` до запуска. Невалидное/неограниченное значение и CR/LF/NUL блокируются. Передача в Podman — ephemeral mode-`0600` env-file вне проекта/ZIP, путь, но **не значение** в argv, с best-effort erase+unlink в `finally`; автоматической передачи full host environment нет. Rootless runner возвращает только redacted logs, а обнаруженная literal утечка даёт `SECRET_LEAK_DETECTED`. Это **exact-value detection**, а не универсальный DLP для изменённых/закодированных секретов. Raw execution roots, host environments и логи не включаются в handoff exports.

Per-Run `EXPLICIT_APPROVED_EGRESS` всё ещё не активирован, network `NONE`. `PROJECT_CONTROL_WRITE` не предоставлен. Наличие secret refs не обходит doctor и не разрешает host CLI fallback.

## Проверки оператора

Из извлечённого Engine:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:. python -m unittest -v \
  tests.test_ph_051_06_result_channel tests.test_ph_051_05_codex_adapter \
  tests.test_ph_051_04_disposable_roots tests.test_ph_051_03_rootless_podman \
  tests.test_ph_051_02_executor_protocol
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:. python tests/run_tests.py
```

Тесты проверяют invalid/missing/oversize/UTF-8/duplicate JSON, symlink/hardlink/FIFO/UID/mode/undeclared output, secret echo, output flood, inert shell-looking JSON, sealed Run, immutable ART, control-plane digest и отсутствие canonical product mutation. Пробный Podman CLI в unit tests **mocked**: фактическая OS security matrix требует рабочего Linux non-root Podman+pinned image, что остаётся **NOT RUN / NO GO** на данном стенде. PH-051-09 и PH-051-12 позже выполняют настоящие integration/acceptance; здесь не изобретаются новые команды, providers, Git/deployment или remote route.
