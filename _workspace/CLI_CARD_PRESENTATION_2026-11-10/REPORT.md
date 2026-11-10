# Рабочая область и карточка CLI

Дата: 2026-11-10. Выполнены все изменения представления из задания пользователя:

- «Опрос и GPT» занимает всю доступную ширину с сохранением навигации и обычных отступов; max-width других разделов не меняется.
- Кнопки CLI находятся в одной строке. Основная кнопка — «Анализировать через CLI».
- Подключённый CLI: кнопка «Подключено» с зелёной галочкой, инструкция подключения скрыта. Повторная проверка по нажатию сохранена. При ошибке показаны реальные сообщение/состояние, снова доступна инструкция.
- Удалена пустая стартовая подсказка «После запуска результат анализа появится здесь, без скачивания пакета и копирования JSON.». Реальные сообщения активного/завершённого анализа и ошибок сохранены.
- Внизу карточки текст «На выполнение расходуются токены агента.» серым шрифтом 12px.

Build `CLI-CARD-PRESENTATION-20261110` установлен по стандартному пути, обычный desktop shortcut обновлён. Данные и предыдущая версия сохранены. Новых подтверждений и local login нет.

## Scope и изменения

Только index.html, app.css, renderCliState в interview.js и build metadata: [baseline/allowed changes](INPUT_BASELINE.json), [diff](SOURCE_DIFF.patch), [input/output hashes](CHANGED_FILE_HASHES.json). До изменений проверены source/docs/manifests и полный frozen payload включая .pyd. Backend/CLI process logic, HTTP/API, packs, schemas/registries/core и test files не менялись. Чужие изменения сохранены. Добавлена [глава 32](../../Project_Harness_Documentation_v0.5.1/13_Local_Web_Manual_Companion/32_CLI_Card_Presentation.md), прежние docs/reports сохранены.

## Только целевая проверка

Один presentation run в настоящем headless Edge/TCP, final installed wheel из независимой venv вне source tree, пустой PYTHONPATH. Windows 11 x64 / CPython 3.14.10, Flask 3.1.3 / Waitress 3.0.2 / Playwright 1.64.1. Package inventory совпал с final source. [Команда/interpreter/exit/log hash](visual-check.run.json), [среда/geometry/states](VISUAL_RESULT.json), [log](visual-check.log).

1920/1360/1024/390 CSS pixels: рабочая область заполняет main, main занимает всю доступную ширину после sidebar, кнопки остаются в одной строке и внутри карточек, horizontal overflow отсутствует. На 1920 ширина main 1665px, panel 1555px после стандартных отступов. Проверены disconnected label/help, hidden idle status, exact note; затем connected label/green check/hidden help, reload без новых probes, failed recheck с восстановлением инструкции. JS errors/dialogs 0. **PASS.** В connection шагах использован явно обозначенный FixtureCli; настоящий CLI/провайдер не запускались, analysis/model requests 0. Новые formal regression tests не добавлялись, прежние workflow suites повторно не запускались.

Снимки просмотрены визуально: [подключённый CLI, 1920](output/playwright/connected-1920.png), [до подключения, 1360](output/playwright/disconnected-1360.png), [узкий экран](output/playwright/disconnected-390.png). Рабочие сообщения анализа не заменены пустым placeholder: сообщение выводится при наличии job_id, скрывается только пустое состояние.

Docs validator PASS / 0 errors, ожидаемый WARN без ZIP: [log](docs-validator.log). Source/build/wheel/frozen bytes, CRC wheel, docs mirrors/manifests, весь frozen payload включая .pyd и allowed scope / unchanged tests — PASS: [integrity](INTEGRITY.json). Frozen/UNSIGNED installer собраны из canonical src: [build result](BUILD_RESULT.json), [build run](frozen-build.run.json).

Приложение остановлено штатным public POST, без force kill: [stop](STOP_FOR_UPDATE.json). Operator upgrade PASS, hashes app-data/project roots до/после одинаковы; предыдущая версия сохранена; --check-package и --doctor exit 0: [upgrade](OPERATOR_UPGRADE.json), [native installer log](installer-native.log), [ярлыки](SHORTCUTS.json). Видимый браузер не открывался.

## Exact bytes и ограничения

Source digest `sha256:d4776d5f0db1ddbdd96e6bc21df4d7ea15a1c505d254664325c97b5d7c344d7e`. Wheel SHA-256 `8dab80854d87e0c6197a65bb082a0f8724fc29c29878ca7292a809a3e9a2bea2`. UNSIGNED installer SHA-256 `fbca7a11cc074f7fea622fb3f24aec99f2877fc9337653e2db0b770649ef85f2`. Полные source/docs inventories — [freeze](RUNTIME_FREEZE.json), hashes evidence — [index](EVIDENCE_INDEX.json).

Full engine/core regression, полная PH-LW matrix, повторный CLI/model analysis и actual installed-EXE browser reacceptance **NOT RUN**: scope этой правки только представление. Installed EXE подтверждён по bytes/package/doctor, browser evidence — final installed wheel. Старые PH-LW/LOCAL_WEB_MANUAL verdicts остаются в своих exact-byte границах. Automatic Task executor disabled / прежний NO-GO; полная v0.5.1 NOT RELEASED. ZIP не создавались, другие этапы не включались.

Следующий разрешённый шаг: открыть Harness через прежний ярлык → «Опрос и GPT». Другие этапы и широкие проверки не выполнять.
