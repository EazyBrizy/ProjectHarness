"""Publish PH-LW-09 completed logs, matrix and report; never package ZIPs."""
from collections import Counter
import hashlib,json,re
from pathlib import Path
from package_acceptance import ROOT,ENGINE,DOCS,files
from finalize_evidence import sanitize
S=ROOT/'_scratch/ph_lw_09';O=ENGINE/'PH_LW_09_LOGS';W=ROOT/'_workspace/PH_LW_09'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text('utf-8'))
def save(p,v):p.write_text(sanitize(json.dumps(v,ensure_ascii=False,indent=2))+'\n','utf-8')

def main():
    frozen=read(S/'FINAL_BUILD_FREEZE.json');source=ENGINE/'src/project_harness'
    assert frozen['source_hashes']=={p.relative_to(source).as_posix():sha(p) for p in files(source)}
    assert sha(ENGINE/'dist/project_harness_engine-0.5.1-py3-none-any.whl')==frozen['wheel_sha256']
    native=read(S/'native-verified/PH_LW_09_WINDOWS_TEST_REPORT.json')
    installed=read(S/'runs/installed-wheel-verified.run.json')
    assert native['status']=='PASS' and installed['status']=='PASS',(native,installed)
    check=native['checks'][0];assert not check['skips']
    log=(S/'native-verified/stage_tests.log').read_text('utf-8')
    counts=Counter(re.findall(r'^test\S+ \((tests\.[^.]+)\.[^)]+\) \.\.\.',log,re.M))
    assert sum(counts.values())==check['ran']
    command=read(S/'runs/native-verified.run.json')['command']
    rows=read(S/'core-regressions/MATRIX.json')
    for row in rows:row['evidence']='core-regressions/'+row['log']
    rows += [{'module':module,'command':command,'status':'PASS','ran':count,'failures':0,'errors':0,'skips':[],
        'log':'native-verified/stage_tests.log','evidence':'native-verified/PH_LW_09_WINDOWS_TEST_REPORT.json',
        'platform':native['platform']} for module,count in counts.items()]
    assert {r['module'] for r in rows}=={'tests.'+p.stem for p in (ENGINE/'tests').glob('test_*.py')}
    assert len(rows)==len({r['module'] for r in rows})
    prior={x['module']:x for x in read(ENGINE/'PH_LW_08_LOGS/REGRESSION_MATRIX_CURRENT.json')['rows']}
    comparisons=[];failure_ids=[]
    blocker_module='tests.test_ph_f06_maturity_lifecycle'
    for row in rows:
        if row['module'] not in prior:assert row['status']=='PASS';continue
        old=prior[row['module']]
        diffs={k:{'previous':old[k],'current':row[k]} for k in ('status','ran','failures','errors') if old[k]!=row[k]}
        if len(old['skips'])!=len(row['skips']):diffs['skips']={'previous':len(old['skips']),'current':len(row['skips'])}
        comparisons.append({'module':row['module'],'differences':diffs})
        if row['status']=='FAIL':
            def ids(p):return sorted(re.findall(r'^(?:FAIL|ERROR): (.+)$',p.read_text('utf-8'),re.M))
            old_ids=ids(ENGINE/'PH_LW_08_LOGS/core-regressions'/old['log'])
            new_ids=ids(S/'core-regressions'/row['log'])
            failure_ids.append({'module':row['module'],'inherited_failure':old['status']=='FAIL','same_failed_test_ids':old_ids==new_ids,'previous':old_ids,'current':new_ids})
    changed=[x for x in comparisons if x['differences']]
    assert len(changed)==1 and changed[0]['module']==blocker_module,changed
    assert changed[0]['differences']=={'status':{'previous':'PASS','current':'FAIL'},'ran':{'previous':13,'current':9},'errors':{'previous':0,'current':1}},changed
    assert all(x['same_failed_test_ids'] for x in failure_ids if x['inherited_failure']),failure_ids
    not_run=[f'{blocker_module}.PHF06MaturityLifecycleTests.{name}' for name in (
        'test_01_greenfield_all_four_stages_have_verified_immutable_acceptances',
        'test_02_maintenance_complete_level_up_release_and_idempotent_replay',
        'test_03_lower_equal_targets_noop_and_skip_rejected_without_history_changes',
        'test_04_new_level_up_cannot_reset_an_unfinished_cycle_or_active_run')]
    stats={'modules':len(rows),'test_methods':sum(x['ran'] for x in rows),'module_statuses':dict(Counter(x['status'] for x in rows)),
        'failure_events':sum(x['failures'] for x in rows),'error_events':sum(x['errors'] for x in rows),
        'skips':sum(len(x['skips']) for x in rows),'timeouts':sum(x['status']=='TIMEOUT' for x in rows),
        'not_run_due_to_setup_error':not_run}
    wheel_log=(S/'runs/installed-wheel-verified.log').read_text('utf-8')
    wheel_count=int(re.search(r'Ran (\d+) tests',wheel_log).group(1))
    assert '"source_import": false' in wheel_log and '"skips": 0' in wheel_log
    O.mkdir(exist_ok=True);index=[]
    groups={'runs','native-final','native-verified','core-regressions','screenshots-initial','screenshots-revised','screenshots-third','screenshots-fourth','screenshots-native','screenshots-wheel','screenshots-verified','screenshots-wheel-verified'}
    for raw in sorted(S.rglob('*')):
        if not raw.is_file() or raw.suffix not in {'.log','.json','.png','.md'}:continue
        relative=raw.relative_to(S)
        if len(relative.parts)>1 and relative.parts[0] not in groups:continue
        target=O/relative;target.parent.mkdir(parents=True,exist_ok=True)
        if raw.suffix=='.png':target.write_bytes(raw.read_bytes())
        else:target.write_text(sanitize(raw.read_text('utf-8',errors='replace')),'utf-8')
        index.append({'raw_source':raw.relative_to(ROOT).as_posix(),'file':relative.as_posix(),'raw_sha256':sha(raw),'published_sha256':sha(target)})
    save(O/'EVIDENCE_INDEX.json',index)
    save(O/'REGRESSION_MATRIX_CURRENT.json',{'status':'FAIL','provenance':'Fresh core modules plus final native combined suite; no inherited results substituted',**stats,'rows':sorted(rows,key=lambda x:x['module'])})
    save(O/'PREVIOUS_BASELINE_COMPARISON.json',{'status':'NEW_MANUAL_LIFECYCLE_BLOCKER','unchanged_modules':43,'changed_modules':changed,'rows':comparisons,'failed_test_ids':failure_ids})
    verdict={'status':'PASS','tests':check['ran'],'skips':[],'source':'native-verified/PH_LW_09_WINDOWS_TEST_REPORT.json',
        'installed_wheel_tests':wheel_count,'installed_source':'runs/installed-wheel-verified.run.json','native_wrapper_status':native['status']}
    save(O/'NATIVE_SCOPE_VERDICT.json',verdict)
    save(O/'BUILD_PROVENANCE.json',{'build_id':'PH-LW-09-20261107','engine_build_digest':frozen['engine_build_digest'],
        'wheel_sha256':frozen['wheel_sha256'],'input':read(W/'INPUT_BASELINE.json'),'zip_created':False})
    target_count=sum(x['ran'] for x in rows if x['module'] not in prior)
    report=f'''# PH-LW-09 — фактический отчёт

Дата: 2026-11-07. **PH-LW-09: NO-GO — новый manual lifecycle blocker.** Код, целевые tests, документация и приёмка полного prompt r2 выполнены на распакованной проверенной базе PH-LW-08; этап не принят из-за описанного ниже regression. Automatic executor выключен; PH-LW-10 не выполнялся; Engine/Documentation ZIP не создавались. Handoff ZIP внутри тестовых compiler fixtures — штатный продуктовый output, не архив поставки Engine.

## База и изменения

Входные Engine manifest `dbccdd6a9d4b0f505aa6626e157aebd171dc6e9a1d4c19c075cfd797cc874802`, Documentation manifest `8124e124f2fcae5207cd1e68f0559608120f7815888e02904e4a665a7b6885ec`, wheel `91367028938d984b0c5f91a6dba9fe953a888d6cd9c9944ccb94cb9f6e94049e` совпали; drift отсутствовал. [Baseline](../_workspace/PH_LW_09/INPUT_BASELINE.json), [input hashes](../_workspace/PH_LW_09/INPUT_FILE_HASHES.json). Правило пользователя о работе без ZIP заменяет историческое требование r2; исторические источники не переписаны.

Allowed changes: public manual Task/result API, Local Web Task orchestration/service/HTTP/UI, прямые manual fixes в runtime/result reader, новые tests/runner, docs/mirror, metadata/wheel/manifests, новые evidence и workspace navigation/tooling. [Changed files](PH_LW_09_CHANGED_FILES.md), [сохранённые инварианты](PH_LW_09_PRESERVED_INVARIANTS.md).

Реализованы current-stage Work Packages/Tasks/dependencies, canonical future Stage Plan outlines, exact Task/Run/JIT/context previews, read-only copy, idempotent next. Private upload либо exact canonical result channel проходит strict JSON/schema/ref/path/baseline validation и kernel ingestion. Один неизменяемый result на Run; claim агента, independent PASS и Task completion различаются. Verification consent bound к current Run/product/plan digest, показывает точные argv/cwd/timeout и host-code предупреждение. Без consent команды не запускаются; toolchain не устанавливается. Реальные gates/diff/errors отображаются без повышения статуса. Block/resume требует reason/resolution, exact OPEN blocker revision и актуальный fingerprint. Safety recovery fail-closed. Automatic projects не переключаются в manual.

Прямые обнаруженные core defects: `allow_manual:true` считался доказательством manual checks; теперь непустые checks без поддержанного evidence остаются BLOCKED. Повторный verify перезаписывал report перед отказом immutable evidence; теперь каждый check получает отдельные exact report/evidence refs, прежние байты сохранены. Host verify также отклоняет ещё READY automatic policy до первого automatic phase. Result reader отвергает duplicate JSON keys/nonfinite constants. Core schemas/registries, Stage planner и semantic evidence contract не изменены.

## Фактическая приёмка

| Run | Результат |
|---|---|
| Новые PH-LW-09 modules | {target_count} methods PASS, 0 SKIP |
| Native Windows suite PH-LW-04–09 | {check['ran']} PASS, 0 SKIP; wrapper/doctor/docs PASS |
| Installed wheel, отдельная venv и Unicode CWD | {wheel_count} PASS, 0 SKIP; site-packages import, console doctor/launcher и TCP health PASS |
| Полная свежая matrix | {stats['modules']} modules / {stats['test_methods']} methods; {stats['module_statuses'].get('PASS',0)} PASS / {stats['module_statuses'].get('PASS_WITH_SKIPS',0)} PASS_WITH_SKIPS / {stats['module_statuses'].get('FAIL',0)} FAIL |
| Failure/error/skip/timeout events | {stats['failure_events']} / {stats['error_events']} / {stats['skips']} / {stats['timeouts']} |
| Обязательные методы NOT RUN из-за setUpClass ERROR | 4 метода PHF06MaturityLifecycleTests; незакрытый gate |

Стенд: настоящий Windows 11 x64, NTFS, non-admin, Python 3.14.10 x64, Flask 3.1.3, Waitress 3.0.2, реальный Edge/TCP. [Native report](PH_LW_09_LOGS/native-verified/PH_LW_09_WINDOWS_TEST_REPORT.json), [source environment](PH_LW_09_LOGS/SOURCE_ENVIRONMENT.json), [wheel environment](PH_LW_09_LOGS/WHEEL_ENVIRONMENT.json). Команды, CWD, timeout, exit и log hashes — [evidence index](PH_LW_09_LOGS/EVIDENCE_INDEX.json) и `runs/*.run.json`. Полный [matrix](PH_LW_09_LOGS/REGRESSION_MATRIX_CURRENT.json) сохраняет унаследованные FAIL/SKIP; [сравнение](PH_LW_09_LOGS/PREVIOUS_BASELINE_COMPARISON.json) подтверждает одинаковые результаты 43 из 44 прежних модулей и одинаковые failed test IDs семи прежних FAIL-модулей. Новый восьмой FAIL — PH-F06, не automatic/Podman blocker и не основание объявить весь этап PASS.

## Новый blocker: отсутствует поддержанный Task-level manual proof

`tests.test_ph_f06_maturity_lifecycle` ранее PASS: 13 methods; сейчас 9 methods, один `setUpClass ERROR`, четыре обязательных метода NOT RUN. [Полный log](PH_LW_09_LOGS/core-regressions/test_ph_f06_maturity_lifecycle.log). `active_stage_planning.py` создаёт обычные Tasks с непустым `manual_checks` и `allow_manual:true`. Fixture `ph_f06_fixtures.complete_task` вызывает verify до предоставления независимого manual proof; отдельные Stage sources создаются позже и не доказывают конкретный Task check. Прежний runtime считал один флаг permission достаточным для PASS. PH-LW-09 прямо запрещает PASS для missing manual checks, поэтому исправленный runtime возвращает BLOCKED, а существующий lifecycle fixture больше не проходит.

Это реальный blocker manual пути после PROTOTYPE, а не допустимый унаследованный automatic NO-GO. Возврат shortcut, подавление ошибки, удаление manual checks или ослабление старого теста не применялись. Planner, schemas/registries и исторический PH-F06 PASS оставлены неизменными. В принятом core contract нет Task-level intake evidence для таких свободно заданных checks. Произвольный новый proof schema/API или перенос Stage approval в Task completion изменили бы контракт; такой change не выполнялся молча. До согласованного решения и positive/negative/recovery coverage PH-LW-09 остаётся NO-GO. Следующий разрешённый предмет работы — этот blocker, только по отдельному заданию, без автоматического перехода к PH-LW-10.

В Edge явный fixture external agent реально изменяет продукт, затем браузер выполняет upload → received → no-consent BLOCKED → consent → real verify PASS → complete → next, без private Python editing canonical state. Второй браузерный путь проверяет failing exit 9 → block → exact-ref resume. Fixture запись файла — действие тестового внешнего исполнителя, не evidence реального Codex/Podman. Негативные tests: forged/wrong/stale refs, changed result/baseline, forbidden writes, control tamper до intake и из verification command, missing tools/dependencies/paths, unknown fields, hardlink, consent/plan mismatch, foreign upload, duplicate click/multi-tab, partial publication и ambiguous recovery без повторного запуска команд. Fault-injection fixtures явно отделены от позитивного публичного маршрута.

Ранние FAIL сохранены: неверное использование Windows directory preflight для файла; некорректная automatic fixture без профилей; UI refresh race; повторная verification с прежним immutable evidence ID; docs README распознавался validator как неизвестный prefix NO; setup logger не сериализовал Path. Исправлены реализация/fixtures/тексты, semantic ожидания не ослаблены. Browser expectation timeout приведён к 30 секундам для реальных операций. Промежуточные native/wheel runs остановлены после обнаружения пропуска future outlines, отмечены INTERRUPTED отдельным record; их raw FAIL exits не переписаны. Финальные suites выполнены на зафиксированной сборке последовательно. Core suite начат до read-only outline дополнения; его core runtime исходники не менялись, финальный native/wheel проверяет окончательный Local Web source.

Одна ранняя одиночная диагностика не имеет отдельного сохранённого raw stdout; причина и граница evidence зафиксированы в [diagnostic note](PH_LW_09_LOGS/EARLY_DIAGNOSTIC_NOTE.md). Её результат не использован для acceptance verdict.

В native stdout сохранены Waitress queue diagnostics и два `WinError 10038` при обслуживании/закрытии тестового сервера; аналогичные две записи есть в предыдущем PH-LW-08 native log. Они не скрыты: runner завершил 143 tests без unittest errors/failures и с exit 0. Это наблюдение о тестовом harness, не отдельное доказательство корректности всех сценариев shutdown.

## Итоговые файлы и открытые gates

Build `PH-LW-09-20261107`; source digest `{frozen['engine_build_digest']}`; wheel SHA-256 `{frozen['wheel_sha256']}`. Docs mirror побайтово совпадает; build/lib и wheel сгенерированы из src. [Финальная аттестация](../_workspace/PH_LW_09/FINAL_WORKING_TREE_VERIFICATION.json), [output hashes](../_workspace/PH_LW_09/SHA256.txt), [изменённые hashes](../_workspace/PH_LW_09/CHANGED_FILE_HASHES.json).

Отдельные verdicts PH-LW-04/05/06/07/08 — PASS в их scopes; новые PH-LW-09 target/native/wheel checks PASS, **PH-LW-09 в целом NO-GO** из-за manual lifecycle blocker. `LOCAL_WEB_MANUAL: NO-GO` до закрытия blocker и PH-LW-12; `AUTOMATIC_EXECUTOR: NO-GO`; полная v0.5.1 `NO-GO / NOT RELEASED`. NOT RUN: четыре метода PH-F06 после setUpClass ERROR, physical power-loss/storage-failure, clean-machine installer, реальный внешний Codex, полный lifecycle PH-LW-10–12, positive governed per-Run egress и rootless Podman security acceptance. Неоднозначный interrupted commit требует canonical диагностики и не auto-replay; task-level manual evidence ingestion вне текущего core contract, такие checks блокируют completion. Staged uploads остаются private/bounded; не входят в поставку. Следующий шаг — только новое задание пользователя; PH-LW-10 не начат.
'''
    (ENGINE/'PH_LW_09_TEST_REPORT.md').write_text(report,'utf-8')
    (ENGINE/'PH_LW_09_PRESERVED_INVARIANTS.md').write_text('''# PH-LW-09 — сохранённые инварианты

- MANUAL_HANDOFF default; automatic executor, host agent fallback, Podman/egress, provider/LAN/generic exec не активированы.
- Browser → authenticated POST/service/operation guard → public Engine API → canonical .harness; GET/polling read-only.
- Exact Run/Task/JIT/snapshot/result/product/plan binding; отдельный одноразовый consent, idempotency и stale conflict.
- Agent COMPLETED не independent PASS; PASS не Task completion; Task completion не Stage acceptance.
- Sequential levels, accepted scope, current-stage fence, future outlines, immutable accepted history и semantic evidence сохранены.
- Повторный verify создаёт новые report/evidence refs; прошлые checks не перезаписываются. Missing manual proof остаётся BLOCKED.
- Safety blockers не возобновляются in-place. Неоднозначный recovery не повторяет команды.
- Core schemas/registries/planner, нормативные specs/r2, старые tests/reports/archives сохранены; ZIP поставки не создавались.

Доказательства: [report](PH_LW_09_TEST_REPORT.md), [аттестация](../_workspace/PH_LW_09/FINAL_WORKING_TREE_VERIFICATION.json).
''','utf-8')
    before=read(W/'INPUT_FILE_HASHES.json')
    changed=[p.relative_to(ROOT).as_posix() for folder in (source,ENGINE/'tests',ENGINE/'local_web',DOCS) for p in files(folder) if before.get(p.relative_to(ROOT).as_posix())!=sha(p)]
    (ENGINE/'PH_LW_09_CHANGED_FILES.md').write_text('# PH-LW-09 — изменения\n\n'+ '\n'.join('- `'+x+'`' for x in changed)+'\n\nТакже новые reports/evidence, README/workspace navigation/tooling и generated build/lib/dist/egg-info/docs mirror/manifests. Полные input/output hashes: [CHANGED_FILE_HASHES.json](../_workspace/PH_LW_09/CHANGED_FILE_HASHES.json).\n','utf-8')
    (O/'README.md').write_text('# PH-LW-09 evidence\n\n`native-verified` и `installed-wheel-verified` — финальные runs; `core-regressions` — полная свежая оставшаяся matrix. Ранние FAIL и INTERRUPTED сохранены отдельно. Только synthetic fixtures; uploads/auth/cache/venv не публикуются. Raw/published hashes — EVIDENCE_INDEX.json.\n','utf-8')
    (W/'RESULT_SUMMARY.json').write_text(json.dumps({'stage_verdict':'NO-GO','blocker':blocker_module,'native':verdict,'matrix':stats,'new_tests':target_count},indent=2)+'\n','utf-8')
    print(json.dumps({'evidence_publication':'PASS','stage_verdict':'NO-GO','native':verdict,'matrix':stats},indent=2))

if __name__=='__main__':main()
