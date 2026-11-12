import json,os,platform,sys,unittest
from pathlib import Path
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[1];ENGINE=ROOT/'Project_Harness_Engine_v0.5.1'
if '--source' in sys.argv:sys.path.insert(0,str(ENGINE/'src'))
import project_harness
from baseline import inventory
package=Path(project_harness.__file__).resolve().parent
assert inventory(package)==inventory(ENGINE/'src/project_harness')
if '--source' not in sys.argv:assert package.is_relative_to(Path(sys.prefix).resolve())
sys.path.insert(0,str(ENGINE));os.environ['DECISION_OPTIONS_EVIDENCE']=str(ROOT/'_scratch/document_decision_options_20261112/playwright')
prefix='tests.test_document_decision_options.'
groups={'source':[
 prefix+'DecisionOptionsTests.test_strict_options_recommendation_values_and_legacy_envelopes',
 prefix+'DecisionOptionsTests.test_existing_questions_receive_options_without_duplicates_or_unblocking',
 prefix+'DecisionOptionsTests.test_selection_keep_open_append_custom_and_next_packet_context',
 prefix+'DecisionOptionsTests.test_replay_origin_tamper_stale_set_and_changed_sources',
 prefix+'DecisionOptionsTests.test_existing_commit_recovery_keeps_user_intent_before_and_after_atomic_write'],
 'wheel':[
 prefix+'DecisionOptionsBrowserTests.test_recommended_options_preview_single_click_custom_and_future',
 'tests.test_cli_document_analysis.CliAnalysisTests.test_result_uses_strict_preview_replay_does_not_rerun_and_draft_not_committed',
 'tests.test_manual_analysis_archive.ManualArchiveBrowserTests.test_one_click_zip_download_without_history_and_reply_still_previews',
 'tests.test_manual_analysis_archive.ManualArchiveTests.test_single_archive_content_exact_binding_read_only_and_replay',
 'tests.test_document_analysis_clarity.AnalysisBrowserTests.test_current_technology_question_has_typed_answer_and_resolution',
 'tests.test_document_analysis_universality.UniversalityBrowserTests.test_generic_structured_answers_from_schema_and_literal_identifiers']}
group=sys.argv[sys.argv.index('--group')+1] if '--group' in sys.argv else 'source'
names=groups[group]
if '--case' in sys.argv:names=[sys.argv[sys.argv.index('--case')+1]]
print(json.dumps({'python':sys.version,'executable':sys.executable,'package':str(package),'platform':platform.platform(),
    'cwd':str(Path.cwd()),'source_import':'--source' in sys.argv,'scope':names},ensure_ascii=False),flush=True)
result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromNames(names))
path=OUT/(sys.argv[sys.argv.index('--result')+1] if '--result' in sys.argv else 'SOURCE_RESULTS.json');assert not path.exists()
path.write_text(json.dumps({'status':'PASS' if result.wasSuccessful() and not result.skipped else 'FAIL','methods':names,
 'ran':result.testsRun,'failures':[n.id() for n,_ in result.failures],'errors':[n.id() for n,_ in result.errors],'skips':len(result.skipped)},indent=2)+'\n','utf-8')
raise SystemExit(not result.wasSuccessful() or bool(result.skipped))
