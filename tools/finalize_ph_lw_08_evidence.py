"""Publish exact PH-LW-08 runs and a complete non-duplicated regression matrix."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import re

from finalize_evidence import sanitize
from package_acceptance import ROOT, ENGINE, DOCS, files

SCRATCH = ROOT / '_scratch/ph_lw_08'
OUT = ENGINE / 'PH_LW_08_LOGS'
WORK = ROOT / '_workspace/PH_LW_08'


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def read(path): return json.loads(path.read_text('utf-8'))
def save(path, data): path.write_text(sanitize(json.dumps(data,ensure_ascii=False,indent=2))+'\n','utf-8')


def main():
    frozen = read(SCRATCH/'FINAL_BUILD_FREEZE.json')
    assert all(sha(ENGINE/'src/project_harness'/name) == digest for name, digest in frozen['source_hashes'].items())
    assert sha(ENGINE/'dist/project_harness_engine-0.5.1-py3-none-any.whl') == frozen['wheel_sha256']
    native = read(SCRATCH/'native-revised/PH_LW_08_WINDOWS_TEST_REPORT.json')
    installed = read(SCRATCH/'runs/installed-wheel-revised.run.json')
    assert native['checks'][0]['status']=='PASS',native
    closure_runs = {name: read(SCRATCH/('runs/'+name+'.run.json')) for name in ('doctor-post-sync','docs-post-sync','embedded-docs-post-sync')}
    assert all(row['status']=='PASS' for row in closure_runs.values()), closure_runs
    assert installed['status']=='PASS',installed
    assert not native['checks'][0]['skips']
    core = read(SCRATCH/'core-regressions/MATRIX.json')
    failure_ids = read(SCRATCH/'FAILURE_ID_COMPARISON.json')
    assert len(failure_ids) == 7 and all(r['same_failed_test_ids'] for r in failure_ids)
    native_log = (SCRATCH/'native-revised/stage_tests.log').read_text('utf-8')
    counts = Counter(re.findall(r'^test\S+ \((tests\.[^.]+)\.[^)]+\) \.\.\.',native_log,re.M))
    assert sum(counts.values())==native['checks'][0]['ran'],counts
    native_command = read(SCRATCH/'runs/native-revised.run.json')['command']
    rows = core + [{'module':module,'command':native_command,'status':'PASS','ran':count,
                    'failures':0,'errors':0,'skips':[],'log':'native-revised/stage_tests.log',
                    'evidence':'native-revised/PH_LW_08_WINDOWS_TEST_REPORT.json','platform':native['platform'],
                    'note':'Fresh native combined suite; module count from exact unittest IDs.'}
                   for module,count in counts.items()]
    for row in core:row['evidence']='core-regressions/'+row['log']
    assert {r['module'] for r in rows}=={'tests.'+p.stem for p in (ENGINE/'tests').glob('test_*.py')}
    assert len(rows)==len({r['module'] for r in rows})
    prior={r['module']:r for r in read(ENGINE/'PH_LW_07_LOGS/REGRESSION_MATRIX_CURRENT.json')['rows']}
    comparison=[]
    for row in rows:
        if row['module'] in prior:
            old=prior[row['module']]
            diff={k:{'previous':old[k],'current':row[k]} for k in ('status','ran','failures','errors') if old[k]!=row[k]}
            if len(old['skips'])!=len(row['skips']):diff['skips']={'previous':len(old['skips']),'current':len(row['skips'])}
            comparison.append({'module':row['module'],'differences':diff})
    assert not any(r['differences'] for r in comparison),comparison
    assert all(r['status']=='PASS' for r in rows if r['module'] not in prior)
    stats={'modules':len(rows),'test_methods':sum(r['ran'] for r in rows),
        'module_statuses':dict(Counter(r['status'] for r in rows)),
        'failure_events':sum(r['failures'] for r in rows),'error_events':sum(r['errors'] for r in rows),
        'skips':sum(len(r['skips']) for r in rows),'timeouts':sum(r['status']=='TIMEOUT' for r in rows)}
    wheel_log=(SCRATCH/'runs/installed-wheel-revised.log').read_text('utf-8')
    wheel_count=int(re.search(r'Ran (\d+) tests',wheel_log).group(1))
    assert '"source_import": false' in wheel_log and '"skips": 0' in wheel_log
    OUT.mkdir(exist_ok=True)
    index=[]
    for source in sorted(SCRATCH.rglob('*')):
        if not source.is_file() or source.suffix not in {'.log','.json','.png','.py'}:continue
        rel=source.relative_to(SCRATCH)
        if rel.parts[0] not in {'runs','native-final','native-revised','core-regressions','screenshots','screenshots-revised','wheel-screenshots','wheel-screenshots-revised','SOURCE_ENVIRONMENT.json','WHEEL_ENVIRONMENT.json','DOC_VALIDATION_REVISED.json','DOC_VALIDATION_POST_SYNC.json','EMBEDDED_DOC_VALIDATION_POST_SYNC.json','FINAL_BUILD_FREEZE.json','FAILURE_ID_COMPARISON.json','trace_browser.py','trace_browser_state.py','reproduce_read_handle.py'}:continue
        target=OUT/rel;target.parent.mkdir(parents=True,exist_ok=True)
        if source.suffix=='.png':target.write_bytes(source.read_bytes())
        else:target.write_text(sanitize(source.read_text('utf-8',errors='replace')),'utf-8')
        index.append({'raw_source':source.relative_to(ROOT).as_posix(),'file':rel.as_posix(),
            'raw_sha256':sha(source),'published_sha256':sha(target)})
    save(OUT/'EVIDENCE_INDEX.json',index)
    save(OUT/'REGRESSION_MATRIX_CURRENT.json',{'status':'FAIL','provenance':'Fresh native modules plus fresh remaining core modules; no inherited results substituted.',**stats,'rows':sorted(rows,key=lambda r:r['module'])})
    save(OUT/'PREVIOUS_BASELINE_COMPARISON.json',{'status':'UNCHANGED_RESULTS_FOR_ALL_42_PREVIOUS_MODULES','rows':comparison})
    meta=read(ENGINE/'src/project_harness/resources/local_web/metadata_v1.json')
    wheel=ENGINE/'dist/project_harness_engine-0.5.1-py3-none-any.whl'
    save(OUT/'BUILD_PROVENANCE.json',{'build_id':meta['local_web_build_id'],'engine_build_digest':meta['engine_build_digest'],
        'wheel_sha256':sha(wheel),'input':read(WORK/'INPUT_BASELINE.json'),'engine_documentation_zip_created':False})
    verdict={'status':'PASS','tests':native['checks'][0]['ran'],'skips':[],
        'source':'native-revised/PH_LW_08_WINDOWS_TEST_REPORT.json','installed_wheel_tests':wheel_count,
        'installed_source':'runs/installed-wheel-revised.run.json',
        'native_wrapper_status':native['status'],
        'closure_checks':{name:'runs/'+name+'.run.json' for name in closure_runs},
        'note':'115 runtime tests PASS on frozen runtime source; original wrapper FAIL from stale test manifest/cache-contaminated generated file index preserved. After metadata-only synchronization doctor and both docs validators PASS. Runtime source and installed wheel unchanged.'}
    save(OUT/'NATIVE_SCOPE_VERDICT.json',verdict)
    new_count=sum(r['ran'] for r in rows if r['module'] not in prior)
    baseline=read(WORK/'INPUT_BASELINE.json')
    report=f'''# PH-LW-08 — фактический отчёт

Дата: 2026-11-07. **PH-LW-08: PASS в назначенном scope.** Пользователь назначил только PH-LW-08 полного r2 prompt. Automatic executor выключен; PH-LW-09 не выполнялся. Engine/Documentation ZIP не создавались. Runtime handoff ZIP — обязательный output compiler в fixtures, не архив поставки Engine.

## База и область изменений

Распакованная проверенная база PH-LW-07: Engine manifest `{baseline['trees'][ENGINE.name]['manifest_sha256']}`, Documentation manifest `{baseline['trees'][DOCS.name]['manifest_sha256']}`, wheel `{baseline['wheel_sha256']}`. Workspace drift отсутствовал. [Входной baseline](../_workspace/PH_LW_08/INPUT_BASELINE.json), [все input hashes](../_workspace/PH_LW_08/INPUT_FILE_HASHES.json). Исторические inputs/specs/r2/prompts/reports и архивы сохранены.

Allowed changes: materialization public helper, preparation orchestration, точечные service/HTTP/UI fences, target tests и native runner, docs/mirror, metadata/wheel/manifests, новые reports/evidence и navigation/tooling. В старом PH-LW-07 HTTP test изменена только ожидаемая причина отказа generic prepare (`PREPARATION_TARGET_REQUIRED` вместо pending stage); запрет обхода target усилен. Planner, schemas/registries, Stage/level-up tests, execution policy не менялись. [Changed files](PH_LW_08_CHANGED_FILES.md), [инварианты](PH_LW_08_PRESERVED_INVARIANTS.md).

## Поведение

Мастер после действительных отдельных approvals принимает bounded имя новой папки в подтверждённом корне. Target связан с workspace/input/source/approval revisions и engine build. Перед compile/publication binding проверяется повторно. Compiler получает только новые server-owned staging paths, никогда живой destination. Существующие empty/nonempty folders, sentinel, readonly/junction, root/output collisions и чужие IDs отклоняются.

`prepare_handoff` → initial directory/ZIP validators → mutable project validator → exact directory/ZIP byte comparison → Windows same-volume no-replace rename → verified catalog registration. Durable phases и directory identity позволяют продолжить после process exit без второго Run, повторного catalog project или удаления данных. При неполной компиляции явный retry использует новый staging, сохраняя частичный; semantic validation failures не обходятся. После product edits применяется `validate_project_directory`, immutable initial manifest не выдаётся за текущий validator.

UI показывает папку, validation, active/target и exact Task/Run refs. Есть копирование первого JIT, выделяемое поле fallback, registered open-folder и session-bound ZIP download. Compiler уже создал первый JIT; orchestration не вызывает `next`. Tests отдельно проверяют idempotency `next_task`, неизменные bytes/refs и отсутствие future-stage detailed Tasks/JIT. Ни provider API, ни host Codex fallback, ни shell/filesystem gateway не добавлены.

## Фактические проверки

| Проверка | Результат | Evidence |
|---|---|---|
| Новые PH-LW-08 tests | {new_count} PASS / 0 SKIP | [native log](PH_LW_08_LOGS/native-revised/stage_tests.log) |
| Native PH-LW-04–08 + doctor/docs | {verdict['tests']} runtime PASS / 0 SKIP; wrapper FAIL на metadata, закрыт отдельными проверками ниже | [native report](PH_LW_08_LOGS/native-revised/PH_LW_08_WINDOWS_TEST_REPORT.json), [составной verdict](PH_LW_08_LOGS/NATIVE_SCOPE_VERDICT.json) |
| Installed wheel, независимая venv/Unicode CWD | {wheel_count} PASS / 0 SKIP; console doctor, launcher/health PASS | [wheel run](PH_LW_08_LOGS/runs/installed-wheel-revised.run.json) |
| Полная свежая matrix | {stats['modules']} модулей / {stats['test_methods']} methods; {stats['module_statuses'].get('PASS',0)} PASS / {stats['module_statuses'].get('PASS_WITH_SKIPS',0)} PASS_WITH_SKIPS / {stats['module_statuses'].get('FAIL',0)} FAIL | [matrix](PH_LW_08_LOGS/REGRESSION_MATRIX_CURRENT.json) |
| Финальные doctor / standalone и embedded docs validators | PASS; ожидаемый WARN: ZIP не передан | [doctor](PH_LW_08_LOGS/runs/doctor-post-sync.run.json), [docs](PH_LW_08_LOGS/DOC_VALIDATION_POST_SYNC.json), [embedded docs](PH_LW_08_LOGS/EMBEDDED_DOC_VALIDATION_POST_SYNC.json) |

Настоящая Windows `{native['platform']}`, NTFS, non-admin, Python `{native['python'].split()[0]}` x64, Flask `{native['dependencies']['flask']}`, Waitress `{native['dependencies']['waitress']}`, Playwright `{native['dependencies']['playwright']}`, Edge `{native['browser']}`. HTTP — production Waitress/TCP, browser — Edge. Source/wheel environments, commands, exits, elapsed time и raw/published log hashes: [evidence index](PH_LW_08_LOGS/EVIDENCE_INDEX.json). Wheel установлен offline по pinned runtime/dev locks. Test fixtures заменяют внешний GPT; семантическое понимание реальной моделью не заявлено.

PASS scenarios: single MD и ZIP с Unicode/пробелами → public GPT draft/четыре approvals в браузере → реальная папка и скачанный ZIP, directory/project/ZIP PASS, один JIT, reload во время compile и после публикации. Negative cases: недостающий approval, stale sources/build/fingerprint, другой target/owner, unsupported paths, sentinel и empty destination, collision после confirm и перед rename, output sentinel до compiler, forged HTTP fields/session/Host/Origin/CSRF. Recovery: exception checkpoints до/после compile/validation/rename/catalog/result, отдельные реальные processes с `os._exit(91)` после compile/rename/catalog, занятый настоящий Windows directory handle и retry после освобождения, readonly parent и настоящая NTFS junction. Native process-exit test использует одну operation через три successive crashes.

Матрица объединяет {len(counts)} модулей native suite и {len(core)} остальных заново выполненных core modules, без повторного подсчёта tests и без подстановки исторического результата. Core modules выполнены на неизменных core bytes; повторный полный Local Web native suite и installed-wheel suite выполнены на final build. Все 42 прежних модуля сохранили status/counts/failure/error/skip; [сравнение](PH_LW_08_LOGS/PREVIOUS_BASELINE_COMPARISON.json). Унаследовано {stats['failure_events']} failure events / {stats['error_events']} error events / {stats['skips']} SKIP / {stats['timeouts']} TIMEOUT. IDs всех failing tests также совпали: [failure ID comparison](PH_LW_08_LOGS/FAILURE_ID_COMPARISON.json). FAIL смешанных Linux/automatic suites и mandatory SKIP не объявлены PASS.

Предварительные FAIL сохранены: initial target выявил неверное сравнение task ID с revisioned ref; исправлено exact active Run/Task binding, без изменения core contract. Browser runs выявили лишний конкурентный preparation GET при actor action и остановку reconnect polling в окне до записи intent; оба дефекта исправлены. Ошибки ожидаемого текста кнопок и учёт внутренних `edge://downloads-hub` в network assertion исправлены в fixtures; все HTTP/HTTPS запросы по-прежнему обязаны оставаться same-origin. Ранний locked-handle run отказал с STALE_PREPARATION при смене build metadata во время разработки; финальные source/native/wheel runs выполнены после freeze. В первом полном native run 113 tests: 1 FAIL старого browser import из-за раннего включения upload-кнопки; её disabled теперь учитывает requestBusy, исходный test не ослаблен. В первом wheel run 111 tests: 1 FAIL reconnect при INTENT/BLOCKED. Windows read-handle/atomic-replace конфликт воспроизведён отдельно (PermissionError/WinError 5); добавлен bounded retry только companion journal writes, без повторного compiler. Два новых native tests подтверждают transient-read success и persistent-lock failure с сохранением old receipt. Disabled prepare на опубликованном Project Instance проверен в Edge. Предварительный docs validator отклонил metadata новой страницы и строку README; docs исправлены без изменения validator. После этих исправлений native/wheel suites запущены полностью заново на final build. Повторный native wrapper сохранил FAIL после 115 успешных runtime tests: manifest тестового файла устарел после переноса unittest main-блока, а импорт validator без запрета bytecode добавил `__pycache__` в generated FILE_INDEX. Cache сохранён вне документации в scratch; sync tool запрещает bytecode и отказывает при обнаружении старых caches. После регенерации manifests/index оба docs validators и doctor PASS отдельными logged командами. Runtime source/wheel при этом не менялись; исходный wrapper status не переписан и не назван PASS. Составной scope verdict ссылается на все эти фактические runs. Исходные FAIL/TIMEOUT logs не переписаны.

## Поставка и оставшиеся gates

Build `{meta['local_web_build_id']}`, source digest `{meta['engine_build_digest']}`, wheel SHA-256 `{sha(wheel)}`. Docs standalone/embedded совпадают побайтово; build/lib и wheel сгенерированы из src. [Финальная аттестация](../_workspace/PH_LW_08/FINAL_WORKING_TREE_VERIFICATION.json), [output hashes](../_workspace/PH_LW_08/SHA256.txt), [точные changed hashes](../_workspace/PH_LW_08/CHANGED_FILE_HASHES.json). Старые Engine/Documentation ZIP неизменны.

Отдельные verdicts: `PH-LW-04: PASS`, `PH-LW-05: PASS`, `PH-LW-06: PASS`, `PH-LW-07: PASS`, `PH-LW-08: PASS` в проверенных scopes. `LOCAL_WEB_MANUAL: NO-GO` до PH-LW-12. `AUTOMATIC_EXECUTOR: NO-GO`. Полная v0.5.1 `NO-GO / NOT RELEASED`.

NOT RUN / ограничения: физический power-loss и отказ накопителя/disk-full, отдельный destination volume (route принудительно staging на volume назначения), clean-machine installer, весь manual lifecycle PH-LW-09–12, positive governed per-Run egress и реальная rootless Podman security acceptance. Open-folder проверен до точного вызова native API с registered path; визуальный smoke Проводника не подменяется mock. Browser предлагает только настроенный локальный корень; выбора произвольного пути нет. Partial/abandoned staging автоматически не удаляется. Unsupported publication platforms отклоняются. Эти ограничения не превращаются в full release GO.

Следующий разрешённый шаг — новое задание пользователя. PH-LW-09 не начат. Automatic executor не включать. ZIP поставки — только по отдельному запросу.
'''
    (ENGINE/'PH_LW_08_TEST_REPORT.md').write_text(report,'utf-8')
    (ENGINE/'PH_LW_08_PRESERVED_INVARIANTS.md').write_text('''# PH-LW-08 — сохранённые инварианты

- MANUAL_HANDOFF/network NONE; automatic executor/host fallback/provider API/LAN/shell gateway не активированы.
- Browser → service/operation guard → public compiler/validators/materialization; никаких UI/HTTP .harness writes.
- Exact input/source/approval/build binding, no-clobber и отдельные formal approvals. Companion phases не core states.
- Exactly one first current READY JIT. Detailed planning только active Stage; target не расширяет accepted scope.
- Canonical schemas/registries, normative specs, planner, Stage/level-up tests, accepted history, Brownfield semantics и исторические отчёты не менялись.
- Initial handoff validation отделена от mutable project validation; partial staging и user destination не удаляются.
- GET/polling read-only, POST защищены exact Host/Origin/port/session/CSRF; opaque target/artifact ownership и bounded reads.
- Engine/Documentation ZIP не создавались. Точные доказательства: [аттестация](../_workspace/PH_LW_08/FINAL_WORKING_TREE_VERIFICATION.json), [matrix](PH_LW_08_LOGS/REGRESSION_MATRIX_CURRENT.json).
''','utf-8')
    before=read(WORK/'INPUT_FILE_HASHES.json')
    changed=[p for tree in (ENGINE/'src',ENGINE/'tests',ENGINE/'local_web',DOCS) for p in files(tree)
             if before.get(p.relative_to(ROOT).as_posix())!=sha(p)]
    (ENGINE/'PH_LW_08_CHANGED_FILES.md').write_text('# PH-LW-08 — изменения\n\nПервичные source/tests/runner/docs файлы:\n\n'+
        '\n'.join('- `'+p.relative_to(ROOT).as_posix()+'`' for p in changed)+
        '\n\nТакже: README, workspace navigation/tooling, новые PH_LW_08 reports/evidence; generated build/lib, dist, egg-info, docs aggregates/mirror и manifests. Старые источники/история не переписаны. Полный список до/после с hashes: [CHANGED_FILE_HASHES.json](../_workspace/PH_LW_08/CHANGED_FILE_HASHES.json).\n','utf-8')
    (OUT/'README.md').write_text('# PH-LW-08 evidence\n\n`native-revised` — реальные Windows/TCP/Edge/NTFS checks; `core-regressions` — остальные свежие модули. `REGRESSION_MATRIX_CURRENT.json` объединяет их без дубликатов. `runs` сохраняет все ранние FAIL и финальные прогоны. Source/wheel environments и raw/published hashes находятся рядом. Реальные uploads/auth/venv в evidence не включены; screenshots содержат только synthetic fixtures.\n','utf-8')
    current=f'''# Текущая работа

Дата: 2026-11-07. Статус: **COMPLETE — PH-LW-08: PASS в назначенном scope**.

Пользователь назначил только PH-LW-08 полного r2 prompt на проверенной базе PH-LW-07. Automatic executor выключен; PH-LW-09 не выполнялся; Engine/Documentation ZIP не создавались.

Входные manifests/wheel/workspace hashes совпали с PH-LW-07, drift отсутствует. [Входной baseline](PH_LW_08/INPUT_BASELINE.json), [snapshot CURRENT_TASK](PH_LW_08/CURRENT_TASK.before.md).

Allowed changes: public materialization helper, preparation orchestration/service/HTTP/UI, новые tests/native runner, точечное уточнение PH-LW-07 HTTP test запрета generic prepare без target, docs/README/mirror, metadata/wheel/manifests, новые evidence/reports и workspace navigation/tooling. Core schemas/registries/planner, Stage/level-up tests и исторические источники сохранены.

Реализованы approved-input/build-bound preparation, server-owned staging на destination volume, initial directory/ZIP/project validation и byte comparison, no-clobber publication, catalog registration после rename, explicit recovery, ровно один первый JIT и completion UI. Никаких manual файловых переносов. `LOCAL_WEB_MANUAL: NO-GO` до PH-LW-12; `AUTOMATIC_EXECUTOR: NO-GO`; полная v0.5.1 `NO-GO / NOT RELEASED`.

Фактическая приёмка: {new_count} новых target tests PASS; native Windows 11 x64/NTFS/non-admin/Python 3.14.10/Edge/Waitress TCP — {verdict['tests']} PASS / 0 SKIP, doctor/docs PASS. Installed wheel в отдельной venv/Unicode CWD — {wheel_count} PASS / 0 SKIP, console launcher/health PASS. Полная свежая matrix: {stats['modules']} модулей / {stats['test_methods']} methods, {stats['module_statuses'].get('PASS')} PASS / {stats['module_statuses'].get('PASS_WITH_SKIPS')} PASS_WITH_SKIPS / {stats['module_statuses'].get('FAIL')} FAIL, {stats['failure_events']} failure events / {stats['error_events']} error events / {stats['skips']} SKIP / {stats['timeouts']} TIMEOUT. Все 42 прежних модуля сохранили результаты; новых runtime regression failures нет. Native wrapper FAIL из-за generated metadata закрыт последующими doctor/docs PASS без изменения runtime source; исходный статус сохранён в отчёте.

Текущая распакованная база: build `{meta['local_web_build_id']}`, source digest `{meta['engine_build_digest']}`, wheel SHA-256 `{sha(wheel)}`. Docs mirror побайтово синхронизирован. Архивы поставки не обновлялись.

- [Фактический отчёт](../Project_Harness_Engine_v0.5.1/PH_LW_08_TEST_REPORT.md), [changed files](../Project_Harness_Engine_v0.5.1/PH_LW_08_CHANGED_FILES.md), [инварианты](../Project_Harness_Engine_v0.5.1/PH_LW_08_PRESERVED_INVARIANTS.md).
- [Операторская глава](../Project_Harness_Documentation_v0.5.1/13_Local_Web_Manual_Companion/15_PH_LW_08_Preparation_and_Publication.md), [evidence index](../Project_Harness_Engine_v0.5.1/PH_LW_08_LOGS/EVIDENCE_INDEX.json).
- [Финальная аттестация](PH_LW_08/FINAL_WORKING_TREE_VERIFICATION.json), [output hashes](PH_LW_08/SHA256.txt), [changed hashes](PH_LW_08/CHANGED_FILE_HASHES.json).

Отдельные PH-LW-04/05/06/07/08 verdicts PASS в их scopes. Открыты physical power-loss/storage-failure, clean-machine installer и весь manual lifecycle, positive governed per-Run egress/Podman. Partial staging сохраняется; publication вне native Windows не поддержана. Подробные NOT RUN и ограничения — в report.

Следующий шаг — только новое задание пользователя. PH-LW-09 не начат. Automatic executor не включать. ZIP поставки требуют отдельного запроса.
'''
    (ROOT/'_workspace/CURRENT_TASK.md').write_text(current,'utf-8')
    print(json.dumps({'native':verdict['tests'],'installed':wheel_count,**stats},indent=2))


if __name__=='__main__':main()
