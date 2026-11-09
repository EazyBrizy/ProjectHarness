# Каноническая модель и генерируемые артефакты

**Документ:** Project Harness  
**Версия:** 0.5.0  
**Дата:** 2026-08-18  
**Статус:** PROPOSED IMPLEMENTATION BASELINE — готов к реализации после подтверждения

## 1. Один источник истины

Tasks, prompts, roadmaps, status and reports are not maintained as unrelated hand-written copies. Harness stores normalized entities and reproducibly generates views.

## 2. Canonical domains

```text
Workspace
└── Project
    ├── Sessions / Sources / Source Inventory
    ├── Requests / Request Plans / Routes / Results / Request Traces
    ├── Project Definition
    │   ├── Users / Outcomes / Goals / Success Criteria
    │   ├── Scope / Assumptions / Unknowns / Risks
    │   └── Authority / Profiles
    ├── Requirements / Quality Attributes
    ├── Constraints / Invariants / Policies / Waivers
    ├── Questions / Answers / Decisions / ADR
    ├── Architecture Options / Architecture Baseline
    ├── Technology Candidates / Technology Baseline / Compatibility
    ├── Repositories / Environments / Bootstrap
    ├── Contracts / Artifacts / Documentation Sections
    ├── Work Packages / Tasks / DAG / Parallel Batches / Leases
    ├── Prompt Modules / Prompt Specs
    ├── Context Policies
    ├── Skills / Verification Profiles / Adapter Profiles
    ├── Change Packs / Migrations
    ├── State / Events
    └── Run Plans / Runs / Tool Invocations / Evidence / Task Reports / Blockers
```

`Run` является отдельной attempt; отдельной canonical сущности `Attempt` в v0.3 baseline нет.

## 3. Candidate and accepted artifacts

```text
Candidate
→ schema and semantic validation
→ material review/gate
→ Accepted | Rejected | Superseded
```

Candidate stores generator, sources/spans, confidence, unresolved conflicts, timestamp and hash. Confidence is advisory and never replaces a gate.

## 4. Generated artifacts

- Project Definition and brownfield baseline views;
- PROJECT/ARCHITECTURE/TECHNOLOGY/ROADMAP/STATUS/AGENTS documents;
- requirement/constraint/documentation coverage;
- DAG and task cards;
- Prompt Plans, Compiled Bundles and Context Packets;
- capability resolutions;
- Task Reports and Result renderings;
- commit/release plans;
- combined documentation, indexes and manifests.

Generated header:

```yaml
generated_by: project-harness
engine_version: 0.4.1
source_model_revision: sha256:...
generator_contract_version: 1
manual_edit_policy: FORBIDDEN_OR_IMPORT_AS_CHANGE_PACK
```

## 5. Source maps and reproducibility

Every generated material block maps to canonical entity ID/revision, source hash, transformer/compiler version, precedence decision and effective policy set.

## 6. Entity completeness

Every persistent entity requires:

```text
schema
ID prefix
lifecycle/status registry
storage path
revision/hash semantics
provenance
migration policy
validation rules
```

## 7. ID and status registries

The canonical registry is defined in [`../12_Implementation_Specifications/18_Registries_Lifecycles_and_Contract_Normalization.md`](../12_Implementation_Specifications/18_Registries_Lifecycles_and_Contract_Normalization.md). Documents and examples must not define independent prefix/status lists.

## 8. Human and machine layers

Canonical state resides in machine layer. Human documents are synchronized views with stable section IDs and source refs. Detailed policy: [`../12_Implementation_Specifications/17_Documentation_Layers_and_Minimal_Mode.md`](../12_Implementation_Specifications/17_Documentation_Layers_and_Minimal_Mode.md).
