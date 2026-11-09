# PH-LW-07 — фактический отчёт

Дата: 2026-11-07. **PASS в точном scope PH-LW-07**. Build `PH-LW-07-20261107`. Это не release GO и не выполнение PH-LW-08.

## База, полномочия и changes

Прочитан полный [PH-LW-07 r2 prompt](../Harness_Local_Web_Prompts_RU_r2/prompts/PH_LW_07.md), Local Web plan/acceptance/source mapping, применимые normative v0.5.0/v0.5.1 и публичные input/draft/operation contracts. Новое задание разрешило PH-LW-07 вместо прежнего запрета в CURRENT_TASK. Требование ZIP старого prompt явно отменено текущим заданием пользователя; исторические источники не переписаны.

Вход — точные распакованные PH-LW-06 деревья. Engine manifest `ad8baab86981abd99951c2793468b9c520291443279fac62ad9280614b840745`, Documentation manifest `30a9e17207887b0d9d473e63806c2ad369242b5c3d5534d1ec94d1a3faefa57b`, wheel `04c34ced9484c0664f399ef45fe393c475c55d33fdf0fd6df8bd8bbfbc25e1dc`. Сверка с прежней внешней аттестацией PASS, workspace drift отсутствует. [Все входные file hashes](../_workspace/PH_LW_07/INPUT_FILE_HASHES.json), [preflight](../_workspace/PH_LW_07/INPUT_BASELINE.json). Происхождение WIP/NO-GO, включая прежнее различие заявленной PH-051-12 и supplied PH-051-11 базы, сохранено в metadata и исторических reports.

Allowed changes: отдельные approval public API/receipts; точечные service/HTTP/recovery fences; формы intake; tests/native runner; docs/mirror, metadata/wheel/manifests; новые reports/evidence и workspace navigation/tooling. Реализация не меняет core schemas/registries, Stage/level-up tests и accepted history. [Changed files](PH_LW_07_CHANGED_FILES.md), [инварианты](PH_LW_07_PRESERVED_INVARIANTS.md).

## Реализованное поведение

- Четыре Greenfield и пять Brownfield/Hybrid actions в порядке `approvals_for_mode()`. Отдельный baseline между definition и architecture. Точный subject content показан до каждого действия, actor явно задаётся один раз, timestamp назначает server.
- Companion receipt v1 вне strict PROJECT_INPUT связывает subject digest, exact draft/source revisions, content digest, fingerprint, actor/time, request и before/after. Stage DEC/ACT поля не добавлены. Receipt — audit binding, не подпись/identity proof.
- Guarded public approval API делает atomic canonical write. Double click/exact retry возвращает прежнее решение; changed payload/key, другая вкладка, stale source/fingerprint и forged fields отклоняются.
- «На доработку» сохраняет комментарий, сбрасывает selected/dependent current draft approvals, показывает уточнение. Material draft/source edits консервативно инвалидируют current approvals с причиной и прежним receipt. Исторические receipts не переписываются.
- Missing architecture/technology/target/sensitivity и другие readiness gaps блокируют `approved:true`. GET только читает; persisted readiness обновляется после успешного POST commit через `check_intake`.
- Final handoff confirmation возвращает честное `PREPARATION_PENDING_PH_LW_08`, Project Instance не создан. HTTP prepare заблокирован до PH-LW-08; прежние trusted Python/CLI APIs не удалены.

Операторская глава: [отдельные согласования](docs/Project_Harness_Documentation_v0.5.1/13_Local_Web_Manual_Companion/14_PH_LW_07_Separate_Approvals.md). Browser создание новых Brownfield/Hybrid intake не добавлено: проверены формы для заранее созданных/зарегистрированных public API intake; repository inventory/live tree читается без команд и mutations.

## Фактические проверки

| Run | Результат | Evidence |
|---|---|---|
| Входные PH-LW-03/06 regressions | 35 PASS / 0 SKIP | [baseline](PH_LW_07_LOGS/baseline/MATRIX.json) |
| Новые target modules в общей matrix | 22 PASS / 0 SKIP | [matrix](PH_LW_07_LOGS/REGRESSION_MATRIX_CURRENT.json) |
| Native final PH-LW-04–07 | 86 runtime PASS / 0 SKIP, docs PASS; отдельный doctor retest PASS | [composite verdict](PH_LW_07_LOGS/NATIVE_SCOPE_VERDICT.json) |
| Installed wheel, отдельная venv/Unicode CWD | 84 PASS / 0 SKIP, console doctor/launcher/health PASS | [wheel run](PH_LW_07_LOGS/runs/installed-wheel-final.run.json) |
| Вся regression matrix | 42 модулей / 478 methods; 32 PASS / 3 PASS_WITH_SKIPS / 7 FAIL | [полная matrix](PH_LW_07_LOGS/REGRESSION_MATRIX_CURRENT.json) |
| Docs validator | 35 PASS / 1 ожидаемый ZIP WARN | [docs](PH_LW_07_LOGS/native-retest/DOC_VALIDATION.json) |

Windows `Windows-11-10.0.26200-SP0`, NTFS, non-admin, Python `3.14.10` x64; Flask `3.1.3`, Waitress `3.0.2`, Playwright `1.64.1`, Edge `157.0.4341.42`. Реальный production Waitress/TCP и Edge; Flask test client не подменяет эти runs. Wheel imports подтверждены из site-packages вне source; runtime/dev зависимости установлены offline по hash locks. [Source environment](PH_LW_07_LOGS/SOURCE_ENVIRONMENT.json), [wheel environment](PH_LW_07_LOGS/WHEEL_ENVIRONMENT.json), [команды/exit/hash каждого run](PH_LW_07_LOGS/EVIDENCE_INDEX.json).

Обязательные scenarios: four/five actions, missing last approval, wrong order/baseline, source changed, stale fingerprint/subject digest, GPT actor/approved_at/approved forgery, double click/concurrency, exact replay/restart, rework/invalidation, read-only GET, HTTP Host/Origin/port/session/CSRF/unknown/duplicate fields, native child crash **до commit, после commit, после receipt** и ambiguous recovery — PASS. Positive workflow действительно даёт `check_intake: READY_FOR_HANDOFF`; до него hidden approvals отсутствуют. Текущие formal Stage/level-up tests неизменны; их свежие результаты находятся в общей matrix.

Сохранённые ранние неуспехи: target-initial — 5 error subtests из-за повторного key fixture при разных edits; target-second — fixture открыла согласования без выбранного проекта; target-third — тестовый direct GET столкнулся с законным OS lock фонового browser GET. Исправлены fixtures/synchronization, не semantic expectations. Target-fourth прошёл, но та же тестовая гонка повторилась в первом полном native run (85 PASS / 1 ERROR / 0 SKIP). Вместо direct Python GET проверяется появление сохранённого комментария в UI после нового response; ожидания поведения не ослаблены. Native-retest дал 86 runtime PASS / 0 SKIP и docs PASS. Его wrapper остался FAIL только из-за устаревшего manifest после добавления двух reports и исправленного test: после sync отдельный `doctor-retest` PASS. Исходный wrapper report не переписан. Installed-wheel run: полный PASS. Исторические FAIL logs сохранены. Финальная визуальная проверка: [Greenfield](PH_LW_07_LOGS/browser-final/approvals-greenfield.png), [Brownfield](PH_LW_07_LOGS/browser-final/approvals-brownfield.png), [Hybrid](PH_LW_07_LOGS/browser-final/approvals-hybrid.png).

Общая matrix содержит 24 failure events / 88 error events / 7 SKIP / 0 TIMEOUT. Failure/error events включают subtests и не являются числом failed methods. Все 40 прежних модулей сохранили status/counts/failures/errors/skips; [точное сравнение](PH_LW_07_LOGS/PREVIOUS_BASELINE_COMPARISON.json). Это унаследованные mixed Linux/automatic failures, не освобождение manual path от проверок:

| Модуль | Failures | Errors | Skips |
|---|---:|---:|---:|
| `tests.test_ph_051_03_rootless_podman` | 2 | 8 | 1 |
| `tests.test_ph_051_04_disposable_roots` | 0 | 16 | 1 |
| `tests.test_ph_051_05_codex_adapter` | 0 | 4 | 2 |
| `tests.test_ph_051_06_result_channel` | 0 | 21 | 0 |
| `tests.test_ph_051_08_atomic_apply` | 0 | 31 | 0 |
| `tests.test_ph_051_09_automatic_runtime` | 18 | 1 | 0 |
| `tests.test_ph_051_10_migration_recovery` | 4 | 7 | 0 |

Все конкретные SKIP reasons сохранены в matrix/logs; mandatory SKIP/NOT RUN не признаны PASS. Не менялись системная защита, permissions или Linux/automatic expectations ради зелёной matrix.

## Поставка, gates и следующий шаг

Wheel SHA-256: `fc90f3258eb0e11d55f270a592bad828b4853aa1d80604ac76e8c2261e886246`. Source build digest: `sha256:bfec035053b1c413091b3719980d82bf74e3a725fe3e45db1f20bf28ba84b947`. Docs standalone/embedded синхронизированы побайтово, build/lib и dist сгенерированы из src. [Финальная внешняя аттестация](../_workspace/PH_LW_07/FINAL_WORKING_TREE_VERIFICATION.json), [output hashes](../_workspace/PH_LW_07/SHA256.txt). Старые Engine/Documentation ZIP не обновлялись; новые не создавались.

Отдельные verdicts: `PH-LW-04: PASS`, `PH-LW-05: PASS`, `PH-LW-06: PASS`, `PH-LW-07: PASS` в их проверенных scopes. `LOCAL_WEB_MANUAL: NO-GO` до PH-LW-12. `AUTOMATIC_EXECUTOR: NO-GO`. Полная v0.5.1: `NO-GO / NOT RELEASED`.

NOT RUN / открытые gates: positive governed per-Run egress, реальная rootless Podman security acceptance, Windows power-loss/storage-failure, clean-machine installer и полный manual lifecycle PH-LW-12. Subprocess `os._exit` не заменяет power-loss. Browser/GPT draft — синтетические fixtures, provider/model общения нет. Automatic executor не включался, shell/filesystem gateway, host Codex fallback, LAN listener и внешние fetch не добавлены.

PH-LW-07 завершён. Следующий шаг — только новое задание пользователя; PH-LW-08 не выполнялся и требует отдельного назначения. Engine/Documentation ZIP также требуют отдельного явного запроса.
