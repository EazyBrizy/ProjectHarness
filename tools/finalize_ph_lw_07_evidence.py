"""Publish completed PH-LW-07 evidence, preserving earlier FAIL logs; no ZIPs."""
from __future__ import annotations
from collections import Counter
import hashlib
import json
from pathlib import Path
import re

from finalize_evidence import sanitize
from package_acceptance import files

ROOT = Path(__file__).resolve().parents[1]
ENGINE = ROOT / 'Project_Harness_Engine_v0.5.1'
DOCS = ROOT / 'Project_Harness_Documentation_v0.5.1'
SCRATCH = ROOT / '_scratch/ph_lw_07'
OUT = ENGINE / 'PH_LW_07_LOGS'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text('utf-8'))


def save(path, value):
    path.write_text(sanitize(json.dumps(value, ensure_ascii=False, indent=2))+'\n', 'utf-8')


def summary(rows):
    return {'modules':len(rows), 'test_methods':sum(r['ran'] for r in rows),
        'module_statuses':dict(Counter(r['status'] for r in rows)),
        'failure_events':sum(r.get('failures',0) for r in rows),
        'error_events':sum(r.get('errors',0) for r in rows),
        'skips':sum(len(r.get('skips',[])) for r in rows),
        'timeouts':sum(r['status']=='TIMEOUT' for r in rows)}


def main():
    rows = read(SCRATCH/'regressions-final/MATRIX.json')
    assert len(rows) == len(list((ENGINE/'tests').glob('test_*.py')))
    assert len({r['module'] for r in rows}) == len(rows)
    native = read(SCRATCH/'native-retest/PH_LW_07_WINDOWS_TEST_REPORT.json')
    installed = read(SCRATCH/'runs/installed-wheel-final.run.json')
    assert installed['status'] == 'PASS'
    assert all(row['status']=='PASS' for row in native['checks'] if row.get('name')!='doctor')
    assert read(SCRATCH/'runs/doctor-retest.run.json')['status']=='PASS'
    installed_log = (SCRATCH/'runs/installed-wheel-final.log').read_text('utf-8')
    wheel_count = int(re.search(r'Ran (\d+) tests', installed_log).group(1))
    assert '"source_import": false' in installed_log and '"skips": 0' in installed_log
    previous = {r['module']:r for r in read(ENGINE/'PH_LW_06_LOGS/REGRESSION_MATRIX_CURRENT.json')['rows']}
    comparison = []
    for row in rows:
        if row['module'] in previous:
            old = previous[row['module']]
            changes = {k:{'previous':old.get(k),'current':row.get(k)} for k in ('status','ran','failures','errors') if old.get(k)!=row.get(k)}
            if len(old['skips']) != len(row['skips']): changes['skips']={'previous':len(old['skips']),'current':len(row['skips'])}
            comparison.append({'module':row['module'],'differences':changes})
    assert not any(r['differences'] for r in comparison), comparison
    assert all(r['status']=='PASS' for r in rows if r['module'] not in previous)
    OUT.mkdir(exist_ok=True)
    pairs = [(p,OUT/p.relative_to(SCRATCH)) for p in SCRATCH.rglob('*') if p.is_file()
        and p.suffix in {'.json','.log','.png'} and p.relative_to(SCRATCH).parts[0] in
        {'baseline','target-initial','target-second','target-third','target-fourth','regressions-final','native-final','native-retest','runs','browser','browser-final'}]
    pairs += [(p,OUT/p.name) for p in (SCRATCH/'SOURCE_ENVIRONMENT.json', SCRATCH/'WHEEL_ENVIRONMENT.json', ROOT/'_workspace/PH_LW_07/INPUT_BASELINE.json')]
    index = []
    for source,target in sorted(pairs):
        target.parent.mkdir(parents=True,exist_ok=True)
        if source.suffix=='.png': target.write_bytes(source.read_bytes())
        else: target.write_text(sanitize(source.read_text('utf-8',errors='replace')),'utf-8')
        index.append({'raw_source':source.relative_to(ROOT).as_posix(),'file':target.relative_to(OUT).as_posix(),
                      'raw_sha256':sha(source),'published_sha256':sha(target)})
    save(OUT/'EVIDENCE_INDEX.json',index)
    stats=summary(rows)
    save(OUT/'REGRESSION_MATRIX_CURRENT.json',{'status':'FAIL' if stats['module_statuses'].get('FAIL') else 'PASS',
        'provenance':'All modules executed in this task; affected PH-LW modules ran after final source edits.',**stats,'rows':rows})
    save(OUT/'PREVIOUS_BASELINE_COMPARISON.json',{'status':'UNCHANGED_RESULTS_FOR_ALL_40_PREVIOUS_MODULES','rows':comparison})
    meta=read(ENGINE/'src/project_harness/resources/local_web/metadata_v1.json')
    save(OUT/'BUILD_PROVENANCE.json',{'build_id':meta['local_web_build_id'],'engine_build_digest':meta['engine_build_digest'],
        'wheel_sha256':sha(ENGINE/'dist/project_harness_engine-0.5.1-py3-none-any.whl'),
        'input':read(ROOT/'_workspace/PH_LW_07/INPUT_BASELINE.json'), 'zip_created':False})
    save(OUT/'NATIVE_SCOPE_VERDICT.json',{'status':'PASS','tests':native['checks'][0]['ran'],
        'skips':native['checks'][0]['skips'],'source':'native-retest/PH_LW_07_WINDOWS_TEST_REPORT.json',
        'original_wrapper_status':native['status'], 'doctor_retest':'runs/doctor-retest.run.json',
        'doctor_retest_status':'PASS', 'note':'86 runtime tests and docs PASS; original doctor found stale manifest after report/test edits. Manifest synchronized and doctor retested separately; original FAIL preserved.',
        'installed_wheel_tests':wheel_count,'installed_source':'runs/installed-wheel-final.run.json'})
    (OUT/'README.md').write_text('''# PH-LW-07: фактическое evidence

`regressions-final` — все модули заново в этом задании; исторические результаты не подставлены.
Ранние core modules выполнялись во время финального редактирования только approval presentation/CSS;
все затронутые PH-LW modules запущены после этих правок. Native и installed-wheel прогоны — после freeze.
`baseline` — проверка исходных PH-LW-03/06 APIs до правок. `target-*` сохраняют первоначальные FAIL и retests.
`native-final` — первый полный run с одной тестовой гонкой; `native-retest` — 86 runtime PASS и docs PASS.
Его wrapper FAIL сохранён: doctor обнаружил устаревший manifest после добавления reports и test fix.
`runs/doctor-retest` — PASS после синхронизации manifest; NATIVE_SCOPE_VERDICT связывает эти runs.
Оба выполнялись на настоящем Windows 11 x64/NTFS/non-admin/Python 3.14, pinned Flask/Waitress и Edge/TCP.
`runs/installed-wheel-final` — независимая venv, Unicode CWD, site-packages import, launcher/doctor/health.
`browser-final` — реальные снимки финального UI, только синтетические fixtures.
Зависимости и platform общие для source runs в SOURCE_ENVIRONMENT; wheel — WHEEL_ENVIRONMENT.
Raw logs остаются в `_scratch/ph_lw_07`; опубликованные копии редактируют только приватные пути/credentials.
EVIDENCE_INDEX хранит разные raw/published hashes. Вложенные log hashes относятся к raw bytes.
FAIL/SKIP не повышаются до PASS. Automatic/Podman/egress и installer gates остаются незакрытыми.
Engine/Documentation ZIP не создавались. Финальная аттестация рабочих деревьев — `_workspace/PH_LW_07`.
''','utf-8')
    baseline=read(ROOT/'_workspace/PH_LW_07/INPUT_BASELINE.json')
    failed=[r for r in rows if r['status']=='FAIL']
    skipped=[r for r in rows if r['skips']]
    native_count=native['checks'][0]['ran']
    new_tests=sum(r['ran'] for r in rows if r['module'] not in previous)
    report=f'''# PH-LW-07 — фактический отчёт

Дата: 2026-11-07. **PASS в точном scope PH-LW-07**. Build `{meta['local_web_build_id']}`. Это не release GO и не выполнение PH-LW-08.

## База, полномочия и changes

Прочитан полный [PH-LW-07 r2 prompt](../Harness_Local_Web_Prompts_RU_r2/prompts/PH_LW_07.md), Local Web plan/acceptance/source mapping, применимые normative v0.5.0/v0.5.1 и публичные input/draft/operation contracts. Новое задание разрешило PH-LW-07 вместо прежнего запрета в CURRENT_TASK. Требование ZIP старого prompt явно отменено текущим заданием пользователя; исторические источники не переписаны.

Вход — точные распакованные PH-LW-06 деревья. Engine manifest `{baseline['trees'][ENGINE.name]['manifest_sha256']}`, Documentation manifest `{baseline['trees'][DOCS.name]['manifest_sha256']}`, wheel `{baseline['wheel_sha256']}`. Сверка с прежней внешней аттестацией PASS, workspace drift отсутствует. [Все входные file hashes](../_workspace/PH_LW_07/INPUT_FILE_HASHES.json), [preflight](../_workspace/PH_LW_07/INPUT_BASELINE.json). Происхождение WIP/NO-GO, включая прежнее различие заявленной PH-051-12 и supplied PH-051-11 базы, сохранено в metadata и исторических reports.

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
| Новые target modules в общей matrix | {new_tests} PASS / 0 SKIP | [matrix](PH_LW_07_LOGS/REGRESSION_MATRIX_CURRENT.json) |
| Native final PH-LW-04–07 | {native_count} runtime PASS / 0 SKIP, docs PASS; отдельный doctor retest PASS | [composite verdict](PH_LW_07_LOGS/NATIVE_SCOPE_VERDICT.json) |
| Installed wheel, отдельная venv/Unicode CWD | {wheel_count} PASS / 0 SKIP, console doctor/launcher/health PASS | [wheel run](PH_LW_07_LOGS/runs/installed-wheel-final.run.json) |
| Вся regression matrix | {stats['modules']} модулей / {stats['test_methods']} methods; {stats['module_statuses'].get('PASS',0)} PASS / {stats['module_statuses'].get('PASS_WITH_SKIPS',0)} PASS_WITH_SKIPS / {stats['module_statuses'].get('FAIL',0)} FAIL | [полная matrix](PH_LW_07_LOGS/REGRESSION_MATRIX_CURRENT.json) |
| Docs validator | 35 PASS / 1 ожидаемый ZIP WARN | [docs](PH_LW_07_LOGS/native-retest/DOC_VALIDATION.json) |

Windows `{native['platform']}`, NTFS, non-admin, Python `{native['python'].split()[0]}` x64; Flask `{native['dependencies']['flask']}`, Waitress `{native['dependencies']['waitress']}`, Playwright `{native['dependencies']['playwright']}`, Edge `{native['browser']}`. Реальный production Waitress/TCP и Edge; Flask test client не подменяет эти runs. Wheel imports подтверждены из site-packages вне source; runtime/dev зависимости установлены offline по hash locks. [Source environment](PH_LW_07_LOGS/SOURCE_ENVIRONMENT.json), [wheel environment](PH_LW_07_LOGS/WHEEL_ENVIRONMENT.json), [команды/exit/hash каждого run](PH_LW_07_LOGS/EVIDENCE_INDEX.json).

Обязательные scenarios: four/five actions, missing last approval, wrong order/baseline, source changed, stale fingerprint/subject digest, GPT actor/approved_at/approved forgery, double click/concurrency, exact replay/restart, rework/invalidation, read-only GET, HTTP Host/Origin/port/session/CSRF/unknown/duplicate fields, native child crash **до commit, после commit, после receipt** и ambiguous recovery — PASS. Positive workflow действительно даёт `check_intake: READY_FOR_HANDOFF`; до него hidden approvals отсутствуют. Текущие formal Stage/level-up tests неизменны; их свежие результаты находятся в общей matrix.

Сохранённые ранние неуспехи: target-initial — 5 error subtests из-за повторного key fixture при разных edits; target-second — fixture открыла согласования без выбранного проекта; target-third — тестовый direct GET столкнулся с законным OS lock фонового browser GET. Исправлены fixtures/synchronization, не semantic expectations. Target-fourth прошёл, но та же тестовая гонка повторилась в первом полном native run (85 PASS / 1 ERROR / 0 SKIP). Вместо direct Python GET проверяется появление сохранённого комментария в UI после нового response; ожидания поведения не ослаблены. Native-retest дал 86 runtime PASS / 0 SKIP и docs PASS. Его wrapper остался FAIL только из-за устаревшего manifest после добавления двух reports и исправленного test: после sync отдельный `doctor-retest` PASS. Исходный wrapper report не переписан. Installed-wheel run: полный PASS. Исторические FAIL logs сохранены. Финальная визуальная проверка: [Greenfield](PH_LW_07_LOGS/browser-final/approvals-greenfield.png), [Brownfield](PH_LW_07_LOGS/browser-final/approvals-brownfield.png), [Hybrid](PH_LW_07_LOGS/browser-final/approvals-hybrid.png).

Общая matrix содержит {stats['failure_events']} failure events / {stats['error_events']} error events / {stats['skips']} SKIP / {stats['timeouts']} TIMEOUT. Failure/error events включают subtests и не являются числом failed methods. Все 40 прежних модулей сохранили status/counts/failures/errors/skips; [точное сравнение](PH_LW_07_LOGS/PREVIOUS_BASELINE_COMPARISON.json). Это унаследованные mixed Linux/automatic failures, не освобождение manual path от проверок:

| Модуль | Failures | Errors | Skips |
|---|---:|---:|---:|
'''
    report+='\n'.join(f"| `{r['module']}` | {r['failures']} | {r['errors']} | {len(r['skips'])} |" for r in failed)
    report+=f'''

Все конкретные SKIP reasons сохранены в matrix/logs; mandatory SKIP/NOT RUN не признаны PASS. Не менялись системная защита, permissions или Linux/automatic expectations ради зелёной matrix.

## Поставка, gates и следующий шаг

Wheel SHA-256: `{sha(ENGINE/'dist/project_harness_engine-0.5.1-py3-none-any.whl')}`. Source build digest: `{meta['engine_build_digest']}`. Docs standalone/embedded синхронизированы побайтово, build/lib и dist сгенерированы из src. [Финальная внешняя аттестация](../_workspace/PH_LW_07/FINAL_WORKING_TREE_VERIFICATION.json), [output hashes](../_workspace/PH_LW_07/SHA256.txt). Старые Engine/Documentation ZIP не обновлялись; новые не создавались.

Отдельные verdicts: `PH-LW-04: PASS`, `PH-LW-05: PASS`, `PH-LW-06: PASS`, `PH-LW-07: PASS` в их проверенных scopes. `LOCAL_WEB_MANUAL: NO-GO` до PH-LW-12. `AUTOMATIC_EXECUTOR: NO-GO`. Полная v0.5.1: `NO-GO / NOT RELEASED`.

NOT RUN / открытые gates: positive governed per-Run egress, реальная rootless Podman security acceptance, Windows power-loss/storage-failure, clean-machine installer и полный manual lifecycle PH-LW-12. Subprocess `os._exit` не заменяет power-loss. Browser/GPT draft — синтетические fixtures, provider/model общения нет. Automatic executor не включался, shell/filesystem gateway, host Codex fallback, LAN listener и внешние fetch не добавлены.

PH-LW-07 завершён. Следующий шаг — только новое задание пользователя; PH-LW-08 не выполнялся и требует отдельного назначения. Engine/Documentation ZIP также требуют отдельного явного запроса.
'''
    (ENGINE/'PH_LW_07_TEST_REPORT.md').write_text(report,'utf-8')
    print(json.dumps({'published_files':len(index),'native':native_count,'installed':wheel_count,**stats},indent=2))


if __name__=='__main__': main()
