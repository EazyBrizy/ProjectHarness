# PROJECT_INPUT@3 field guide

`PROJECT_INPUT.yaml` may use JSON syntax; JSON is valid YAML 1.2 and keeps the Project Harness core runtime dependency-free.

The canonical contract is `SCHEMA-PROJECT-PREPARATION-INPUT@3` in `schemas/project_input.schema.json` (JSON Schema Draft 2020-12). All normative objects are closed with `additionalProperties: false`; the only open extension point is `skills.resolutions[].configuration`. Unknown fields are errors and are never silently discarded. Forbidden provider accounting keys are rejected even inside the open configuration object.

The input is semantic, not merely a form. Browser GPT must ground it in user answers, supplied documentation, repository inventory, and explicit evidence. The deterministic engine validates the same required/allowed keys, types, enums, IDs, profiles, capabilities, scopes, dependency DAG, implementation decision, and approvals without requiring the optional `jsonschema` package.

## Implementation section

```json
{
  "implementation": {
    "target_level": "MVP",
    "claimed_current_level": "NONE"
  }
}
```

`target_level` accepts `PROTOTYPE`, `ALPHA`, `BETA`, `MVP`, `RELEASE`, or temporary decision value `UNSURE`. A handoff requires a canonical level. `UNSURE` returns `WAITING_DECISION`; the engine may recommend a level but never substitutes it automatically.

`claimed_current_level` accepts `NONE`, `UNKNOWN`, or a canonical level. Greenfield requires `NONE`. Brownfield/Hybrid requires a user claim, normally `UNKNOWN` when no defensible claim exists. This field never stores observed or accepted maturity.

Implementation level controls depth and evidence, not product scope. `MVP` means Production MVP. Higher targets do not automatically require technologies, cloud services, microservices, Kubernetes, CI/CD, or new features.

## Stage planning semantics

The target defines a sequential path from `PROTOTYPE`. For target `MVP`:

```text
PROTOTYPE → ALPHA → BETA → MVP
```

The input `planning.work_packages` supplies the detailed active-stage DAG. The compiler generates outlines and Gates for all later stages but does not create atomic Tasks or executable Prompt Bundles for them. Future stages are replanned from the accepted prior-stage baseline.

Every non-`VERIFY` task needs a non-empty write scope. Every task needs commands, expected paths, or explicitly allowed manual checks. Task dependency aliases are resolved to canonical `TSK-*` IDs.

## Data sensitivity

Accepted classifications are:

- `PUBLIC`
- `INTERNAL`
- `CONFIDENTIAL`
- `RESTRICTED`
- `SECRET`
- `REGULATED`

`UNKNOWN` is temporary during intake. It keeps readiness at `WAITING_INPUT` and cannot pass the handoff gate.

## Approval gates

A `GREENFIELD` input requires four explicit approvals:

1. `project_definition`
2. `architecture_baseline`
3. `technology_baseline`
4. `codex_handoff`

A `BROWNFIELD` or `HYBRID` input requires a fifth, separate gate:

1. `project_definition`
2. `brownfield_baseline`
3. `architecture_baseline`
4. `technology_baseline`
5. `codex_handoff`

Every approved record requires its own non-empty `actor` and RFC 3339 `approved_at`. A questionnaire answer is not an approval. Brownfield approval becomes an immutable `DEC-<PROJECT>-BROWNFIELD-001@1`, and the accepted baseline references it.

## Brownfield maturity fields

Do not add runtime conclusions to `PROJECT_INPUT@3`. These are persisted separately in Stage State and Maturity Assessment:

- `observed_candidate_level`
- `highest_satisfied_candidate_level`
- `highest_accepted_level`
- assessment criteria, evidence, dimensions, route, and confidence

Assessment is read-only with respect to product files and never automatically runs repository commands. Formal baseline acceptance requires a separate `accept-stage` approval with exact assessment reference and SHA-256 digest.

## Skills

`CREATE` and `EXTEND` remain rejected by the Core preparation route. v0.5.0 accepts only `REUSE`, `CONFIGURE`, or `TASK_ONLY`. Governed declarative PROJECT skill authoring is not part of this release.

## Migration

`MIG-ENGINE-0.4.1-TO-0.5.0` upgrades a v0.4.1 Project Instance from input v2/schema 5 to input v3/schema 6. The target level must be supplied explicitly. Completed legacy history is preserved and is not converted into an accepted implementation level. The project migration is transactional and idempotent after full current-state validation.

The input migration implementation also accepts older v1 input only through the explicit sequential compatibility path; unknown properties are preserved for error reporting rather than silently dropped.
