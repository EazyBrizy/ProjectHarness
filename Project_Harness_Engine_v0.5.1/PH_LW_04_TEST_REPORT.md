# PH-LW-04 — тестовый и security отчёт (фактическая сборка)

**Дата:** 2026-11-03. **Результат реализации:** исходники локального Flask/Waitress HTTP shell + one-time session + local assets внесены, wheel/документация собраны. **Security acceptance PH-LW-04: NOT COMPLETE / NO-GO. Полный релиз v0.5.1: NO-GO / NOT RELEASED.** Реальные HTTP/Waitress/browser и Windows 11 x64/NTFS проверки не выполнены; нельзя называть локальный UI production-ready.

## 1. Фактическая среда / provenance

- Среда сборки: Linux, Python 3.13.5; native Windows 11 x64/NTFS **отсутствует**.
- Входные ZIP: Engine PH-LW-03 SHA-256 `586ea587afa47bf787861c577480762547f36ff8849374917a3911a8ef3d3860`; Documentation PH-LW-03 SHA-256 `e7adc0ab63bb86c0a798398f6deef38fecc848941c3fabe5e9afd0dbd1c18510`. Оба `ZipFile.testzip` и входные SHA-256 manifest проверки: **PASS** (1000/1000 Engine; 141/141 Documentation).
- Нормативные спецификации: v0.5.0 `ca487d3e978af116418a597b5d05cd890d11e2e93855c9f7a312e21f083dd16f`, v0.5.1 `91413b977ecf9f3143e0808bbd3e96bae1aef1b4d50a90420dc1495dc82c497e`; исходный ZIP нормативной базы не изменён.
- Опциональные Flask==3.1.3 и Waitress==3.0.2 **не установлены**, попытка `pip install` с закреплёнными версиями завершилась ненулевым кодом (нет доступного package index), см. `PH_LW_04_LOGS/PINNED_HTTP_DEPENDENCIES_INSTALL.log`. Никакой mocking не может компенсировать отсутствие real listener.

## 2. Реализовано строго в границе PH-LW-04

- `project-harness ui [--app-data PATH] [--no-browser]` через lazy launcher; Waitress на заранее связанном IPv4 `127.0.0.1:0`, без development server/reloader/0.0.0.0, консервативные WSGI limits. Browser open только после успешного prebind/server creation; токен не показывается stdout.
- Session bootstrap — 256-bit CSPRNG, SHA-256 storage, 90s TTL, single-use, HTML fragment + immediate `history.replaceState`, HttpOnly SameSite=Strict host-only cookie, серверные 8h/30min session TTL, CSRF; Host+порт, Origin, content type/JSON, security headers/CSP, no generic files/shell.
- Только перечисленные authenticated project/status/operation/artifact routes; existing PH-LW-03 LocalWebService enforcement, read-only catalog, artifact owner/path/digest checks. Несуществующие UI действия отключены; нет auto-run.
- Русская доступная browser shell и локальные CSS/JS/HTML из wheel. Без Node/npm/CDN/telemetry для работы.
- Windows native security script подготовлен, но **НЕ ВЫПОЛНЯЛСЯ**.

## 3. Test matrix — факты, а не план

| Проверка | Фактический результат | Evidence / комментарий |
|---|---|---|
| Входные ZIP CRC и manifests | **PASS** | Engine 1000/1000, Docs 141/141 на входе PH-LW-03 |
| PH-LW-01–04 targeted suite: `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:. python -m unittest -q tests.test_ph_lw_01_contract tests.test_ph_lw_02_windows_core tests.test_ph_lw_03_service tests.test_ph_lw_04_http` | **53 tests, 13 SKIP, 0 FAIL** | `PH_LW_04_TARGETED_COMBINED_AFTER_FIX.log`; пропуски Windows и Flask/Waitress/browser — не PASS |
| Final packaged Engine ZIP, **unzip + 53 targeted tests + source doctor** | **PASS with 13 SKIP** | `PH_LW_04_LOGS/EXTRACTED_ENGINE_ZIP_SMOKE.log`; проверка реальных распакованных bytes, без работоспособного Flask/Waitress |
| Final PH-LW-03 + PH-LW-04 tests | **30 tests, 11 SKIP, 0 FAIL** | `PH_LW_04_TARGETED_FINAL.log` |
| PH-LW-04 HTTP suite | **15 tests: 5 PASS / 10 SKIP** | `PH_LW_04_TARGETED_INITIAL.log`, `PH_LW_04_TARGETED_FINAL.log` (HTTP cases пропущены) |
| Existing regression modules individually (bounded, before final missing-dependency negative test) | **31 / 34 PASS, 3 TIMEOUT, 0 FAIL** | По `PH_LW_04_LOGS/REGRESSION_MODULES/MATRIX.json`, подробные per-module logs. Exit=0 может включать skipped; TIMEOUT не PASS |
| Full monolithic `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:. python tests/run_tests.py` | **TIMEOUT** | 240s process timeout, `PH_LW_04_FULL_REGRESSION.log`; полного PASS нет |
| Python syntax + JS `node --check` | **PASS** | Static compilation/AST; `JS_SYNTAX.log` (0 exit) |
| Offline built wheel `python -m pip wheel --no-deps --no-build-isolation --no-index --wheel-dir dist .` | **PASS** | `WHEEL_BUILD.log`, wheel SHA-256 в external manifest |
| Wheel install in independent `python -m venv`, `pip install --no-index --no-deps <wheel>` | **PASS** | `WHEEL_INSTALL.log` |
| Installed wheel `project-harness doctor`, `--version`, UI package files/extras, `ui --help` | **PASS** | `WHEEL_SMOKE.log` (assets index.html/app.css/app.js; Flask/Waitress optional pinned extras) |
| Installed wheel `project-harness ui --no-browser` without pinned deps | **Expected fail-closed (exit 2)** | `WHEEL_UI_FAIL_CLOSED.log`; это не real HTTP listener PASS |
| Standalone docs aggregate, manifest + actual Docs ZIP CRC/tree | **PASS** | `DOC_AFTER_ZIP.json` (`errors=[]`, `warnings=[]`, 142 hashes, 143 ZIP members) |
| Flask test-client auth/Host/Origin/CSP/CSRF/path/XSS negative cases | **NOT RUN** | Flask not installed; 10 skipped HTTP-dependent cases counted above |
| Real Waitress WSGI body/connection limits, network binding, LAN non-reachability | **NOT RUN** | Waitress unavailable; no HTTP server activated |
| Playwright actual browser HTTP/fragment/CSP/no external requests/XSS | **NOT RUN** | Browser test needs live Flask/Waitress; Playwright alone insufficient |
| Windows 11 x64 NTFS / Microsoft Edge / real installed Windows wheel | **NOT RUN / WINDOWS_NOT_TESTED** | Windows host unavailable; `ci_ph_lw_04_windows.ps1` not run |
| Rootless Podman isolation and governed positive per-Run egress | **NOT RUN / PRE-EXISTING NO-GO** | Outside PH-LW-04; not treated as a new success |

### Not fully green regression modules

- `test_gate_evidence_contract`: **TIMEOUT** after 55.06s in bounded individual run; contents in per-module log; no assertion of successful coverage.
- `test_maintenance_lifecycle`: **TIMEOUT** after 55.07s in bounded individual run; contents in per-module log; no assertion of successful coverage.
- `test_ph_f06_maturity_lifecycle`: **TIMEOUT** after 55.06s in bounded individual run; contents in per-module log; no assertion of successful coverage.

## 4. Финальные ограничения, решающие acceptance

**NO-GO для PH-LW-04 HTTP security gate:** real pinned Flask/Waitress and browser security verification не выполнены; Windows native session/NTFS, LAN reachability, exact Host/Origin behaviour и production package install на Windows остаются недоказанными. Native Windows PowerShell test script приложен как воспроизводимый runbook, но его наличие не служит доказательством исполнения. Manual Python/CLI PH-LW-03 остается доступным, automatic Codex по умолчанию запрещен. Дополнительно сохраняются старые NO-GO v0.5.1 из PH-051-12 — Podman security и положительный governed per-Run egress.

Позитивные выводы ограничены реально выполненными dependency-independent tests, core-regressions, установленным wheel, CLI doctor и документационным ZIP validator. Тестовые patched imports используются **только для проверки fail-closed import path**; реальные HTTP/Windows проверки не подменялись mock PASS. Все новые limitations и preserved invariants перечислены в `PH_LW_04_PRESERVED_INVARIANTS.md`.

## 5. Как воспроизвести обязательную проверку до GO

На реальном Windows 11 x64 NTFS с доступным утверждённым Python 3.14 x64, установленными pinned Flask/Waitress, Microsoft Edge/Playwright: `powershell -ExecutionPolicy Bypass -File .\local_web\ci_ph_lw_04_windows.ps1 -DocumentationZip <path-to-updated-Documentation-ZIP>`. Он выполнит фактические HTTP/security/browser tests и сохранит transcript. При непрохождении или SKIP обязательных этапов ставить NO-GO, не переписывать этот исторический отчёт. В текущей Linux среде этот script **не запускался**.
