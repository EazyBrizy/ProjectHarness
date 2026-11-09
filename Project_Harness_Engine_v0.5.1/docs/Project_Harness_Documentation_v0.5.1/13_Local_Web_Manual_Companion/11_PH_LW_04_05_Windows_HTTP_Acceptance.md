# PH-LW-04 и PH-LW-05 — Windows HTTP приёмка

**Версия:** 0.5.1-WIP  
**Дата:** 2026-10-25  
**Дата Windows-приёмки:** 2026-11-07  
**Build:** `PH-LW-05-WINDOWS-RETEST-20261107`. Полная v0.5.1, `LOCAL_WEB_MANUAL` и `AUTOMATIC_EXECUTOR` остаются **NO-GO / NOT RELEASED**. PH-LW-06 не реализуется этим исправлением.

## Точная область и история

Повторная приёмка выполнена на предоставленной паре PH-LW-05. Исходные `PH_LW_04_TEST_REPORT.md` и `PH_LW_05_TEST_REPORT.md` сохранены: их Linux/NOT RUN результаты относятся к прежним bytes. Текущие команды, exits, skips, regressions и отдельные verdicts находятся в новом Engine `PH_LW_04_05_WINDOWS_ACCEPTANCE_TEST_REPORT.md`; hashes финальных ZIP — во внешнем `PH_LW_04_05_WINDOWS_ACCEPTANCE_SHA256.txt`.

Исходный Engine SHA-256: `d247127b5ab91b1dffd0f1f0649225bcf2b0bf02abea85a3c211cf3580b40c76`; Documentation: `fd6a5d2aff1495708c30cf4f493ef30aed5bc6095a84a2fcd00e4a984013f1df`. Внешние контрольные суммы входной пары не предоставлены; CRC и полные внутренние manifests проверены. Lineage PH-051-11 и прежние automatic blockers не меняются.

## Исправленные поведения

- Авторизованный GET обзора принимает `project_id` и возвращает read-only status вместо HTTP 500.
- Некорректный тип action и не-ASCII CSRF отклоняются структурированно, до изменения проекта.
- `LocalWebService.submit(..., check_current=True)` возвращает exact ранее записанный receipt до проверки нового состояния. Новые HTTP requests по-прежнему проверяют текущую доступность и fingerprint; worker повторяет проверку под OS guard. Изменённый payload/fingerprint с прежним key остаётся conflict.
- Scalar multipart fields `mode`, `expected_fingerprint`, `expected_source_revision` должны присутствовать ровно один раз. Поле `files` сохраняет разрешённую множественность.
- Snapshot/ledger reads проверяют Windows ancestors, включая `imports` и `snapshots`; обычный GET не создаёт каталогов и не выполняет recovery. Persistent NTFS junctions и hardlinks отвергаются.
- Raw ZIP ограничен upload budget 64 MiB, каждый Markdown и распакованная entry — 8 MiB. Законный ZIP с несколькими entries и общим raw size больше 8 MiB теперь принимается. Hash/provenance/replay проверки сохранены.
- После импорта, замены и создания intake UI снова включает доступные source actions. «Документации нет» не требует обходного refresh.
- Общая Stage transaction сохраняет fsync на Windows через write-capable descriptor. Ошибка flush не подавляется; journaling, recovery и approvals не изменены.
- Windows fixtures сохраняют опасные ZIP filename bytes и используют platform-independent компоненты путей для fault injection.

## Реальная проверочная среда

Windows 11 Pro x64, build 26200, локальный NTFS, non-admin; CPython 3.14.10 x64. Flask 3.1.3 / Waitress 3.0.2 и транзитивные runtime packages установлены из прежнего lock с проверкой hashes. Edge 157.0.4341.42 / Playwright 1.64.1 используются только для разработки и приёмки.

Production launcher и acceptance используют одну конфигурацию `create_loopback_server`: предварительный bind `127.0.0.1`, Waitress 64 MiB body / 16 KiB headers / 32 connections / 20 s idle. Тесты проверяют реальную передачу chunked bytes, multipart, HTTP replay/restart, браузерный import/preview/replace/no-doc, Host/Origin/CSRF, чужой browser origin и отсутствие внешней загрузки документов. Конкретный успешный/неуспешный исход каждого запуска определяется отчётом, не наличием теста.

## Команды оператора

Из Engine root, в обычном Windows PowerShell 5.1 или PowerShell 7:

```powershell
.\local_web\ci_ph_lw_04_windows.ps1 -PythonExecutable C:\path\venv\Scripts\python.exe -DocumentationZip C:\path\Documentation.zip
.\local_web\ci_ph_lw_05_windows.ps1 -PythonExecutable C:\path\venv\Scripts\python.exe -DocumentationZip C:\path\Documentation.zip
```

Прямой `python.exe` не получает `-3.14`; для `py` этот version selector выбирается автоматически. Скрипты не требуют обхода execution policy, inline Python quoting или изменения системных настроек. `-LogDirectory` позволяет сохранить evidence вне исходного дерева. `-SkipRegressions` явно записывает NOT RUN для полного regression набора **в этом запуске**; отдельная regression matrix обязательна для совокупного verdict. Mandatory stage suite с skips не может получить PASS. Логи не должны содержать bootstrap/session secrets или реальные документы пользователя.

## Границы доказательства

Эта среда содержит инструменты разработчика; она не заменяет clean-machine installer test PH-LW-11/12. Tests с подготовленным core fixture не считаются прохождением отсутствующих UI approvals/GPT/lifecycle экранов. Permanent-link rejection и проверка digest во время копирования не являются доказательством OS sandbox или защиты от произвольного вредоносного процесса с теми же правами. Power-loss durability и полный installer/recovery цикл остаются отдельными gates.

Ближайший новый функциональный этап — [опрос и GPT exchange](02_Control_Map_26_Commands.md), но его выполнение требует отдельного задания PH-LW-06. Нормативные specs, strict contracts, отдельные approvals и принятая история не изменены.
