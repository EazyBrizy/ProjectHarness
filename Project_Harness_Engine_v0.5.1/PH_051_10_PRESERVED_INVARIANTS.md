# PH-051-10 — Сохранённые инварианты

- Только governed последовательные Stage transitions `PROTOTYPE→ALPHA→BETA→MVP→RELEASE`, никаких level-up/Stage API изменений.
- `.harness/stages/STAGE_STATE.yaml` остаётся canonical source current-cycle target; принятую историю и `PROJECT_INPUT_ACCEPTED` миграция не переписывает.
- Stage Acceptance Reports, historical Stage plans/Gates, preexisting completed manual Runs byte-identical до/после migration.
- Brownfield assessment exact refs, semantics Stage Gate proof и same-level maintenance остаются прежними.
- Legacy v0.4.1→v0.5.0 migration доступна; default v0.5.0→v0.5.1 только `MANUAL_HANDOFF`, `NONE`, explicit verification completion, без auto activation.
- Единственный automatic provider `CODEX_CLI_LOCAL` строго внутри rootless Podman; no unsandboxed fallback, Podman self-test failure блокирует автоматический путь.
- Agent output не равен независимой verification, PASS не подменяет Stage acceptance; apply baseline/write-set/secret scan остаётся обязательным.
- Apply journal recovery до любого нового попытки; неверифицированный partial output прошлой попытки карантинируется; new Run identity при retry.
- Runtime execution roots и raw logs не входят в handoff/project lock/export. Failed cleanup не выдаётся за successful verification.
- Версия остаётся `0.5.1-WIP / NOT RELEASED` до PH-051-11/12 и реальной rootless Podman security matrix.
