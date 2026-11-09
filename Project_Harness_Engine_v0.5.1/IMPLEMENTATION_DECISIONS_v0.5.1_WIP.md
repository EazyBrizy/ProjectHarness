# PH-051-01 — Registry collision and execution-policy decision

**Date:** 2026-10-25  
**Status:** ACCEPTED IMPLEMENTATION DECISION (PH-051-01 contract only), v0.5.1 WIP.

The normative v0.5.1 §19.1 says `REG-CONTRACT-CATALOG: 4 → 5`;
actual accepted source `Project_Harness_Engine_v0.5.0.zip` and existing
project locks contain `REG-CONTRACT-CATALOG@5` (no rebase permitted).
The safe compatible revision is **5 → 6**, while ID prefixes go 2 → 3,
statuses 5 → 6, project input 3 → 4, canonical schema 6 → 7.
A new project pins exact version/digest pairs in `PROJECT_LOCK`.
Historic registry snapshots and immutable project input are not rewritten;
manual v0.5.0 projects retain old registry snapshots and exact digests.
There is no claim that the original normative text has been amended.

`LOCAL_AUTOMATIC` may be specified in `PROJECT_INPUT@4` only with exact
revisioned ACTIVE ADP/SBX records. The profile resolver is read-only and
returns exact SHA-256; automatic `prepare` nonetheless fails closed with
`AUTOMATIC_EXECUTOR_NOT_IMPLEMENTED` until trusted executor+Podman doctor
activation is implemented. Manual is the only operational default.

`MIG-ENGINE-0.5.0-TO-0.5.1` names the conservative PROJECT_INPUT v3→v4
normalization and the future persisted-project migration. PH-051-10 still
owns its in-place migration route; PH-051-01 does not silently upgrade or
rewrite old locks. No security testing of rootless Podman was performed.
