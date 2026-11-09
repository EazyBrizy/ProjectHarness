"""Record visual review and immutable diagnostic-attempt decisions."""
import hashlib,json
from pathlib import Path
from package_acceptance import ROOT

W=ROOT/'_workspace/PH_LW_12_FIX';S=ROOT/'_scratch/ph_lw_12_fix'
def save(name,value):
    (W/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n','utf-8')
def artifact(name,observation):
    path=S/name
    return {'file':path.relative_to(ROOT).as_posix(),
        'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'observation':observation}

save('VISUAL_QA.json',{'status':'PASS','method':'Direct visual inspection of final frozen EXE headless Edge screenshots',
    'limits':'Synthetic fixtures; screenshots supplement exact DOM/core assertions, not universal DLP.',
    'screenshots':[
        artifact('final05-installed-deep/screenshots/prepared-False.png','MD intake: ordinary deep Unicode path, selectable JIT, handoff controls visible.'),
        artifact('final05-installed-deep/screenshots/prepared-True.png','ZIP intake: deep Unicode path, correct reserved Task/Run, handoff controls visible.'),
        artifact('final05-installed-extended/screenshots/10/mvp-to-release.png','Stage panel STAGE_PLANNING_REQUIRED; target/active RELEASE; main status and selected card ACTIVE; highest accepted MVP.'),
        artifact('final05-installed-deep-full/installed-task-pass.png','Deep full manual flow: received COMPLETED result, separate manual evidence, independent verification PASS, completion button and current refs visible.')],
    'visible_browser_windows_opened':False,'fixture_credentials':'Only synthetic Task/Run/project refs; no live bootstrap/session/CSRF tokens displayed.'})
save('ATTEMPT_DECISIONS.json',{'policy':'Raw FAIL/ERROR/TIMEOUT/stopped diagnostics remain immutable. Only complete final05 freeze counts; all former results repeated.',
    'attempts':[
        {'candidate':'01','status':'SUPERSEDED; not credited','reason':'Deep published archive comparison and rename still used ordinary Windows IO; installer extended fixture also deadlocked on delayed read due serialized transport.',
            'process_stop_record':'CANDIDATE_01_STOPPED_PROCESSES.json','logs':['installed-deep.log','installed-extended.log']},
        {'candidate':'02','status':'SUPERSEDED; not credited','reason':'Deep control-plane scan falsely marked existing files deleted; actual 431 rejection status was received but subsequent Windows connection reset lost its already rejected body.',
            'process_stop_record':'CANDIDATE_02_STOPPED_PROCESSES.json','logs':['final-installed-deep.log','final-installed-extended.log']},
        {'candidate':'03','status':'Runtime PASS; package docs superseded','reason':'Windows matrix 459 PASS / 2 known capability SKIP; actual EXE passed. Final docs validator rejected missing addendum base date. Provisional report preserved, attestation not completed.'},
        {'candidate':'04','status':'Superseded; mandatory deep full E2E FAIL','reason':'Docs fixed; 22-method suite PASS, but deep full reload got INTERNAL_ERROR despite core publication SUCCEEDED. Isolated source/frozen repeats PASS did not close defect.'},
        {'candidate':'05','status':'FINAL CANDIDATE; verdict requires full current matrix and final validator','reason':'Real temp-file rename race reproduced with scheduling barrier. Two unchanged assertions give 2 ERROR before / 2 PASS after. Operation/preparation snapshots retain root/ownership/integrity without mutable canonical scan. All source/wheel/maturity/installer suites repeated.'}],
    'test_driver_corrections':[
        'Old fault test releases deliberately held GET before awaiting the next queued request. All previous assert/expect ASTs unchanged.',
        'Frozen HTTP fixture only tolerates response-body ConnectionResetError after exact HTTP431 status has already been parsed; resets before status and body failures on all other statuses still fail.',
        'Reference-assets before reproduction callback fixed; project blocked status expectation aligned to existing public BLOCKED enum; no production status semantics changed.',
        'External product-only agent and nonempty control snapshot use private native IO on deep test fixtures; no private approval/YAML mutation.'
    ],'build_wrapper_diagnostic':'build-04 and fixed-doc validator PASS; outer helper initially expected an aggregate change that did not occur. Separate exact three-file equivalence checker PASS; no runtime or test changes.',
    'platform':'Windows only','automatic_executor_enabled':False,'zip_pair_created':False})
print('VISUAL_QA and ATTEMPT_DECISIONS written')
