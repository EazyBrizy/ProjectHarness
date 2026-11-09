# PH-051-04 — Disposable execution root и bounded control projection (v0.5.1 WIP)

**Версия:** 0.5.1-WIP  
**Дата:** 2026-10-25  
**Статус:** NOT RELEASED  
**Нормативная база:** `03_Project_Harness_v0.5.1_Local_Executor_and_Sandbox.md`, §§ 3, 8, 12, 18; план PH-051-04. Не расширяет scope PH-051-03/05–09.

## Фактически реализованный Python API

`project_harness.execution_roots.prepare_execution_root(project_root, runtime_root, *, run_ref=None)` читает **только текущий persisted active Run**, точный Task/JIT/Run Plan из `.harness`. `runtime_root` — явно заданный **абсолютный** внешний каталог; пути пересекающиеся с canonical project или symlink ancestors запрещены. `run_ref`, если указан, должен строго совпадать с текущим Run. Это bounded Python API следующего компонента; **публичных CLI `execute-current` / `executor-doctor` в PH-051-04 нет**.

```python
from pathlib import Path
from project_harness.execution_roots import prepare_execution_root, check_execution_baseline

prepared = prepare_execution_root(
    Path('/path/to/prepared-project'),
    Path('/var/tmp/project-harness-execution'),
    run_ref='RUN-EXACT-CURRENT-ID',
)
  # prepared: status=PREPARED; idempotent; execution_root/product_dir/control_dir/output_dir
  # check_execution_baseline(project_root, persisted_binding) returns PASS or BASELINE_CHANGED
```

Пример содержит placeholders, а не реальную команду запуска агента. Вызов не резервирует новый Run, не меняет Task status, не запускает Codex/Podman и не применяет diff. Run должен существовать после обычного `next`/JIT. Для `LOCAL_AUTOMATIC` необходимы будущие этапы PH-051-05–09 и реальный Podman doctor PASS.

## Структура и границы

```text
<runtime-root>/<project-id>/executions/<RUN-ID>/
  product/                 # snapshot product plane, отдельные иноды
  control/                 # bounded read-only projection (chmod 0444/0555)
    prompt-bundle.md
    prompt-bundle.yaml
    context-packet.json
    task-contract.yaml
    run-plan.yaml
    permitted-config.json
    agent-task-result.schema.json
  output/                  # пустой, separate result channel для следующих этапов
```

Builder отбрасывает `.harness`, `.git`, generated Harness root views, symlinks и текущие cache exclusions. Special files (FIFO/sockets/device nodes) и hardlinks, которые могут ссылаться на внешние secrets, отклоняет fail-closed; source regular files читаются через `O_NOFOLLOW`/`O_NONBLOCK` и открытие относительно directory file descriptors. Содержимое `product/` — *byte copy*, не hardlink, чтобы агент не мог изменить исходные файлы через shared inode. Сборка требует совпадения canonical product digest до/после, digest скопированных файлов и exact JIT references. Nested control artifacts, которые нарушают соответствие baseline, не копируются и блокируют подготовку.

В `control/` экспортируются **только** семь перечисленных файлов. `permitted-config.json` содержит пять whitelisted полей текущей validated execution policy (`mode`, exact ADP/SBX refs, `network_mode`, `completion_policy`), без host environment, секретов, полноразмерного `.harness` и сторонних исходников. Файлы/каталог имеют read-only mode на host; **техническое принуждение read-only в agent container обеспечивается Podman `control:ro`** из PH-051-03, после успешных OS self-tests. Один `chmod` сам по себе не является изоляционной гарантий.

До записи binding Kernel проверяет existing signed control-plane boundary. Сразу после записи ровно одного metadata file создаётся новая hash-chained фаза `EXECUTION_ROOT_PREPARED` в **существующем** `.harness/runtime/OPERATION_JOURNAL/<RUN-ID>.yaml` с exact `kernel_written_paths`. Это необходимо для штатного `validate-project`. Любые неавторизованные изменения `.harness` до подготовки блокируются и **не подписываются**; replay не добавляет фазу и не изменяет старые records. Journal является control metadata, а не копируется в `control/`.

Project-local `.harness/runtime/EXECUTION_BINDINGS/<RUN-ID>.yaml` содержит только metadata: точные Run/Task/JIT refs, path-independent `execution_ref`, SHA-256 runtime root path, canonical product/control digests, snapshot digest, list/hash whitelist projected files. **Не хранит** writable snapshot bytes, absolute host runtime path, secret values или agent output. Builder повторно сверяет поля с canonical sources, не верит сохранённым digest как истине. `zip_directory()` исключает `EXECUTION_BINDINGS` из export/handoff; runtime root должен быть вне project tree и потому тоже не попадает в экспорт или lock.

## Replay, stale baseline и восстановление

Создание одного Run root эксклюзивно; повторные идентичные вызовы возвращают тот же path и `idempotent=True` без перезаписи контента. Изменённый продукт в canonical repository возвращает `BASELINE_CHANGED` через `check_execution_baseline`; новый apply (в PH-051-08) обязан вызывать этот check непосредственно перед переносом diff. Изменённый disposable snapshot, не пустой output, tampered projection, stale source/ref/metadata, чужой runtime root и наличие orphan root без binding — **блокируют replay**. Builder не очищает произвольный orphan автоматически; post-crash quarantine/cleanup остаётся PH-051-10.

При ошибке в обычном (не crash) создании builder удаляет лишь созданный им root и несостоявшийся binding, а canonical product остаётся byte-identical. Встроенная проверка rootless Podman `validate_execution_mounts` повторно подтверждает disjointness и exact `product/control/output` директории. Только `product` и `output` становятся writable mounts. Отсутствие Podman по-прежнему **NO GO** для реальной container security acceptance; unit tests на snapshot/permissions не подменяют OS integration.

## Что НЕ реализовано этим этапом

Нет Codex CLI invocation, независимой verification, валидации agent result, secret-redaction/logging, diff/write-set gate, atomic canonical apply, automatic CLI runtime/status, миграции/orphan cleanup и дополнительного executor/backend. Manual `next → verify → complete`, Stage Gates/level-up, Brownfield и maintenance не меняются. Подробные реальные test results и ограничения — в `PH_051_04_TEST_REPORT.md` архива Engine.
