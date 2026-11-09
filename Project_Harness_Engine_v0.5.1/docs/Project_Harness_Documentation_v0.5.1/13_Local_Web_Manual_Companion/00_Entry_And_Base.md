# PH-LW-01: статус, точная база и границы

**Версия:** 0.5.1-WIP  
**Дата:** 2026-10-25  
**Этап подготовки:** PH-LW-01, 2026-11-01  
**Статус:** CONTRACT DESIGN / NOT IMPLEMENTED / NATIVE WINDOWS NOT RUN

## База и решение

Этот дополнительный документ не изменяет нормативные спецификации v0.5.0/v0.5.1. Нормативный порядок: спецификации v0.5.0/v0.5.1 → фактические публичные контракты Engine → Windows Local Web plan r2 → документация companion. Исходные SHA-256 входа зафиксированы внешним `PH_LW_01_TEST_REPORT.md` и `src/project_harness/resources/local_web/metadata_v1.json`.

- Запрошенная база из `SOURCES_AND_BASELINE.md`: Engine `c4bd7bd446f926f32ccfe185fe89ede27207ca6ef0998a35ba3c971293b91174`, Documentation `3a5eee4fac314b5ecaec2edb338d64dd26ecddecc3d0e9212fdeff62ca88209a`; её отчёт `PH_051_12_TEST_REPORT.md` не предоставлен.
- Фактическая база для данного артефакта: оба ZIP `PH_051_11`; Engine `44b75136131d917403b99299077e829c025783a6bb94c2b539fbe0b913449dbd`, Documentation `17ab78d0412c713fabf957bd54e7cc65d0b8dc77d358fe0d7f9f2635bca172fd`. CRC и все записи исходных manifests проверены.
- Нельзя отождествлять эту сборку с PH-051-12 NO-GO snapshot по сходному `0.5.1` имени, переносить его историю, статистику тестов либо утверждать, что его изменения присутствуют. Требование exact-base provenance **открыто** до сверки реального PH-051-12 набора.
- Полная v0.5.1 WIP/NOT RELEASED/NO-GO. `LOCAL_WEB_MANUAL` также не является GO: здесь контракт/fixtures, ни Web server, ни installer, ни real Windows evidence ещё не реализованы. Real rootless Podman и governed positive egress не подтверждены; они не становятся принятыми через UI.

## Что включено, что не включено

Включены additive контракт, строго ограниченные два shell-namespace JSON Schema, карта 26 CLI/API routes, dependency/config fixtures, Windows CI entrypoint с честным отказом на других ОС и тесты карты. Не добавлены Flask route handlers, оконный интерфейс, локальный background server, новый executor, automatic execution, web-based approvals, remote provider, shell/terminal, deployment, Git/PR. Production ядро и принятые project state/evidence schemas не меняются.

## Навигация

1. [Windows архитектура, зависимости, установщик и каталоги](01_Architecture_Runtime_Installation.md)
2. [Карта 26 действий, API и test IDs](02_Control_Map_26_Commands.md)
3. [GPT draft, отдельные согласования и журналы](03_Draft_Approvals_Journal.md)
4. [HTTP/ZIP/Windows threat model](04_Threat_Model_And_Consent.md)
5. [Acceptance/CI/Windows matrix](05_Acceptance_CI_Baseline.md)
6. [Golden fixtures и правила генерации](06_Golden_Fixtures.md)

Machine-readable control map: `src/project_harness/resources/local_web/control_map_v1.json` (Engine source/package resource). Это проектные интерфейсные DTO, не подмена core registry/schema и не доступный web API.
