# Безопасность, trust boundaries и supply chain

**Документ:** Project Harness  
**Версия:** 0.5.0  
**Дата:** 2026-08-18  
**Статус:** PROPOSED IMPLEMENTATION BASELINE — готов к реализации после подтверждения

## 1. Классы доверия

| Класс | Пример | Политика |
|---|---|---|
| TRUSTED_DISTRIBUTION | Engine, schemas, immutable safety policy | Signature/digest and release validation. |
| TRUSTED_PROJECT | Accepted Project Definition, decisions, constraints, contracts | Versioning, authority and ownership. |
| CANDIDATE_INFERENCE | Extracted requirement, architecture proposal, semantic review | Schema/provenance; no canonical acceptance without gate. |
| UNTRUSTED_INPUT | New docs, repository text, ZIP, Change Pack | Quarantine, parsing, no instruction authority. |
| GENERATED | Prompt/context/views/reports | Source revision, compiler and schema validation. |
| EXTERNAL_TOOL_OUTPUT | Build logs, scanner output, web/API response | Size limits, redaction, delimiting and evidence hash. |

## 2. Архивная безопасность

Harness проверяет:

- path traversal and absolute paths;
- symlink/hardlink escapes;
- decompression ratio and archive limits;
- nested archives;
- filename/case collisions;
- executable and unexpected binary types;
- manifest/hash mismatch;
- writes outside quarantine;
- parser resource limits.

## 3. Prompt injection

Документ, code comment или tool output не может:

- менять instruction precedence;
- повышать authority;
- включать tools/capabilities;
- разрешать commit/push/deploy;
- обходить constraints/security policy;
- требовать secrets;
- изменять Harness maintenance route.

Untrusted excerpts помещаются в отдельный data layer с source delimiters.

## 4. Secrets

- не входят в canonical docs, Prompt Bundles, reports или run traces;
- используются references/providers;
- tool output проходит redaction;
- secret scan выполняется на changed paths;
- наличие доступа не доказывается раскрытием значения;
- входные bundles с secrets блокируются или quarantined;
- credential rotation не кодируется как обычный project task без security policy.

## 5. Опасные действия

Требуют explicit capability и approval:

- destructive migration/data deletion;
- force/reset/history rewrite;
- production deployment;
- push to protected branch;
- publication/release;
- disabling audit/security checks;
- execution of supplied scripts;
- modification outside registered repositories;
- expansion of data egress boundary;
- creation/use of privileged credentials.

## 6. Inference safety

Model-assisted component выдаёт candidate output. Kernel проверяет schema, source refs, forbidden claims и effective constraints. Model не может самостоятельно утверждать waiver, decision authority или PASS evidence.

## 7. Distribution integrity

Archive содержит version, manifest, checksums, optional signature/attestation, dependency lock и validation report. Project lock фиксирует exact distribution/compiler/profile/adapters digests.

## 9. v0.4.1 control-plane assurance boundary

v0.4.1 добавляет deterministic tamper detection: protected snapshot, exact file type/digest/size/link-count checks и chained phase-boundary operation journal. Нарушение переводит active Task, Run и Project в `BLOCKED` до восстановления доверенного control plane.

Эта гарантия не равна OS-level write prevention. Journal не является secret-backed digital signature, а Python process не является security sandbox. Rootless container isolation и enforceable filesystem boundary относятся к v0.5.1.
