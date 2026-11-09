# PH-LW-10 — фактическая приёмка Stage lifecycle

2026-11-07. **PH-LW-10: PASS в назначенном manual scope.** Реализован полный prompt r2 на проверенной распакованной базе PH-LW-09 manual evidence. Automatic executor выключен; PH-LW-11 не выполнялся; Engine/Documentation ZIP не создавались. Требование ZIP-пары исторического prompt заменено явным указанием пользователя от 2026-11-07; исходный prompt сохранён.

## База и допустимые изменения

[Входной baseline](../_workspace/PH_LW_10/INPUT_BASELINE.json), [input hashes](../_workspace/PH_LW_10/INPUT_FILE_HASHES.json), [предыдущий CURRENT_TASK](../_workspace/PH_LW_10/CURRENT_TASK.before.md). Проверены manifests распакованных Engine/Documentation, прежний wheel и workspace checkpoint. Исторические NO-GO, input archives/specifications/r2, core schemas/registries и прежние test files сохранены.

Allowed changes: Local Web lifecycle adapters/public form helpers, service/HTTP/assets integration, новые PH-LW-10 tests/Windows runner, операторская глава и docs mirrors, metadata/generated wheel/manifests, новые reports/evidence/workspace tooling/navigation. Core governance, evidence resolver, migration algorithm, statuses и accepted scope не переписаны.

## Реализованное поведение

Stage overview разделяет canonical current-cycle target, active, claimed, observed и highest accepted; отображает exact semantic gaps и read-only acceptance/Run/evidence history. `prepare_stage_approval` создаёт unsigned form; каждый subject имеет отдельный status/rationale/validator/evidence. Actor/DEC/time появляются только после explicit action. `accept_stage` сохраняет реальные BLOCKED/FAIL; missing/unknown/forged proof не повышает maturity.

Active Stage plan проходит public preparation и strict reviewed schema. Exact context server-owned; изменённый work plan требует существующего `ACTIVE_STAGE_PLAN_REVIEW` с rationale; неизменённый не получает выдуманного Decision. `plan_active_stage` открывает только ближайшую Stage и первый READY JIT. Material scope divergence отклоняется. Level-up использует canonical target; проверены Prototype→Alpha при target RELEASE, accepted MVP→RELEASE, no-op и отказ незавершённого cycle.

Maintenance form покрывает обязательные Task/scope/verification/documentation поля и вызывает existing `start_maintenance`. Проверены обычное completion и допустимая отмена; после completed product change cancel запрещён. Stage recovery отделён от обычного Task blocker. Accepted history сохраняется по exact hashes.

Brownfield/Hybrid repository выбирается явно и читается без repository commands. New intake размещается отдельно; inventory/current revision/tree digest привязаны к запросу. Assessment показывает UNKNOWN gaps и отдельную необходимость baseline approval; README claim не принимается за proof; stale source отвергается.

Migration preview использует validator и explicit confirmation. Проверены v0.5.0 и v0.4.1, default MANUAL_HANDOFF, completed Run/history preservation, replay/NO_ACTION и настоящие process-exit interruptions после old/new rename. Recovery требует отдельный POST и existing journal; GET ничего не чинит. В legacy v0.4.1 converter отсутствие execution в lock означает существующий schema default MANUAL_HANDOFF; режим проверен через public Task view, core не изменён.

Exact-byte сохранение `PROJECT_INPUT_ACCEPTED` проверено для v0.5.0→v0.5.1. Legacy v0.4.1 converter по существующему контракту нормализует этот файл и фиксирует прежний digest в migration report; для него проверено сохранение completed Runs, а не неизменность legacy input bytes. Эти version-specific правила явно отражены в операторской документации. UI не расширяет допустимые изменения legacy input и не принимает maturity по completed history.

HTTP mutations сохраняют exact Host/Origin/port, session/CSRF, revision/fingerprint, ownership, idempotency и общий fence. Native folder picker вызывается фиксированным absolute system PowerShell path; HTTP не принимает path/command. Проверены реальное Windows dialog selection/cancel, узкий service picker contract и readonly source. Никакого shell/filesystem gateway, provider API, host Codex fallback, LAN listener, external fetch/CDN/telemetry.

После canonical commit сверка использует exact kernel transaction digest и не повторяет mutator. Reload может пересечься с предыдущим GET: UI объединяет совпадающие чтения и ограниченно повторяет только GET при `OPERATION_CONFLICT` (12 × 250 ms). POST не повторяется. Guard и test deadlines не ослаблены.

## Фактические результаты

| Проверка | Результат |
|---|---|
| Новые PH-LW-10 service/HTTP/native dialog/Edge tests | 29 PASS, 0 SKIP в source и installed wheel |
| Native PH-LW-04–10 current matrix | 183 unique methods PASS, 0 SKIP; полный исходный run + 77-test recheck (включая 49 browser/HTTP cases) и новый polling race test; doctor/docs PASS |
| Installed wheel, отдельная venv/Unicode CWD/site-packages | 181 unique methods PASS, 0 SKIP; исходные main/native + 37-test final browser/HTTP/migration/native recheck; console doctor/launcher/TCP health PASS |
| PH-F06 public lifecycle | 13 PASS, 0 SKIP |
| Полная свежая matrix | 49 modules / 575 methods; 39 PASS / 3 PASS_WITH_SKIPS / 7 FAIL |
| Failure/error/skip/module-timeout events | 24 / 88 / 7 / 0 |

Стенд: настоящий Windows 11 x64/NTFS/non-admin, CPython 3.14.10 x64, pinned Flask 3.1.3/Waitress 3.0.2, реальный Waitress TCP и Edge. [Исходный native report](PH_LW_10_LOGS/native-accepted/PH_LW_10_WINDOWS_TEST_REPORT.json), [final source recheck](PH_LW_10_LOGS/source-verified/tests.json), [installed main](PH_LW_10_LOGS/runs/installed-main.run.json), [final installed recheck](PH_LW_10_LOGS/runs/installed-verified.run.json), [полная matrix](PH_LW_10_LOGS/REGRESSION_MATRIX_CURRENT.json), [сравнение с базой](PH_LW_10_LOGS/PREVIOUS_BASELINE_COMPARISON.json). Native picker сериализован отдельно от source dialog. Все cases выполнены; coverage и supersession проверены по точным IDs. Семь прежних FAIL имеют те же failed IDs; они не объявлены PASS. Все прежние модули повторены, незакрытых новых regression failures в current matrix нет. Mandatory NOT RUN назначенного scope отсутствует.

Ранние диагностические FAIL/ERROR сохранены отдельно: некорректные исходные defaults/fixture binding, коллизия JS identifiers, shadowing document, конкурирующие GET, повторная подготовка уже готового Gate, ожидание обязательного execution key в legacy lock. Browser migration replay воспроизвёл explicit operation-fence conflict после reload; ограниченный read-only retry устранил его без автоматического mutation. Исправления не ослабляют semantic assertions.

Первый native attempt (`native-final`) явно ABORTED до PH-LW-10 cases, когда core regression обнаружил лишние lifecycle controls в GREENFIELD workspace (32 вместо прежних 27). Production fix ограничил новые helpers совместимым kind и выдал уникальные UI IDs. Исходный PH-LW-03 test не менялся; полный 15-test recheck PASS, inventory/metadata PH-LW-01 — 9 PASS. Их rows явно supersede первоначальные core attempts; исходный FAIL сохранён.

Затем полные source/installed прогоны выявили один и тот же прежний PH-LW-07 browser case: approvals counter не менялся за исходные 5000 ms. Native `native-accepted` — 182 methods, 1 FAIL; installed `main` — 179 methods, 1 FAIL. **Эти монолитные прогоны не объявлены PASS.** Все исходные 28 PH-LW-10 cases в них прошли; 29-й polling test добавлен позднее. Диагностика воспроизвела сбой в двух из трёх runs: параллельные `loadApprovals()` получали поздний GET и повторно создавали consent fields, POST решения не отправлялся. Это direct UI regression, а не допустимый semantic failure. Исправление в `approvals.js` объединяет чтения одной формы и проверяет выбранный project; GET остаётся read-only, POST не повторяется.

После fix три последовательных исходных browser cases прошли с теми же assertions и deadlines. [Trace до fix](PH_LW_10_LOGS/approval-diagnostic-repeat/REQUEST_TIMING.json), [состояние UI](PH_LW_10_LOGS/approval-diagnostic-repeat/LAST_UI_STATE.json), [после fix](PH_LW_10_LOGS/runs/approval-fixed-diagnostic.run.json). Промежуточный full PH-LW-07 recheck также получил отдельный WinError 10055 при TCP connect; он сохранён и закрыт новым полным HTTP-module PASS. Причина системной socket error не доказана; системные настройки не менялись.

Следующий `ui-final` run сохранил два отказа: один старый test запросил отсутствующий bundled Chromium, поскольку ручная команда не передала `PH_LW_04_BROWSER_CHANNEL=msedge`; новый migration UI case остановил polling на RUNNING. Первый — ошибка команды запуска. Для второго добавлен deterministic interleaving test: реальный core удаляет backup после rename между перечислением и хешированием файлов polling. Он воспроизвёл `FileNotFoundError` в `_registered` при чтении app-owned operation receipt. После узкого fix `get_operation` проверяет digest/ownership/catalog/native ancestor path, не сканируя меняющийся migration tree; mutation/recovery проверки сохранены. [До fix](PH_LW_10_LOGS/runs/polling-race-before.run.json), [после fix](PH_LW_10_LOGS/runs/polling-race-after.run.json). Existing migration algorithm не изменён. У исходного browser timeout не сохранён server exception trace, поэтому точная причинная связь именно того occurrence с доказанной гонкой остаётся inference; воспроизводимая гонка устранена, browser case повторён успешно.

Последний source recheck использует явный Edge и охватывает все browser/HTTP modules, полный PH-LW-01/03, migration/replay/process-crash/legacy и новый polling test; соответствующие UI/migration/picker cases повторены из окончательного wheel. Все финальные rechecks PASS. [Build delta](PH_LW_10_LOGS/BUILD_DELTA.json) проверяет source hashes и AST: после полных прогонов изменились approvals.js, только методы `_registered`/`get_operation` LocalWebService и generated metadata; в tests добавлен только новый класс, старые bytes восстановлены и сверены. Core algorithms/lifecycle mutators и остальные assets идентичны. Итоговый native/installed verdict — composite по уникальным methods с явным supersession и проверенными hashes, а не новый монолитный exit 0. Общая performance/stress гарантия не заявляется.

В raw stdout также сохранены Waitress queue/connection-limit diagnostics и WinError 10038 фонового server thread при закрытии тестового сервера. Они не удалены из успешного 77-test run; unittest итог — 0 failures/errors/skips. Штатная приёмка маршрутов и guarantee отсутствия всех teardown diagnostics — разные утверждения; последнее этим этапом не заявляется.

Standalone docs validator PASS; единственный WARN — ZIP не передан по явному указанию пользователя. [Покрытие девяти пунктов prompt](PH_LW_10_LOGS/REQUIREMENT_COVERAGE.json) связано с конкретными tests. Диагностические probes не используются как frozen acceptance.

## Outputs, границы и следующий шаг

Build `PH-LW-10-20261107`; source digest `sha256:cfa3d0b37dd4f8f717c52749ab440f4888220904eacf2f2d4c263156ba4a5e54`; wheel SHA-256 `6d1de3e94b84f8c20ced6248b972402d5564a4b1d6dac2254e4f2a6978b9f310`. [Evidence index](PH_LW_10_LOGS/EVIDENCE_INDEX.json), [changed files](PH_LW_10_CHANGED_FILES.md), [финальная аттестация](../_workspace/PH_LW_10/FINAL_WORKING_TREE_VERIFICATION.json), [output SHA-256](../_workspace/PH_LW_10/SHA256.txt). Команды/CWD/platform/exit/log hashes — в run metadata; interpreter/deps — SOURCE_ENVIRONMENT/WHEEL_ENVIRONMENT. Docs mirror, build/lib и wheel сверены с текущими рабочими файлами; private auth/uploads/cache/venv не включены.

Исторические archives неизменны. ZIP внутри synthetic compiler/migration fixtures — входы/outputs тестов, не поставочные Engine/Documentation архивы. Review observations и actor — явные заявления оператора, не криптографическое удостоверение истинности или личности. Process fault injection не доказывает physical power-loss guarantees. Clean-machine installer, полный end-to-end PH-LW-12, реальный Codex, rootless Podman security и positive governed per-Run egress не входят в этот этап.

PH-LW-04–10 PASS в своих scopes. `LOCAL_WEB_MANUAL: NO-GO` до PH-LW-12; `AUTOMATIC_EXECUTOR: NO-GO`; полная v0.5.1 `NO-GO / NOT RELEASED`. Следующий этап — только по новому заданию пользователя. PH-LW-11 не начат.
