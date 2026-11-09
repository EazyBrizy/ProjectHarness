# PH-LW-11 — Один Windows-запуск: launcher, self-contained installer и resume

**Статус промпта:** задание на реализацию; результат ещё не реализован.

## Общий обязательный контекст

Это задача реализации только указанного этапа, не предложение нового аудита вместо изменений. Вход для PH-LW-01: текущие Engine + Documentation **WIP snapshots, сформированные по результатам попытки приёмки PH-051-12 с решением NO-GO**, вместе с `PH_051_12_TEST_REPORT.md`; это не успешно принятый релиз. Для PH-LW-02…12 используй последнюю пару ZIP предыдущего PH-LW и его отчёт, сохраняя происхождение от указанной WIP-базы. Прочитай `IMPLEMENTATION_PLAN_RU.md`, `SOURCES_AND_BASELINE.md` и неизменные спецификации v0.5.0/v0.5.1. Сначала проверь входные SHA-256/manifests, фактические результаты применимых тестов и выпиши допустимые изменения. Не возвращайся к старой базе только из-за одинаковой версии имени.

**Условие продолжения:** закрытие полного release gate PH-051-12 не является prerequisite разработки отдельного Local Web manual companion. Известные blockers — отсутствие фактической rootless Podman security acceptance и отсутствие положительного governed per-Run egress — остаются открытыми; релиз v0.5.1 в полном объёме остаётся NO-GO / NOT RELEASED. Это не разрешает automatic execution и не освобождает manual/preparation от собственных проверок. Новые или унаследованные ошибки в используемых manual/preparation API, governance, целостности данных или изоляции маршрутов являются blockers соответствующего PH-LW; их нельзя списывать на известный automatic NO-GO. При отсутствии Windows фиксируй NOT RUN, без утверждения о Windows-готовности.

Цель серии — native Windows, локальный браузерный мастер, manual GPT/Codex handoff. Не добавляй provider API, remote control plane, Git/PR/deploy, второй sandbox/adapter или терминал в браузере. Не разрешай automatic execution и не закрывай прежний NO-GO Podman/egress. Не меняй accepted scope, последовательность уровней, core statuses, immutable history, evidence semantics и обязательные согласования ради UI.

Web routes вызывают application service и поддержанные Python API; не правят `.harness` напрямую. Небольшой недостающий API допустим только внутри указанной области, с validation/replay tests и документацией. Проверяй unknown fields, пути, stale revisions, concurrency и отказ до mutation. GET/polling ничего не создают и не запускают.

Для завершения этапа внеси код/тесты/docs в разрешённых границах, запусти целевые позитивные/негативные проверки и доступную предыдущую regression suite; явно раздели PASS/FAIL/NOT RUN/platform-specific. Mock Windows/Podman не равен реальному прогону. Синхронизируй source, package resources, wheel, embedded/standalone docs, не оставляй устаревший build/lib.

Верни два полных ZIP `Project_Harness_Engine_v0.5.1_PH_LW_NN.zip` и `Project_Harness_Documentation_v0.5.1_PH_LW_NN.zip`, заменив NN номером этапа, а также `PH_LW_NN_CHANGED_FILES.md`, `PH_LW_NN_TEST_REPORT.md`, фактические logs, сохранённые инварианты и внешние SHA-256. Все новые ограничения и невыполненные проверки фиксируй честно. Не переписывай исторические отчёты. Промежуточная готовность UI не является GO всей v0.5.1.

## Точная область PH-LW-11

Windows launcher/packaging/build scripts, resource discovery, lifecycle/single-instance, installer docs и реальные Windows tests. Не добавлять auto-update cloud service или automatic installation of WSL/Podman.

Упакуй работающий Local Web так, чтобы конечный пользователь не устанавливал Python/Node, не создавал venv и не распаковывал Engine/Documentation вручную.

### Требуется

1. Выпусти реальный `Harness-Setup-win-x64.exe` с frozen application/runtime, всеми dependencies и локальными static/docs/schema/registry assets. Используй один зафиксированный в PH-LW-01 build pipeline; default PyInstaller onedir + per-user installer. Не заменяй EXE файлом `.ps1`, HTML-макетом или ZIP с просьбой пользователю собрать всё самому.
2. Установка обычным пользователем в отдельный app directory; project/app state отдельно. После завершения автоматически открыть launcher/web wizard. Первый экран сразу объясняет MD/ZIP upload и «нет документации». Повторный `Harness.exe`/ярлык открывает последнюю session/project, не создаёт новый intake и не теряет approvals.
3. Один server instance на пользователя: OS-level mutex/lock и authenticated local handshake. Второй запуск открывает существующий процесс безопасно, не доверяет произвольному listener на ожидаемом порту. Порт резервируется реальным bind, другой процесс на порту не убивается. Auth bootstrap не пишется в обычные логи.
4. Без browser/default handler — понятное локальное сообщение и безопасный путь открыть UI вручную. Closing browser не приравнивай к cancellation; «Завершить Harness» проходит drain/check активных mutations и clean stop. Не оставляй бесконтрольные orphan server процессы. Не обещай отменить уже committed kernel action.
5. Проверка целостности package до активации, staged install/version switch, recovery interrupted setup и disk-full. Не перезаписывай live product или `.harness`; uninstall по умолчанию сохраняет проекты и отдельно объясняет app-data cleanup. Не меняй PATH/firewall/ExecutionPolicy без необходимости; не выключай Defender/SmartScreen/UAC. Реальная подпись при наличии signing credentials, иначе честный unsigned status, без обещания отсутствия OS warnings.
6. Работа подготовки после установки offline; не `pip install latest` на машине пользователя, не CDN. Core CLI продолжает работать отдельно. `distribution_root()`/package resources и frozen executable не должны зависеть от CWD/source repo. Не использовать launcher как Python interpreter продуктовых команд.
7. Подготовь reproducible Windows build recipe/CI и список dependency versions/hashes/licenses. Developer CI может иметь Python/packager; это не требование конечному пользователю. Source+wheel+frozen assets byte/contract согласованы.

### Реальная приёмка

Windows 11 x64 VM/host, non-admin, без Python/Node/Podman/WSL на PATH: install→browser→MD import→GPT fixture roundtrip→approvals→project/JIT; затем restart, second launch, port collision, Unicode username/path, offline, readonly/disk-full/interrupted installation. Проверить no external app requests и сохранность проектов при uninstall.

Если нет Windows builder, отдай source/build automation и два ZIP с **WINDOWS_BINARY_NOT_BUILT / NOT_TESTED**. Не создавай фиктивный EXE и не ставь GO. При реальной сборке приложи installer дополнительно к двум ZIP, его SHA-256 и реальные installation/browser logs. Сам build success не заменяет clean-machine test.
