from pathlib import Path
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[1]
text=(ROOT/'_workspace/DOCUMENT_ANALYSIS_UNIVERSALITY_2026-11-12/checkpoint.py').read_text('utf-8')
text=text.replace('_scratch/document_analysis_universality_20261112','_scratch/document_decision_options_20261112')
text=text.replace("=={'test_document_analysis_clarity.py'}", "=={'test_document_analysis_clarity.py','test_document_analysis_universality.py','test_manual_analysis_archive.py'}")
text=text.replace("=={'test_document_analysis_universality.py'}", "=={'test_document_decision_options.py'}")
text=text.replace('35_Project_Independent_Document_Analysis.md','36_Question_Decision_Options.md')
(OUT/'checkpoint.py').write_text(text,'utf-8')
(OUT/'stop_for_update.py').write_text((ROOT/'_workspace/DOCUMENT_ANALYSIS_UNIVERSALITY_2026-11-12/stop_for_update.py').read_text('utf-8'),'utf-8')
print('Prepared task-local delivery helpers')
