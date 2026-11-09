## PH-LW-05 — Native local source import (Windows test NOT RUN)

With pinned HTTP extras installed, run `project-harness ui`; open «Документы» and create a GREENFIELD intake, choose or drop MD/ZIP files, then explicitly import or choose «Документации нет». The app stores immutable snapshots in private sibling `imports/`, never extracts dangerous ZIP members and never sends data externally. The installed-wheel browser/API import flow requires a **real** Flask/Waitress/Windows test. Reproduce with `local_web/ci_ph_lw_05_windows.ps1`. This Linux package cannot claim Windows NTFS acceptance; full v0.5.1 automatic remains NO-GO. See standalone doc `13_Local_Web_Manual_Companion/10_PH_LW_05_Document_Import_and_Source_Revisions.md`.

## PH-LW-04 — Local Web shell (0.5.1 WIP)

`project-harness ui` / `python project-harness.py ui` is an **optional** local browser interface. It requires the pinned Flask 3.1.3 / Waitress 3.0.2 and transitive wheel dependencies from `local_web/requirements-web-win_amd64-cp314.lock`, verified against the offline wheelhouse on the target Windows builder (not available on the current Linux assembly host). Installing the minimal engine wheel does **not** install web dependencies; they are intentionally isolated in `local-web` optional extra. Do not use Flask development server as a workaround. Default application data on Windows: `%LOCALAPPDATA%\ProjectHarness`; `--app-data` permits a trusted local alternative from the console, never from the browser. On normal startup the app opens the browser after binding `127.0.0.1:<ephemeral-port>`; no token is logged or placed in URL query. `--no-browser` is for headless diagnostics and cannot authenticate by itself. A missing browser integration requires a **new** launcher session to obtain a new one-time bootstrap; copying the bare URL does not bypass login. This is not an installer or Windows acceptance; those are future PH-LW-11/12 gates. See `docs/.../13_Local_Web_Manual_Companion/09_PH_LW_04_Loopback_HTTP_Session_and_UI_Shell.md`.

> **PH-LW-03 (2026-11-02; v0.5.1 WIP):** Python-only Local Web application service, без HTTP/installer. `LocalWebService`/`OperationRequest` — read-only status, explicit allowlisted mutation, shared CLI/public OS fence, durable operation receipts. Запуск тестов из Engine root: `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:. python -m unittest -v tests.test_ph_lw_03_service`. Для проверки Windows OS locking нужен настоящий Windows 11 x64 NTFS stand. **WINDOWS_NOT_TESTED; v0.5.1 NO-GO.**

> **PH-LW-02 (2026-11-01):** manual/preparation imports and Stage transaction path/locking boundaries are prepared for native Windows, **WINDOWS_NOT_TESTED**. Use `local_web/ci_ph_lw_02_windows.ps1` on real Windows 11 x64 NTFS. `executor-doctor`/`execute-current` remain `BLOCKED / SANDBOX_UNAVAILABLE` there with no host fallback. No GUI/installer is implemented by this phase.

# Установка и операторский запуск — актуальная поставка 0.5.1-WIP (PH-051-11)

**Статус:** NOT RELEASED, без подтверждённой Podman OS security acceptance. Ни `doctor`, ни `executor-doctor` на ручном проекте не являются разрешением сетевого или host Codex запуска.

Из **извлечённого корня Engine `Project_Harness_Engine_v0.5.1`**:

```bash
python project-harness.py --version
python project-harness.py doctor
python project-harness.py executor-doctor --help
python project-harness.py execute-current --help
```

Изолированная установка **поставленного wheel**, без загрузки зависимостей:

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install --no-index --no-deps dist/project_harness_engine-0.5.1-py3-none-any.whl
project-harness --version
project-harness doctor
project-harness executor-doctor --help
project-harness execute-current --help
```

`project-harness doctor` проверяет distribution, **не** контейнерную изоляцию. `executor-doctor --project <root>` выполняет project-scoped проверку профилей и real Podman только после подтверждённого opt-in; для `MANUAL_HANDOFF` вернёт `BLOCKED / EXECUTOR_UNAVAILABLE` (exit `3`) и не запустит Codex. `execute-current --project <root>` на manual проекте так же блокируется. Для ручного выполнения используйте `next → (внешний Codex) → verify → complete`. После `migrate-project --project <root>` режим остаётся `MANUAL_HANDOFF`; automatic opt-in посредством редактирования PROJECT_LOCK запрещён. Существующий `prepare` отклоняет `LOCAL_AUTOMATIC` — это зарегистрированный pre-existing blocker, а не приглашение изменять compiler в PH-051-11.

Подробности: [operator runbook v0.5.1](docs/Project_Harness_Documentation_v0.5.1/05_Updates/14_Operator_Runbook_v0.5.1_WIP.md) и [security matrix](docs/Project_Harness_Documentation_v0.5.1/05_Updates/15_Podman_Security_Validation_v0.5.1_WIP.md). Ниже — сохранённая базовая процедура v0.5.0 (история).

---

> **PH-051-10 operator migration (0.5.1 WIP):** For an already prepared **0.5.0/6** Project Instance: `project-harness migrate-project --project <root>` (existing public command); then `project-harness validate-project --project <root>`. This adds manual-only policy and does not automatically enable Podman; retry/recovery is described in `docs/Project_Harness_Documentation_v0.5.1/05_Updates/13_Migration_Cleanup_Orphan_Recovery_v0.5.1_WIP.md`. The original v0.5.0 install steps below remain historical.

> **PH-051-02 v0.5.1-WIP:** Extract `Project_Harness_Engine_v0.5.1`.
> The new Python executor protocol is not a public automatic route. Manual
> handoff alone remains operational; `execute-current` and rootless sandbox
> runner are not yet available. Commands below describe the retained v0.5.0
> manual lifecycle unless explicitly labeled otherwise.

# Installation — Project Harness Engine v0.5.0

**Release date:** 2026-08-18  
**Python:** 3.11+

**Current operator workflow:** [`docs/Project_Harness_Documentation_v0.5.0/08_Distribution/04_Operator_Runbook_v0.5.0.md`](docs/Project_Harness_Documentation_v0.5.0/08_Distribution/04_Operator_Runbook_v0.5.0.md). `doctor` checks distribution metadata; handoff validation checks the **initial** archive, not the post-Codex product.

## Run from the extracted archive

The core runtime has no mandatory third-party dependencies:

```bash
python project-harness.py doctor
python project-harness.py --version
python project-harness.py --help
```

Harness-generated `.yaml` files use JSON syntax, which is valid YAML 1.2. To read user-supplied block-style YAML, install the optional parser:

```bash
python -m pip install ".[yaml]"
```

## Install the bundled wheel without network access

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install --no-index --no-deps \
  dist/project_harness_engine-0.5.0-py3-none-any.whl
project-harness --version
project-harness doctor
```

The installed wheel uses embedded registries, schemas, skills, templates, and fixtures. `doctor` reports `layout: installed` for source/embedded parity because the top-level source copies are not part of an installed wheel.

## Smoke check

```bash
project-harness demo --output-dir ./demo --keep-directory
project-harness validate-handoff \
  --project ./demo/harness-demo-codex-handoff.zip
```

The embedded runtime in the generated project can then be checked with:

```bash
python ./demo/harness-demo-codex-handoff/.harness/engine/project-harness.py \
  validate-project \
  --project ./demo/harness-demo-codex-handoff
```

## Optional development test suite

From the source archive root:

```bash
PYTHONPATH=src:. python -m unittest tests.test_engine -v
PYTHONPATH=src:. python -m unittest tests.test_contract_hardening -v
PYTHONPATH=src:. python -m unittest tests.test_implementation_levels -v
# Full source regression suite with correct import path:
python tests/run_tests.py
# Optional pytest, if installed:
PYTHONPATH=src:. python -m pytest -q tests/test_implementation_levels.py
```

### PH-F03 continuation after accepted Stage

At `PLAN_ACTIVE_STAGE`, run the installed `project-harness prepare-active-stage-plan
--project <root> --output <record>` and then the separately reviewed
`project-harness plan-active-stage --project <root> --plan <record>`.
Read the PH-F07 operator runbook and the bundled planning documentation for the strict review
record and interrupted-transaction recovery. `next --project <root>` returns
only the first current-stage JIT, not automatic product execution.

## PH-F05 — intake source/workspace separation (2026-10-24)

`start-intake --force` now rejects a workspace that contains a supplied source,
initial PROJECT_INPUT file or repository, or is inside any of them (and vice versa).
This prevents accidental deletion during workspace reset and recursive source copying.
Use a separate external workspace. The rule applies to both CLI and Python API.

Acceptance tests: `PYTHONPATH=src:. python -m unittest tests.test_ph_f05_intake_acceptance -v`.
The browser GPT remains responsible for semantic interpretation and explicit approvals;
Engine readiness cannot itself prove that the interview asked each question.

## PH-F07: what the commands do not do

`READY_FOR_CODEX` is a compiler/handoff result, **not** the result of running Codex or shipping production code. The external agent must implement the current Task; the operator must check the exact Agent Task Result, run independent `verify`, and invoke `complete`. Missing Gate proof remains a gap/`BLOCKED`: a generic PASS report is not automatically valid for unrelated evidence kinds. Semantic approval requires an accountable human and verifiable source bindings. `verify --allow-command-execution` is **not** an OS sandbox. Maintained PH-F07 commands, records and recovery are documented in the linked operator runbook; release 0.5.0 boundaries remain unchanged.

## PH-051-03 rootless sandbox check (WIP)

`project-harness doctor` still checks distribution health, **not** rootless
isolation. With an exact active SBX profile, the Python API
`RootlessPodmanRunner(configured_executable="codex").doctor(profile)`
requires real rootless Podman and a locally pinned image. If absent or UNKNOWN,
`status=BLOCKED` and **no host agent fallback**. The automatic public CLI
`executor-doctor` / `execute-current` is not available until PH-051-09.
See `docs/Project_Harness_Documentation_v0.5.1/05_Updates/07_Rootless_Podman_Sandbox_v0.5.1_WIP.md`.

## PH-051-04 optional Python API (v0.5.1 WIP)

`project_harness.execution_roots.prepare_execution_root(project_root, runtime_root, run_ref=...)`
constructs the exact current reserved Run's disposable product/control/output
folders under an *explicit absolute external runtime root*. It does not invoke
Podman/Codex or enable automatic execution. See `PH_051_04_TEST_REPORT.md` and
the versioned `05_Updates/08_Disposable_Execution_Root_v0.5.1_WIP.md`
for the scoped contract and baseline check; real rootless Podman acceptance
remains **NOT RUN** in the build environment.

## PH-051-05 exact Local Codex adapter (0.5.1 WIP)

`CodexCliLocalAdapter.from_project(root)` reads pinned ACTIVE ADP/SBX profiles
from project-local exact revisioned records and the `PROJECT_LOCK` SHA-256
bindings. `prepare_current_run(runtime_root)` returns the current JIT argv and
Podman sandbox request; `execute(argv, request)` never launches a host agent
and refuses missing/unsafe Podman. This is an **internal Python integration
slice**, not a supported public automatic workflow. Current manual PROJECT_LOCK
cannot silently opt in. Physical Podman verification and real Codex CLI flags
were NOT TESTED here. Full strict interfaces/limits and targeted tests are in
[PH-051-05 WIP note](docs/Project_Harness_Documentation_v0.5.1/05_Updates/09_Local_Codex_CLI_Adapter_v0.5.1_WIP.md).
`execute-current` and `executor-doctor` remain reserved for PH-051-09.

## PH-051-06 Agent Result and secret-bound environment (0.5.1 WIP)

The internal bound adapter can now validate the exact, pre-created `0600`
`/output/agent-result.json`, persist kernel-owned immutable ART metadata and
redacted/bounded logs, and reject link/type/size/schema/Run mismatch and
any literal secret echo. Only `ENV:NAME` pinned ADP references are resolved;
missing refs block before Podman. No raw credentials are saved in project
records. Exit 0/agent `COMPLETED` is **not** independent verification/apply.

Tests from source: `PYTHONPATH=src:. python -m unittest -v
 tests.test_ph_051_06_result_channel` (on a single line if copied). See
[PH-051-06 operator note](docs/Project_Harness_Documentation_v0.5.1/05_Updates/10_Exact_Result_Channel_v0.5.1_WIP.md).
Rootless Podman integration was not performed on this host. CLI remains manual
`next → verify → complete`; `execute-current`/`executor-doctor` remain PH-051-09.
