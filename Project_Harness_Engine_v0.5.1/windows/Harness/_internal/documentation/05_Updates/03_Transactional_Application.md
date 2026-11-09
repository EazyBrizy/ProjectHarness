# Транзакционное применение и crash recovery

**Документ:** Project Harness  
**Версия:** 0.5.0  
**Дата:** 2026-08-18  
**Статус:** NORMATIVE IMPLEMENTED BASELINE

## 1. Storage boundary

v0.5.0 гарантирует crash-consistency только внутри одного project-local filesystem boundary. Для Stage mutations это означает: после завершения automatic recovery весь canonical write set находится либо в точном old state, либо в точном new state. Mixed canonical state не является допустимым terminal result.

Эта гарантия не является distributed transaction protocol. Multi-repository, remote control plane, daemon, multi-host locking, deployment side effects и external databases остаются вне v0.5.0.

## 2. Реализованный Stage transaction service

Governed Stage transitions используют каталог:

```text
.harness/stages/TRANSACTIONS/<transaction-id>/
├── TRANSACTION.yaml
├── backups/
├── staged/
└── recovery/
```

`TRANSACTION.yaml` является durable reconciliation record. `backups/` содержит immutable copies old files, `staged/` — сериализованный expected new write set, а `recovery/` используется только для безопасного восстановления из backup без уничтожения исходной backup copy.

Transaction service применяется к реализованным Stage mutation entry points `accept-stage` и `level-up`. Тот же helper принимает operation kind и ordered write set, поэтому существующие или последующие governed Stage/Gate routes могут подключаться без создания отдельного transaction framework.

## 3. Journal contract до первого canonical replace

До первого canonical replacement journal обязан быть записан и fsync-подтверждён. Он содержит как минимум:

| Поле | Назначение |
|---|---|
| `id` | deterministic transaction id |
| `operation_kind` | тип Stage operation |
| `request_digest` | canonical digest входа для idempotency |
| `sequence` | монотонный локальный sequence |
| `ordered_write_set` | полный lexicographically ordered target set |
| `entries[].target` | canonical relative target path |
| `entries[].existed_before` | существовал ли target до transaction |
| `entries[].backup_path` | immutable old copy, если target существовал |
| `entries[].staged_path` | serialized new candidate |
| `entries[].old_digest` | expected old digest, если применимо |
| `entries[].expected_new_digest` | expected new digest |
| `entries[].apply_state` | `PENDING`, `APPLIED` или `VERIFIED` |
| `entries[].recovery_state` | recovery progress/verification state |
| `status` | transaction lifecycle status |
| timestamps | prepare/apply/commit/recovery/rollback times |
| `result` и `result_digest` | replayable operation result |
| `write_set_digest` | digest immutable write-set metadata |

Backups и staged candidates fsync’ятся до durable `PREPARED`. Canonical target не может пересекаться с transaction storage, быть symlink или выходить за project root.

Перед переходом в `APPLYING` service повторно читает durable journal и заранее проверяет структуру journal, каждый required backup и digest каждого staged candidate. Непроверенный prepared write set не получает права выполнить первый canonical replace.

## 4. Transaction lifecycle

Internal lifecycle:

```text
PREPARED
→ APPLYING
→ COMMITTED

PREPARED/APPLYING
→ ROLLING_BACK
→ ROLLED_BACK

corrupt or unverifiable recovery
→ RECOVERY_REQUIRED / blocking diagnostic
```

`COMMITTED` разрешён только после digest verification каждого canonical target против `expected_new_digest`. `ROLLED_BACK` разрешён только после проверки, что каждый existed-before target совпадает с `old_digest`, а каждый absent-before target отсутствует.

Per-entry progress полезен для audit, но recovery не доверяет только progress flags: terminal decision всегда подтверждается фактическими canonical digests.

## 5. Ordered apply protocol

Stage transaction выполняется в следующем порядке:

```text
recover/reconcile earlier transaction
→ validate exact request and transaction id
→ serialize complete candidates
→ create and fsync backups
→ persist PREPARED journal
→ re-read and preflight-verify journal/backups/all staged digests
→ persist APPLYING journal
→ replace canonical targets in ordered write-set order
→ persist per-entry apply state
→ verify the complete canonical new write set by digest
→ persist COMMITTED journal
→ return committed result
```

Acceptance transaction включает Acceptance Report, Stage Plan/Gate revisions and indexes, Stage State/history, Decision, `CURRENT_STATE`, `NEXT_TASK` и связанные supersession changes. Level-up включает новый target/path, nearest-stage activation, Stage Plan/Gate revisions and indexes, Stage State/history, project state и stale/superseded prompt changes, где они уже предусмотрены v0.5.0 semantics.

## 6. Deterministic recovery

Recovery выполняется перед новой Stage mutation и как первая часть `validate-project`.

Для unique latest non-terminal transaction используется только следующий rule:

1. если **весь** new write set уже существует и каждый digest совпадает, recovery завершает commit и записывает `COMMITTED`;
2. во всех остальных recoverable состояниях recovery восстанавливает **весь** old write set из verified backups и записывает `ROLLED_BACK`;
3. при отсутствующем/повреждённом journal, backup, digest metadata или неоднозначной последовательности recovery не угадывает и блокирует дальнейшую mutation точным diagnostic.

Partial replacements, stale per-entry flags и повторный запуск recovery не меняют это правило. Recovery idempotent: terminal transaction при повторном запуске получает `NO_ACTION` на reconciliation layer.

## 7. Failure truthfulness

API result, journal status и canonical state обязаны описывать один факт.

| Фактическое состояние после reconciliation | Durable journal | API behavior |
|---|---|---|
| full new write set | `COMMITTED` | committed success |
| full old write set после apply failure | `ROLLED_BACK` | исходная operation error |
| corrupt/unverifiable state | non-terminal or recovery-required diagnostic | mutation blocked |

Комбинация `API error + ROLLED_BACK journal + committed canonical state` запрещена.

Если все replacements завершены, но первая запись финального `COMMITTED` marker не удалась, service повторно проверяет digests и пытается восстановить marker. Одноразовый journal failure возвращает committed success с recovery warning. Если marker невозможно записать устойчиво, service полностью восстанавливает old state, подтверждает `ROLLED_BACK` и только затем возвращает error.

## 8. Idempotency

Transaction id детерминирован formal approval record. Повтор команды с тем же id, operation kind и request digest после `COMMITTED` возвращает сохранённый result с `idempotent: true` и не создаёт второй transition.

Повтор того же id с изменённым request блокируется. Повтор id после подтверждённого `ROLLED_BACK` также блокируется: новая попытка требует нового formal approval и нового transaction id, после чего operation semantics валидируются заново.

## 9. Derived rendering after commit

`ROADMAP.md` и `STATUS.md` являются derived views, а canonical Stage facts уже committed. Поэтому render failure после canonical commit не превращает transition в ложный failure.

Result возвращает:

```text
transaction_status: COMMITTED
render_status: FAILED_RECOVERABLE
```

и явный regeneration route. Повтор идентичной committed command безопасно воспроизводит result и повторяет rendering без нового Stage transition.

## 10. Validation and blocking diagnostics

`validate-project`:

- запускает automatic recovery до обычной semantic validation;
- проверяет структуру и digests всех journals/backups;
- требует terminal status для завершённых transactions;
- обнаруживает mixed target state;
- сопоставляет current Stage indexes/files, Stage State, Acceptance Reports, `CURRENT_STATE` и `NEXT_TASK` с последним завершённым transition;
- возвращает `FAIL`, если recovery заблокирован corruption или ambiguity.

Новая Stage mutation не может проигнорировать unresolved `PREPARED`, `APPLYING`, `ROLLING_BACK` или corrupt transaction root.

## 11. Fault model and conformance

Focused fault-injection suite покрывает:

- failure до каждого canonical apply replace;
- abrupt process loss после каждого canonical replace;
- PREPARED journal write failure;
- durable PREPARED crash до replacements;
- per-entry state persistence failure;
- per-entry recovery-progress persistence failure без остановки full-old restoration;
- one-shot и persistent final COMMITTED marker failure;
- all-replacements-without-marker recovery;
- repeated recovery;
- committed replay и rolled-back retry policy;
- corrupt backup blocking;
- render failure after commit;
- tampered current Stage index, `CURRENT_STATE` и missing Acceptance Report при terminal `COMMITTED` journal;
- acceptance и level-up consistency.

Каждый terminal assertion проверяет digests всего write set, Stage State, Acceptance Report и `CURRENT_STATE`; full-old/full-new являются единственными допустимыми outcomes.

## 12. General Change Pack boundary

Product, Project Control и Harness Distribution Change Packs остаются раздельными planes. Cross-plane program является ordered parent plan, а не одной mixed transaction. External actions используют явные verify/compensation semantics; Stage transaction service не расширяет v0.5.0 до distributed transaction framework.
