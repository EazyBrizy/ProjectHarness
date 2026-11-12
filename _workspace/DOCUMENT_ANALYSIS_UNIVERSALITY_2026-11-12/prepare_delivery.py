from pathlib import Path
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[1]
old=(ROOT/'_workspace/DOCUMENT_ANALYSIS_CLARITY_2026-11-12/final_checkpoint.py').read_text('utf-8')
text=old.replace('_scratch/document_analysis_clarity_20261112','_scratch/document_analysis_universality_20261112')
text=text.replace("build=SCRATCH/'build03'", "build=SCRATCH/'build'").replace("before=SCRATCH/'before-final'", "before=SCRATCH/'before'")
for name in ('RUNTIME_FREEZE','BUILD_RESULT','INTEGRITY','OPERATOR_UPGRADE'):text=text.replace(name+'_FINAL.json',name+'.json')
start=text.index("    allowed=set(baseline['allowed_source'])")
end=text.index("    value={'status':'PASS'",start)
text=text[:start]+'''    assert changed==set(baseline['allowed_source']),changed^set(baseline['allowed_source'])
    tests=inventory(ENGINE/'tests')
    assert {n for n,h in baseline['tests'].items() if tests.get(n)!=h}=={'test_document_analysis_clarity.py'}
    assert set(tests)-set(baseline['tests'])=={'test_document_analysis_universality.py'}
    assert {n for n,h in baseline['docs'].items() if docs.get(n)!=h}=={'FILE_INDEX.md','MANIFEST.sha256'}
    assert set(docs)-set(baseline['docs'])=={'13_Local_Web_Manual_Companion/35_Project_Independent_Document_Analysis.md'}
'''+text[end:]
(OUT/'checkpoint.py').write_text(text,'utf-8')
stop=(ROOT/'_workspace/DOCUMENT_ANALYSIS_CLARITY_2026-11-12/stop_for_update.py').read_text('utf-8')
(OUT/'stop_for_update.py').write_text(stop,'utf-8')
print('Prepared current-task packaging helpers; historical files preserved')
