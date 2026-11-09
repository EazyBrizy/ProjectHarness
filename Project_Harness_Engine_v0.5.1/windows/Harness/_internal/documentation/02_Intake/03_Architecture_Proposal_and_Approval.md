# Architecture и Technology Proposal / Decision Gates

**Документ:** Project Harness  
**Версия:** 0.5.0  
**Дата:** 2026-08-18  
**Статус:** PROPOSED IMPLEMENTATION BASELINE — готов к реализации после подтверждения

## 1. Preconditions

Architecture and Technology proposer starts after Project Definition dimensions are confirmed/classified:

- outcomes/users/scope/success;
- hard constraints/invariants;
- material quality attributes;
- data/security/integration boundaries;
- target platforms and operation model;
- brownfield actual baseline when applicable.

## 2. Separate but linked baselines

- Architecture Baseline defines components, boundaries, data ownership, contracts, deployment topology and quality tactics.
- Technology Baseline defines languages, runtimes, frameworks, databases, infrastructure, build/test tools, versions and compatibility.

Neither is inferred silently from a profile/template.

## 3. Proposal output

```text
Architecture Input Assessment
Architecture Options
Technology Candidates
Decision Matrix
Risk Register
Open Decisions
Migration/Rollback implications
Skill and Bootstrap impact
```

Material choice normally presents 2–4 realistic options with benefits, trade-offs, risks, reversibility and requirement/constraint coverage.

## 4. User-facing gate

```text
ACCEPT_OPTION
ACCEPT_WITH_CHANGES
REQUEST_ADDITIONAL_OPTION
CONTINUE_DISCOVERY
REJECT_AND_REDESIGN
UNKNOWN_USE_REVERSIBLE_BASELINE
```

Each question explains what it changes and offers a recommendation. `UNKNOWN` is allowed only when a reversible assumption and review trigger are safe.

## 5. Decision recording

After approval:

- Architecture Baseline;
- Technology Baseline;
- ADR/Decision records only for material decisions;
- immutable option/proposal hashes;
- consequences, obligations and residual risks;
- compatibility matrix;
- skill gaps and bootstrap prerequisites;
- impact on Work Packages.

## 6. Completeness

Gate verifies:

- release-scope MUST coverage;
- hard constraints;
- no unresolved contract/data ownership conflict;
- version compatibility or prerequisite validation task;
- bootstrap/test/operation path;
- rollback/migration approach;
- no profile default mistaken for user decision.

## 7. Change after start

Material architecture/technology change uses `PROJECT_EVOLUTION` and Change Pack. Completed history remains immutable; affected future tasks/plans become stale.

Details: [`../12_Implementation_Specifications/06_ADR_and_Decision_Policy.md`](../12_Implementation_Specifications/06_ADR_and_Decision_Policy.md) and [`../12_Implementation_Specifications/13_Technology_Baseline.md`](../12_Implementation_Specifications/13_Technology_Baseline.md).
