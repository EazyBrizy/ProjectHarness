# Два способа анализа в одной строке

Дата: 2026-11-10. Задание пользователя — разместить «Автоматически через Codex CLI» и «Вручную через ChatGPT или Codex» рядом в блоке «1. Выберите способ анализа документов».

Готово: две равные колонки с общим заголовком. На экранах ≤760 CSS pixels — одна колонка; кнопки и текст переносятся внутри карточки. Проверка снимков выполнена визуально. [Широкий экран](output/playwright/1360.png), [промежуточный](output/playwright/1024.png), [узкий](output/playwright/390.png).

Изменены только wrapper в index.html, четыре CSS rules для этой группы и build metadata. JavaScript, CLI connection/analysis, содержимое пакетов, API, schemas/registries, core и tests не менялись. [Baseline и разрешённые файлы](INPUT_BASELINE.json), [diff](SOURCE_DIFF.patch), [input/output hashes](CHANGED_FILE_HASHES.json). Входные source/docs/manifests и полный frozen payload включая .pyd проверены до изменений; чужие изменения и старые отчёты сохранены.

## Проверено только изменённое

Один visual-check, 3 viewport: 1360/1024 — карточки рядом с общей верхней границей; 390 — одна колонка. Все кнопки внутри карточек, horizontal overflow отсутствует, page errors/dialogs — 0. Настоящий TCP/headless установленный Edge, независимый installed wheel вне source tree с пустым PYTHONPATH; package inventory совпал с final source. Команда, среда, зависимости и geometry: [run](visual-check.run.json), [log](visual-check.log), [результат](VISUAL_RESULT.json). Формальные regression tests для этой малой правки не добавлялись и не запускались; model/CLI analysis повторно не вызывался.

Docs validator — PASS, 0 errors, ожидаемый WARN без ZIP: [log](docs-validator.log). Standalone/embedded/frozen docs побайтово совпали, manifests/wheel CRC/source-build-frozen equality/package payload including .pyd — PASS: [integrity](INTEGRITY.json). Проверка scope подтверждает изменение только трёх разрешённых source files, unchanged tests и сохранение старой документации; добавлена [глава 31](../../Project_Harness_Documentation_v0.5.1/13_Local_Web_Manual_Companion/31_Analysis_Options_Row.md).

Frozen/UNSIGNED installer собраны из canonical src: [build result](BUILD_RESULT.json), [команда](frozen-build.run.json). Приложение завершено штатным public POST без force kill: [stop](STOP_FOR_UPDATE.json). Новая версия установлена по стандартному пользовательскому пути; данные и предыдущая версия сохранены; --check-package/--doctor exit 0, видимый браузер не запускался: [upgrade](OPERATOR_UPGRADE.json), [native installer log](installer-native.log), [ярлыки](SHORTCUTS.json).

## Exact bytes и границы результата

Build `ANALYSIS-OPTIONS-ROW-20261110`. Source digest `sha256:d9df0cab22d90d65b991e38f1f8ac9a6fdac4ea8c6aaf532f1d362bd9fb5b1a0`. Wheel SHA-256 `e56466460d71e48e909b9d3af89dabe8343b44d6e285e9cedc9314bc94650ff5`. UNSIGNED installer SHA-256 `ef365d79c60d474cf4548f304e3fc85b01a3b7200cf0f443055b612b83ac5967`. Полные source/docs inventories — [freeze](RUNTIME_FREEZE.json); evidence hashes — [index](EVIDENCE_INDEX.json).

Full engine/core regression, CLI workflow tests, model analysis, полная PH-LW matrix и actual installed-EXE browser reacceptance NOT RUN: scope только размещение карточек. Installed EXE проверен по bytes/package/doctor; визуальное evidence — final installed wheel. Это не новый полный PH-LW или LOCAL_WEB_MANUAL verdict. Их прежние GO сохраняют exact-byte границы. Automatic Task executor disabled / прежний NO-GO, full v0.5.1 NOT RELEASED. ZIP не создавались.

Следующий разрешённый шаг: открыть Harness через прежний ярлык → «Опрос и GPT»; карточки способов анализа находятся рядом. Другие этапы и широкие проверки не выполнять.
