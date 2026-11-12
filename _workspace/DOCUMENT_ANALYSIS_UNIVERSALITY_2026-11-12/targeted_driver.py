import json,os,platform,sys,unittest
from pathlib import Path
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[1];ENGINE=ROOT/'Project_Harness_Engine_v0.5.1'
if '--source' in sys.argv:sys.path.insert(0,str(ENGINE/'src'))
import project_harness
package=Path(project_harness.__file__).resolve().parent
from baseline import inventory
assert inventory(package)==inventory(ENGINE/'src/project_harness')
if '--source' not in sys.argv:assert package.is_relative_to(Path(sys.prefix).resolve())
sys.path.insert(0,str(ENGINE))
os.environ['UNIVERSALITY_EVIDENCE']=str(ROOT/'_scratch/document_analysis_universality_20261112/playwright')
prefix='tests.test_document_analysis_universality.'
groups={'probe':[
 prefix+'UniversalityTests.test_arbitrary_names_counts_domains_exact_text_and_project_isolation',
 prefix+'UniversalityTests.test_distinct_code_units_unicode_and_repeated_topic_are_not_lost',
 prefix+'UniversalityBrowserTests.test_generic_structured_answers_from_schema_and_literal_identifiers'],
 'wheel':[
 prefix+'UniversalityBrowserTests.test_missing_plan_empty_lists_schema_enums_and_inert_source_text',
 'tests.test_document_analysis_clarity.AnalysisBrowserTests.test_preview_answers_plan_sources_consistent_status_then_typed_saved_answers',
 'tests.test_document_analysis_clarity.AnalysisBrowserTests.test_current_technology_question_has_typed_answer_and_resolution',
 'tests.test_ph_lw_06_exchange.ExchangeTests.test_unknowns_unsure_and_pending_approvals_cannot_become_ready']}
group=sys.argv[sys.argv.index('--group')+1] if '--group' in sys.argv else 'probe'
names=groups[group]
if '--case' in sys.argv:names=[sys.argv[sys.argv.index('--case')+1]]
print(json.dumps({'python':sys.version,'executable':sys.executable,'package':str(package),'cwd':str(Path.cwd()),
 'platform':platform.platform(),'source_import':'--source' in sys.argv,'scope':names},ensure_ascii=False),flush=True)
result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromNames(names))
path=OUT/(sys.argv[sys.argv.index('--result')+1] if '--result' in sys.argv else 'PROBE_RESULTS.json');assert not path.exists()
path.write_text(json.dumps({'status':'PASS' if result.wasSuccessful() and not result.skipped else 'FAIL',
 'methods':names,'ran':result.testsRun,'failures':[n.id() for n,_ in result.failures],
 'errors':[n.id() for n,_ in result.errors],'skips':len(result.skipped)},indent=2)+'\n','utf-8')
raise SystemExit(not result.wasSuccessful() or bool(result.skipped))
