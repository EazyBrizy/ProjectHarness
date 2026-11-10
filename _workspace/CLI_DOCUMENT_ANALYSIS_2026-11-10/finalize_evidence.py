"""Finish only navigation/evidence; no model calls, runtime mutation or tests."""
import hashlib
import json
from pathlib import Path

OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
(OUT/'PROGRESS.md').write_text('''# Итог 2026-11-10

Работа завершена. Build CLI-DOC-ANALYSIS-20261110 установлен, обычный ярлык обновлён, dev shortcut сохраняет запуск src без переустановки. Данные и previous version сохранены. Пользовательский сервер остановлен штатным POST; видимых окон не открывали.

Два способа документационного анализа: подключённый CLI возвращает предложения в браузер; ручной пакет создаётся одним нажатием. Категорий документов/черновика, local login и лишних подтверждений нет. Только документация, product Task automation отложен. Exact PREVIEW, revision/replay checks, secret scan и restricted-project policy сохранены, direct пакет UNCLASSIFIED.

Final independent installed wheel: 10 PASS, 0 FAIL/ERROR/SKIP (8 CLI/HTTP/process + 2 real TCP/headless Edge метода). Native CLI final03: actual Codex 0.154.0, synthetic MD only, 1 PREVIEW, canonical draft unchanged, command events 0, unrelated MCP startup false. Source pilot failures и причины сохранены в REPORT.md. Новый запуск модели после final03 не требовался.

Docs validator/mirrors/manifests/wheel CRC/frozen payload включая .pyd/installed package/doctor PASS. Full engine/core/PH-LW matrix и actual installed-EXE browser reacceptance NOT RUN. Automatic Task executor disabled / прежний NO-GO; full v0.5.1 NOT RELEASED; ZIP не создавались. См. REPORT.md, RUNTIME_FREEZE.json, OUTPUT_HASHES.json, INTEGRITY.json, OPERATOR_UPGRADE.json.

Следующий разрешённый шаг: открыть прежний ярлык → Опрос и GPT → выбрать CLI-анализ либо ручной пакет. Другие этапы не выполнять.
''','utf-8')
for file in ('WHEEL_RESULTS.json','NATIVE_ANALYSIS_RESULT-03.json','INTEGRITY.json','OPERATOR_UPGRADE.json'):
    assert json.loads((OUT/file).read_text('utf-8'))['status']=='PASS',file
freeze=json.loads((OUT/'RUNTIME_FREEZE.json').read_text('utf-8'))
data={'status':'COMPLETE','build_id':freeze['build_id'],
      'tested_scope':'Only the changed CLI/document-analysis feature and packaging boundary',
      'full_engine_core_matrix':'NOT RUN — no user request; targeted checks only',
      'actual_installed_exe_browser':'NOT RUN — installed bytes/package/doctor verified, browser on installed wheel',
      'AUTOMATIC_EXECUTOR':'DISABLED / previous NO-GO','full_v0_5_1':'NOT RELEASED',
      'report_sha256':sha(OUT/'REPORT.md'),'current_task_sha256':sha(ROOT/'_workspace/CURRENT_TASK.md'),
      'agent_instructions_sha256':sha(ROOT/'AGENTS.md'),'zip_created':False}
(OUT/'FINAL_ATTESTATION.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n','utf-8')
index={p.relative_to(OUT).as_posix():sha(p) for p in sorted(OUT.rglob('*'))
       if p.is_file() and p.name!='EVIDENCE_INDEX.json' and '__pycache__' not in p.parts and p.suffix!='.pyc'}
(OUT/'EVIDENCE_INDEX.json').write_text(json.dumps({'files':index,'self_hash_omitted':True},ensure_ascii=False,indent=2)+'\n','utf-8')
print(json.dumps({'status':data['status'],'build_id':freeze['build_id'],'evidence_files':len(index),'zip_created':False}))
