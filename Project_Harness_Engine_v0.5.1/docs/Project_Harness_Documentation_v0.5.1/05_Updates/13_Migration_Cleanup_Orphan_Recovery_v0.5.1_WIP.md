# PH-051-10 — Migration, завершение Run, очистка и восстановление v0.5.1 WIP

**Версия:** 0.5.1-WIP. **Дата:** 2026-10-25. **Дата реализации:** 2026-10-26.

**Статус:** реализованный ограниченный пакет; **v0.5.1 WIP / NOT RELEASED**.
Нормативная база: `03_Project_Harness_v0.5.1_Local_Executor_and_Sandbox.md`, §§17, 19.1, 21–22. Фактическая sandbox isolation на рабочем стенде не аттестована (rootless Podman отсутствует).

## 1. Миграция существующего v0.5.0 Project Instance

Выполняется существующей публичной операцией:

```bash
project-harness migrate-project --project /absolute/path/to/extracted-project
project-harness validate-project --project /absolute/path/to/extracted-project
project-harness next --project /absolute/path/to/extracted-project
```

Python API: `project_harness.migration.migrate_project(Path(project_root))`. Только совместимый v0.5.0 engine/schema `0.5.0/6`, полностью валидный Project Instance; при передаче `--input` для этого маршрута миграция отклоняется: immutable accepted input менять нельзя. Старый v0.4.1→v0.5.0 маршрут сохраняется отдельно. Первый вызов возвращает `MIGRATED`; повтор для точно мигрированного root — `NO_ACTION`. Недействительный legacy lock/registry digest, symlink journal, конфликт storage или чужая версия блокируют операцию до mutation.

Migration `MIG-ENGINE-0.5.0-TO-0.5.1` добавляет только safe default:

```yaml
execution:
  mode: MANUAL_HANDOFF
  adapter_profile_ref: null
  sandbox_profile_ref: null
  network_mode: NONE
  completion_policy: EXPLICIT_AFTER_VERIFICATION
```

Новое состояние PROJECT_LOCK: schema7, exact текущие registry версии/digests, `execution_profile_bindings` с `adapter/sandbox: {ref: null, digest: null}`, migration ID и отчёт `.harness/reports/MIG-ENGINE-0.5.0-TO-0.5.1.yaml`. Копируется текущий distribution runtime. **Не меняются байты** `.harness/state/PROJECT_INPUT_ACCEPTED.yaml`, исторических `.harness/runtime/RUNS/*.yaml`, Stage Acceptance Reports/Plans/Gates, accepted Stage State, canonical target, product tree. Открытый manual Run после обновления поддерживает свою подписанную control-plane границу, но не считается новым Run.

Migration использует проверенный sibling snapshot, durable marker `.<project-name>.ph05110-migration.json`, fsync и rename/swap. До установки полного нового root crash восстанавливает старый; после установки валидного нового root сохраняет новый. Повтор команды выполняет recovery прежде новой migration. Если journal или состояние root неоднозначны, операция **останавливается без оптимистичного commit**; удаление/ручная подмена journal запрещены.

## 2. Происхождение Run и остановка процессов

Новые завершённые/заблокированные Run records сохраняют `execution_origin: MANUAL_EXTERNAL | LOCAL_AUTOMATIC`; существующие immutable Run records не мигрируются переписыванием и могут не содержать поле. История остаётся read-compatible. `execute-current` не создаёт Run при default manual mode; оператор может продолжать `next → verify → complete` без Podman.

Podman agent container получает подписанные host-only labels `io.project-harness.sandbox`, `io.project-harness.project-sha256` (hash точного Project Instance root), `io.project-harness.run` (точный Run ID); label не содержит секретов или полного пути. Timeout/output overflow: остановка контейнера (`podman stop --time 2` с SIGTERM→grace→kill), bounded `podman rm --force` и `container exists`, затем bounded SIGTERM/SIGKILL process group Podman CLI. Неподтверждённое завершение никогда не превращается в успешную аттестацию Run.

## 3. Host crash, orphan и retry

При повторном `execute-current` на подписанном незавершённом automatic Run engine сначала получает исключающую host-only project lock и проверяет orphan containers через rootless Podman. Если Podman недоступен, результат `BLOCKED / SANDBOX_UNAVAILABLE`; partial Agent Result **не используется** и агент не запускается на host.

После подтверждённой остановки всех containers данного проекта `recover_apply()` разбирает существующий durable journal **перед** новым attempt. Детерминированный результат: `ROLLED_BACK`, `APPLIED` либо `BLOCKED / APPLY_FAILED_RECOVERABLE` на неоднозначности. Старый Run disposable root помещается в `<trusted-runtime-root>/<project-id>/quarantine/<RUN-ID>-<nonce>`; его `/output/agent-result.json` не становится результатом нового Run. Run фиксируется `BLOCKED` с exact reason и `execution_origin: LOCAL_AUTOMATIC`. Новый Run появляется **только после** formal operator `resume --project <root> --resolution <text>` и получает иной Run identity; предыдущие records/evidence не переписываются.

Сбой после подписанного `AUTO_VERIFIED`, но до завершения очистки, не переисполняет агент и не откатывает уже committed product. Отсутствующий cleanup receipt восстанавливается только после проверки Podman + оставшегося Apply journal. Невозможность этой проверки сообщает отдельный cleanup blocker при сохранённом verified Run status. При новом READY attempt прежние execution roots проверяются и помещаются в quarantine; ambiguous journal/symlink/foreign owner блокируют продолжение.

## 4. Cleanup и ограничения

Для обычного финала удаляется private disposable execution root; для orphan/failed attempt он карантинируется. Bounded immutable receipt: `.harness/runtime/CLEANUP_REPORTS/<RUN-ID>.yaml` с `CLEANED`, `QUARANTINED`, `ALREADY_CLEANED` или `CLEANUP_FAILED`. Cleanup failure сохраняется **отдельно** и не меняет продуктовую independent verification/Apply Evidence. Crash leftover временных host-only env-secret файлов переносится вместе с root в quarantine либо перед удалением стирается best-effort; quarantine не является секретным архивом и требует контролируемой операторской очистки.

В handoff/PROJECT_LOCK/manifests попадают только bounded control metadata; raw execution roots, workspace и raw logs запрещены. При отсутствии реального non-root Podman нельзя считать `project_orphan_containers` успешно проверенным; unit mocks тестируют только orchestration/negative ветви и **не** OS isolation. `EXPLICIT_APPROVED_EGRESS` остаётся заблокированным; нет fallback на host. Stage/Gate/level-up, Brownfield, maintenance, Git/deployment и accepted maturity не изменялись.

**Приёмка в этом пакете:** migration/rollback/commit fault-injection, immutable-history hash, orphan label integrity, cleanup, partial result denial, recovered AUTO_VERIFIED/failed Podman cleanup, manual and previous PH-051-01..09 regressions. Живая Podman security matrix — отдельный PH-051-11/12 release gate; здесь `NOT RUN / NO GO release`.
