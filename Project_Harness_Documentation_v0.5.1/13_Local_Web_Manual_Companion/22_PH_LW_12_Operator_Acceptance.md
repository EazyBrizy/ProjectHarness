# PH-LW-12 — операторский маршрут и финальная приёмка

**Версия:** 0.5.1-WIP / NOT RELEASED  
**Дата:** 2026-10-25 (база документации v0.5.1)  
**Дата дополнения:** 2026-11-08

Эта глава описывает существующие элементы Local Web manual companion. Фактические verdicts, builds, команды и ограничения находятся в новых `PH_LW_12_TEST_REPORT.md`, `PH_LW_12_CHANGED_FILES.md` и `PH_LW_12_LOGS/` Engine. Наличие installer не означает успешную приёмку. Предыдущие главы и отчёты сохраняют статусы своих checkpoints.

## Первый запуск

Запустите `windows/Harness-Setup-win-x64.exe` под обычной учётной записью Windows 11 x64 на локальном NTFS. Installer устанавливает runtime, Flask/Waitress, assets, schemas, registries и документацию для текущего пользователя. Комплект UNSIGNED. Python/Node/WSL/Podman для запуска оболочки не требуются; необходимые продукту инструменты устанавливаются отдельно оператором. Не изменяйте ExecutionPolicy, firewall, LongPathsEnabled или другие защитные настройки ради проверки.

Следующие старты — ярлык или `Harness.exe`. Второй обычный запуск подключается к своему действующему серверу. Не закрывайте незнакомый listener и не завершайте чужие процессы. Если браузер не открылся, используйте локальный адрес и одноразовый код из окна Harness: поле «Одноразовый код» → «Войти по локальному коду». Код и session/CSRF нельзя пересылать или включать в отчёт. `Harness.exe` не является универсальным Python interpreter.

В данной рабочей сессии действует указание пользователя не открывать новые видимые browser windows: автоматические browser regressions работают в headless Edge. Свежая проверка normal second launch с открытием default browser имеет отдельный статус; `--no-browser` не объявляется её заменой.

## Документы, опрос и GPT

Откройте «Документы», введите имя, нажмите «Создать intake для документов». Загрузите MD либо ZIP с MD. Сверьте counts принятых и пропущенных файлов, причины и source revision. Предпросмотр — безопасный текст; HTML, внешние изображения и инструкции внутри AGENTS.md не выполняются. Недопустимый ZIP отвергается целиком; повтор одинаковых bytes не создаёт новую revision. Для замены источников используйте явное действие, затем заново рассмотрите invalidated draft/approvals.

При отсутствии документов выберите «Документации нет». Это осознанное отсутствие источников, не успешный анализ требований. В «Опрос и GPT» заполните известные ответы и target, сохраните их. UNKNOWN/UNSURE и существенные gaps не становятся READY автоматически. Навигационная запись resume завершается перед новым пользовательским JSON POST, чтобы её собственная app-data блокировка не конфликтовала с admission. POST не повторяется автоматически.

«Проверить состав пакета» показывает документы и draft для передачи. Установите фактическую sensitivity каждого элемента и отдельно подтвердите право передачи. Создайте пакет, скачайте его и передайте внешнему GPT вручную. Сервер не вызывает provider API. Импортируйте draft-only ответ, рассмотрите preview/diff и примените. Wrong project/export/revision, неизвестные поля, `approved:true`, AUTO/egress и неподдержанные пути отвергаются до mutation. После изменения sources нужен новый пакет. Fixture roundtrip тестирует протокол, а не интеллект модели.

## Отдельные approvals и папка проекта

В «Согласования» укажите actor и рассмотрите каждый subject отдельно: Greenfield — четыре, Brownfield/Hybrid — пять с baseline. GPT не подтверждает их за пользователя. После любого изменения содержания прежние receipts сохраняются как история, но не дают текущего согласия.

После всех required approvals заполните новое имя папки и отдельно подтвердите размещение. «Собрать, проверить и разместить проект» собирает handoff и публикует новый Project Instance под `%USERPROFILE%\HarnessProjects`. Существующую папку с данными Harness не перезаписывает. Дождитесь результата с точными Task/Run refs, папкой и первым JIT; скачивание handoff и открытие папки — отдельные действия. Повторное чтение и reload не создают второй first Run.

## Ручная Task и независимая проверка

Откройте опубликованный Project Instance в «Проекты и запуск», затем «Задачи и Run». Передайте закреплённый JIT внешнему Codex. Изменения разрешённого product plane выполняет внешний агент. Result JSON должен соответствовать точным Task/Run refs и фактическому diff; его `COMPLETED` не означает DONE.

Получите result из файла либо exact canonical channel. Проверьте показанные argv, cwd, timeout и prerequisites. Без отдельного Run/baseline-bound consent команды не запускаются. Недостающий SDK/toolchain даёт явный blocker; Harness ничего не устанавливает скрыто и не использует frozen executable как Python продукта.

Если Task предусматривает manual checks, откройте «Manual checks: независимое review оператора», выполните каждый пункт, выберите фактически проверенные файлы, запишите observations и PASS/FAIL, укажите reviewer и отдельно подтвердите evidence. Затем нажмите «Проверить». Команды выполняются на host с согласия, это не SANDBOXED. Только текущий независимый PASS разрешает отдельное «Завершить». Изменение result/product после проверки требует новой проверки. «Получить следующую задачу» использует допустимый core route; повтор не дублирует Run.

Task blocker и Stage Gate blocker различаются. Для ordinary Task используйте «Заблокировать Run» с причиной и «Возобновить с новым Run» с exact OPEN blocker/ref и resolution. Старые Runs сохраняются. Не исправляйте canonical YAML вручную.

## Stage, level-up, maintenance, Brownfield и migration

В «Стадии и доказательства» отдельно показаны target, active, claimed, observed и highest accepted. Future stages содержат outlines; детальные Tasks/JIT принадлежат active Stage. Для Gate рассмотрите каждый subject, его evidence/source, permitted use, known limitations и next-stage gaps, укажите actor и отдельно подтвердите действие. UNKNOWN/PARTIAL/FAIL не закрывают обязательный subject. Нельзя заполнить все результаты одним generic PASS.

После acceptance рассмотрите next-stage plan. Material changes требуют rationale. Даже при target RELEASE ближайшая следующая стадия определяется последовательностью PROTOTYPE → ALPHA → BETA → MVP → RELEASE. Accepted history и completed Runs не переписываются.

В «Обслуживание» подготовьте same-level maintenance plan, рассмотрите задачи и подтвердите его отдельно. Cancel доступен только при разрешённых core preconditions. Brownfield assessment читает repository и фиксирует gaps; README с заявлением «BETA» не является доказательством. После изменения repository binding assessment устаревает; baseline approval остаётся отдельным.

«Открыть существующий Harness project…» вызывает локальный выбор папки и compatibility preflight. Для поддержанной migration рассмотрите preview/input и явно подтвердите. v0.5.0 → v0.5.1 по умолчанию MANUAL_HANDOFF; restart/replay не должны переписывать accepted input/reports/completed Runs. Не выполняйте migration по GET.

## Диагностика, recovery и закрытие

«Диагностика» показывает core status, доступные действия и причины недоступности. Automatic executor выключен; его Podman/positive governed egress verdict остаётся прежним NO-GO. Недоступные doctor/demo/прочие UI actions следует читать по фактической причине, а не считать выполненными. Source/wheel CLI doctor — отдельная диагностическая проверка комплекта. Результат своей операции показан в соответствующей панели; общий экспорт журнала обозначен disabled с причиной «не реализован».

При потере вкладки откройте Harness снова и перечитайте canonical status. Явное обновление и чтение после committed операции получают новую проекцию, не переиспользуя GET, начатый до операции. Для прерванной операции используйте «Сверить … без повторного запуска»/явную recovery action. Уже committed acceptance/completion не откатывается из-за потери HTTP response. Неоднозначные внешние команды автоматически не повторяются. При locked file/permission/ENOSPC освободите собственный fixture/resource и выполните явную сверку; не удаляйте пользовательский product root.

«Завершить Harness» требует подтверждения и ожидает безопасного прекращения активных изменений. Закрытие вкладки само по себе не отменяет операции. Uninstall удаляет только файлы комплекта и сохраняет projects/app-data; приватные данные очищаются отдельно осознанным действием оператора.

## Границы evidence и поставки

Пользователь принял четыре NOT RUN ограничения: clean Windows без developer runtimes, физически отключённый интернет, реально заполненный диск и настоящая Unicode учётная запись. Они не назначаются повторно prerequisite. Sanitized PATH, отсутствие внешних app requests, Unicode paths и ENOSPC injection остаются именно этими проверками, не PASS перечисленных условий.

Приёмка разделяет source, installed wheel из независимой CWD и actual installed EXE. Advanced-state fixtures создаются отдельно и явно; browser segment не подменяется изготовлением approvals/evidence через private API. Скриншоты — настоящие synthetic UI, без credentials и пользовательских документов. Security scan имеет перечисленные patterns/каналы/исключения; он не является универсальной DLP.

Рабочая поставка — распакованные Engine/Documentation, wheel и installer с SHA-256/manifests. Raw uploads, auth roots, операторские проекты, `_scratch`, `_tools`, `.venv` и caches в distribution не входят. Engine/Documentation ZIP по заданию не создаются. LOCAL_WEB_MANUAL и AUTOMATIC_EXECUTOR имеют независимые verdicts; полный v0.5.1 остаётся WIP / NOT RELEASED до отдельной нормативной приёмки.
