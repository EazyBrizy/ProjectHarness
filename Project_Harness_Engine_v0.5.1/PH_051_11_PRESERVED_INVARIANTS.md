# PH-051-11 — сохранённые инварианты v0.5.0 и PH-051-01..10

**Статус:** `v0.5.1-WIP / NOT RELEASED`. В PH-051-11 не проводился финальный release acceptance (§24, PH-051-12), а реальная rootless Podman security matrix осталась `NOT TESTED / NO-GO`.

1. **Scope/maturity**: последовательные `PROTOTYPE → ALPHA → BETA → MVP → RELEASE`, только approved Stage Gate/level-up, только active Stage подробные Tasks; target не расширяет accepted scope. `stages.py` и `stage_transactions.py` не изменялись.
2. **Canonical и история**: Stage State — canonical current target; accepted `PROJECT_INPUT`, completed Runs, Stage Acceptance Reports, Stage Plans/Gates и исторические evidence не переписывались; PH-051-11 не модифицировал ни одного Project Instance для выпуска. Подтверждать сохранение можно regression tests и сравнением changed-file list с исходными ZIP.
3. **Governance**: strict formal approvals, exact revision/digest/baseline, Brownfield read-only assessment, same-level maintenance, evidence-kind/subject/provenance, `NOT_APPLICABLE` gates и анти-fabrication Gate evidence остаются прежними.
4. **Execution boundaries**: `MANUAL_HANDOFF` default, explicit `LOCAL_AUTOMATIC` contract без несанкционированного включения; `NONE` network default, fail-closed on unavailable Podman, no automatic switch to host/manual, one `CODEX_CLI_LOCAL` and one `ROOTLESS_PODMAN` backend.
5. **Product/control isolation**: canonical product и `.harness` не отдаются агенту на запись; disposable roots, bounded projection и result channel остаются unchanged; host rootless OS sandbox на текущем стенде **не доказан**.
6. **Independent verification и apply**: agent-declared success не равен независимому PASS; scope, baseline, secret scan, journal/recovery/immutable Apply Evidence не затронуты; no false Stage Gate PASS.
7. **Migration/recovery**: v0.5.0→v0.5.1 migration сохраняет manual default и immutable history; orphan quarantine, bounded termination и retry/replay protection сохраняются без изменений кода.
8. **Records/security**: только exact revisioned ADP/SBX schema-valid examples, никакие исходные секреты/действующие credentials и verified image identifiers в примеры не включены; egress example отвергается как нормативный approval.
9. **Delivery**: wheel и embedded/standalone docs синхронны, nested docs manifest теперь действительно проверяется distribution doctor и защищён от подмены.

**Обнаруженные блокеры (не исправленные в этом этапе):** фактический `prepare` отклоняет новый `LOCAL_AUTOMATIC` даже при реализации команд `executor-doctor`/`execute-current`; нет публичного поддерживаемого governed пути изменить lock; `EXPLICIT_APPROVED_EGRESS` не активируется (NONE-only). Требуется отдельное scope решение; запрещены private-Python/test-fixture обходы. Отсутствуют rootless Podman и pinned image для OS security acceptance. Детали см. `PH_051_11_TEST_REPORT.md` и `PH_051_11_SECURITY_MATRIX.md`.
