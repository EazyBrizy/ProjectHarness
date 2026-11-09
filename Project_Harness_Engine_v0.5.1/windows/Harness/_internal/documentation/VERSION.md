> **Current distribution: 0.5.1-WIP / NOT RELEASED, through PH-051-11.** Engine/package version `0.5.1`; canonical schema `7`, `PROJECT_INPUT@4`, ID-prefix registry `3`, lifecycle registry `6`, contract catalog `6` (5→6 documented collision decision). Read [operator runbook v0.5.1](05_Updates/14_Operator_Runbook_v0.5.1_WIP.md) and [security validation](05_Updates/15_Podman_Security_Validation_v0.5.1_WIP.md). Live rootless Podman security attestation is **NOT TESTED / NO GO** here. The remaining v0.5.0 version block below records historical, immutable baseline semantics; it is not the current wheel version.

> **Current delivered package:** `0.5.1-WIP`, PH-051-06 exact result channel,
> immutable kernel ART/Agent Result records, bounded logs and allowlisted ENV
> secret refs (after PH-051-01–05). No public automatic CLI, independent
> verification, product apply or final release. Real Podman security integration
> **NOT RUN / NO GO** on this host. See
> [PH-051-06 note](05_Updates/10_Exact_Result_Channel_v0.5.1_WIP.md).
>
> **Current delivered package:** `0.5.1-WIP`, PH-051-05 exact ADP/SBX-bound
> local Codex CLI adapter (after PH-051-01–04), sandbox-only argv/doctor API.
> No public automatic CLI, result acceptance, verification or apply; real rootless
> Podman tests and actual Codex CLI image/flags **NOT RUN** on packaging host.
> See [PH-051-05 note](05_Updates/09_Local_Codex_CLI_Adapter_v0.5.1_WIP.md).

> **Current delivered package:** `0.5.1-WIP`, PH-051-04 disposable execution root
> and bounded control projection after PH-051-01/02/03. Version remains 0.5.1; schema 7,
> PROJECT_INPUT@4, registries id_prefixes=3, statuses=6, contracts=6.
> Real Podman security checks **NOT RUN** in packaging environment;
> automatic public `execute-current` remains unavailable, manual handoff only.
> See [disposable-root note](05_Updates/08_Disposable_Execution_Root_v0.5.1_WIP.md).
> Historic v0.5.0 baseline information below remains as accepted.

# Версия комплекта Project Harness

**Документ:** Project Harness  
**Версия:** 0.5.0  
**Дата:** 2026-08-18  
**Статус:** STAGE AWARE CORE RUNTIME BASELINE

```text
0.5.0
```

## Семантика версии

v0.5.0 является minor release поверх принятого v0.4.1. Она добавляет новый управляемый lifecycle реализации, не меняя утверждённый product scope и не включая будущие executor/Git/deployment capabilities.

Версия фиксирует:

- documentation and engine distribution `0.5.0`;
- canonical project schema `6`;
- strict `PROJECT_INPUT@3` / `SCHEMA-PROJECT-PREPARATION-INPUT@3`;
- canonical levels `PROTOTYPE`, `ALPHA`, `BETA`, `MVP`, `RELEASE`;
- statuses registry `5`;
- contracts registry `5`;
- id-prefix registry `2` с `STG`;
- implementation-level registry `1`;
- migration `MIG-ENGINE-0.4.1-TO-0.5.0`;
- Stage State, Plans, Gates, Acceptance Reports и Maturity Assessments;
- `TARGET_LEVEL_REACHED` вместо преждевременного project completion;
- atomic stage acceptance и nearest-next-stage activation;
- read-only Brownfield maturity и separate same-level maintenance route;
- normalized immutable Gate evidence schema/resolver with exact path, kind, provenance, subject, baseline and digest validation;
- accepted Gate/Acceptance evidence binding snapshots verified by `validate-project`.

## Compatibility

- **Documentation release:** 0.5.0
- **Canonical project schema:** 6
- **PROJECT_INPUT schema:** 3
- **Engine distribution:** 0.5.0
- **Python runtime:** 3.11+
- **Direct project migration source:** engine 0.4.1 / schema 5
- **Documentation migration source:** v0.4.1
- **Legacy history:** immutable v0.4.1 records preserved
- **OS sandbox / automated executor / Git publication:** не заявлены

## Versioned components

```text
Harness kernel
Canonical schemas
Machine registries
Implementation Level Registry
Stage State / Plans / Gates / Acceptance / Assessments
Prompt and Context compiler
Project preparation templates
Project-local embedded runtime
Migration rules
Documentation package
```

`PROJECT_LOCK` фиксирует exact registry versions/digests и applied migration IDs. Accepted Stage baselines и completed Runs не переписываются при level-up или maintenance.
