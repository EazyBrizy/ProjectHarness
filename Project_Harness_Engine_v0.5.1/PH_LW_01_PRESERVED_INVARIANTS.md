# PH-LW-01 — preserved invariants / next-stage blockers

**Версия:** 0.5.1-WIP  
**Дата:** 2026-11-01  
**Status:** CHARTER / CONTRACT ONLY; no release claim.

- Core stages remain ordered `PROTOTYPE → ALPHA → BETA → MVP → RELEASE`, current canonical target in `.harness/stages/STAGE_STATE.yaml` with accepted input immutable.
- Per-stage tasks/JIT only for active stage, Stage Gate requires real subject-specific evidence and formal DEC/ACT acceptance; no UI receipt is Gate evidence.
- Formal 4/5 intake approvals distinct from Stage/level-up/maintenance decisions; untrusted GPT draft cannot approve anything or opt into automatic egress.
- Manual `next/verify/complete` still needs verification; `verify` host commands only on explicit exact consent in future UI. No automatic provider/agent call added.
- Automatic `execute-current` remains inaccessible in proposed manual Windows UI; no `fcntl` workaround or host fallback was added.
- Brownfield assessment/maintenance/migration and Stage transactions keep exact refs, immutability, single-stage transitions and recovery behavior.
- No historical reports rewritten, no normative specification edited, no production code modified outside added pure JSON resources.
- Windows import (`fcntl`), NTFS interprocess locking, browser/HTTP policy enforcement, safe publish and installer are future separate scoped stages; **NOT RUN/NO-GO** in this delivery.
- Input PH-051-12 hashes absent; actual base PH-051-11 WIP. This provenance difference must remain visible in every following step.
