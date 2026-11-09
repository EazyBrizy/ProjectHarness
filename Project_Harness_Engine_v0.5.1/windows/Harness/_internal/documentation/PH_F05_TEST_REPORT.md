# PH-F05 — Test report (2026-10-24)

**Версия:** 0.5.0  
**Дата:** 2026-08-18  
**Дата исходного прогона:** 2026-10-24  
**Примечание упаковки PH-F06:** добавлена обязательная metadata; результаты исходного PH-F05 ниже не изменены.

Scope: semantic interview and initial Project Instance creation only.

## Test runs
- `PYTHONPATH=src:. python -m unittest tests.test_ph_f05_intake_acceptance -q`: PASS, 4 tests, 2 Greenfield handoff cases.
- `PYTHONPATH=src:. python -m unittest tests.test_engine tests.test_contract_hardening tests.test_ph_f03_active_stage_planning tests.test_ph_f04_runtime_reachability tests.test_ph_f05_intake_acceptance -q`: TIMEOUT / INCOMPLETE. Long-running nested suite; not claimed as complete.
- Initial `python tests/run_tests.py`: TIMEOUT/INCOMPLETE (initial Brownfield cases passed before timeout).
- `python -m pip wheel . --no-deps --no-build-isolation -w dist`: PASS.
- `python project-harness.py doctor`: PASS after manifest correction.

## Findings and boundaries
- Confirmed 4 separate Greenfield approval keys, 5 for Brownfield and Hybrid; canonical targets required; UNSURE -> WAITING_DECISION, UNKNOWN sensitivity -> WAITING_INPUT.
- Two independent Greenfield source conditions (without documents and with normative document) reached READY_FOR_CODEX, and ZIP validation returned PASS.
- Confirmed changed target followed by re-check changes readiness and is reversible.
- Fixed PH-F05 source/workspace overlap guard before destructive force reset; negative tests verify supplied data remain intact.
- GPT semantic behavior (which questions are asked to a human or whether a source claim is trustworthy) is an instruction contract, not machine-proven by these engine tests.
- No assertion that all 117+ tests passed; PH-F08 remains mandatory release gate.

## Regression constraints
No modifications to Stage acceptance, evidence/Gate, level-up, runtime, Brownfield assessment or maintenance semantics. Existing normative v0.5.0 level and target model retained.
