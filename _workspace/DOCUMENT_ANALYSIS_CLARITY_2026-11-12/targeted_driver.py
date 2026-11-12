import json, os, platform, sys, unittest
from pathlib import Path
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[1];ENGINE=ROOT/'Project_Harness_Engine_v0.5.1'
source='--source' in sys.argv
if source:sys.path.insert(0,str(ENGINE/'src'))
import project_harness
package=Path(project_harness.__file__).resolve().parent
if not source:
    from baseline import inventory
    assert package.is_relative_to(Path(sys.prefix).resolve()) and inventory(package)==inventory(ENGINE/'src/project_harness')
sys.path.insert(0,str(ENGINE))
os.environ['ANALYSIS_CLARITY_EVIDENCE']=str(ROOT/'_scratch/document_analysis_clarity_20261112/playwright')
names=[
 'tests.test_document_analysis_clarity.AnalysisContractTests.test_single_channel_dedupe_current_future_commit_and_reload_sources',
 'tests.test_document_analysis_clarity.AnalysisContractTests.test_conflicting_scope_notes_refs_bindings_and_approvals_rejected',
 'tests.test_document_analysis_clarity.AnalysisContractTests.test_existing_user_uncertainty_preserved_and_future_does_not_block',
 'tests.test_document_analysis_clarity.ModelSelectionTests.test_explicit_model_effort_snapshot_invalid_inputs_and_readonly_get',
 'tests.test_document_analysis_clarity.AnalysisBrowserTests.test_preview_answers_plan_sources_consistent_status_then_typed_saved_answers',
 'tests.test_document_analysis_clarity.AnalysisBrowserTests.test_model_selection_in_browser_autosaves_and_survives_reload',
 'tests.test_cli_document_analysis.CliAnalysisTests.test_gets_read_only_connect_fixed_commands_and_unknown_origin_rejected',
 'tests.test_cli_document_analysis.CliAnalysisTests.test_connection_auth_missing_changed_binary_and_stale_inputs_block_before_analysis',
 'tests.test_cli_document_analysis.CliAnalysisTests.test_result_uses_strict_preview_replay_does_not_rerun_and_draft_not_committed',
 'tests.test_cli_document_analysis.CliAnalysisTests.test_cancel_busy_stale_result_and_invalid_reply_never_apply_draft',
 'tests.test_cli_document_analysis.CliAnalysisTests.test_restart_projection_is_read_only_and_never_restarts_cli',
 'tests.test_manual_analysis_archive.ManualArchiveTests.test_single_archive_content_exact_binding_read_only_and_replay',
 'tests.test_manual_analysis_archive.ManualArchiveBrowserTests.test_one_click_zip_download_without_history_and_reply_still_previews',
]
if '--case' in sys.argv:names=[sys.argv[sys.argv.index('--case')+1]]
if '--focus' in sys.argv:names=[
 'tests.test_document_analysis_clarity.AnalysisContractTests.test_export_supplies_exact_consumable_profile_refs',
 'tests.test_document_analysis_clarity.ModelSelectionTests.test_explicit_model_effort_snapshot_invalid_inputs_and_readonly_get',
 'tests.test_document_analysis_clarity.AnalysisBrowserTests.test_preview_answers_plan_sources_consistent_status_then_typed_saved_answers']
print(json.dumps({'python':sys.version,'executable':sys.executable,'package':str(package),'platform':platform.platform(),
    'cwd':str(Path.cwd()),'source_import':source,'scope':names},ensure_ascii=False),flush=True)
result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromNames(names))
name=sys.argv[sys.argv.index('--result')+1] if '--result' in sys.argv else 'TARGETED_RESULTS.json'
path=OUT/name;assert not path.exists()
path.write_text(json.dumps({'ran':result.testsRun,'failures':[n.id() for n,_ in result.failures],
    'errors':[n.id() for n,_ in result.errors],'skips':len(result.skipped),'source_import':source,
    'status':'PASS' if result.wasSuccessful() and not result.skipped else 'FAIL'},indent=2)+'\n','utf-8')
raise SystemExit(not result.wasSuccessful() or bool(result.skipped))
