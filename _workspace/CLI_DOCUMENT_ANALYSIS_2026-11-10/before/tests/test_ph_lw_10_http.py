"""PH-LW-10 real Waitress TCP + Edge forms; no manufactured browser approvals."""
from copy import deepcopy
from pathlib import Path
import json
import os
import shutil
import tempfile
import unittest
from project_harness.local_web_lifecycle import view
from project_harness.serialization import load_data
from project_harness.stages import stage_status
from tests.test_ph_lw_04_05_acceptance import LiveServer
from tests.test_ph_lw_04_http import HAS_FLASK,HAS_WAITRESS,HAS_PLAYWRIGHT
from tests.test_ph_lw_03_service import byte_snapshot
from tests.test_ph_lw_10_lifecycle import public_fixtures,request,draft,payload,fill_maintenance


@unittest.skipUnless(HAS_FLASK and HAS_WAITRESS,'Real pinned Waitress required')
class LifecycleHttpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.gate,cls.accepted=public_fixtures()
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='LW10 TCP ');self.addCleanup(self.tmp.cleanup);self.base=Path(self.tmp.name)
        self.live=LiveServer(self.tmp.name);self.addCleanup(self.live.close);self.root=self.base/'project';shutil.copytree(self.gate,self.root)
        self.pid=self.live.service.register_existing(self.root,kind='project');self.baseurl='/api/projects/'+self.pid;self.live.ready()
    def test_auth_csrf_origin_port_unknown_fields_and_readonly(self):
        before=byte_snapshot(self.root)
        self.assertEqual(self.live.request('GET',self.baseurl+'/lifecycle',headers={'Origin':'http://foreign.invalid'})[0],403)
        for headers in ({'Origin':'null'},{'Host':'localhost:'+str(self.live.port)},{'Origin':'http://127.0.0.1:1'}):
            self.assertEqual(self.live.request('POST',self.baseurl+'/operations',value={},headers=headers)[0],403)
            self.assertEqual(self.live.request('POST','/api/local-selection',value={},headers=headers)[0],403)
        for _ in range(3):self.assertEqual(self.live.request('GET',self.baseurl+'/lifecycle')[0],200)
        self.assertEqual(self.live.request('POST','/api/local-selection',value={'path':'C:/Windows'})[0],400)
        self.assertEqual(before,byte_snapshot(self.root))
    def test_draft_ownership_traversal_replay_conflict(self):
        value={'action':'prepare-stage-approval','payload':{},'expected_fingerprint':view(self.live.service,self.pid)['fingerprint'],'idempotency_key':'tcp-draft-exact-replay'}
        response=self.live.request('POST',self.baseurl+'/operations',value=value);self.assertEqual(response[0],202,response)
        opid=response[2]['operation_id'];self.assertEqual(self.live.service.wait_for(opid,timeout=60)['state'],'SUCCEEDED')
        self.assertEqual(self.live.request('POST',self.baseurl+'/operations',value=value)[2]['operation_id'],opid)
        self.assertEqual(self.live.request('GET',self.baseurl+'/lifecycle/drafts/'+opid)[0],200)
        other=self.base/'other';shutil.copytree(self.accepted,other);pid=self.live.service.register_existing(other,kind='project')
        self.assertEqual(self.live.request('GET','/api/projects/'+pid+'/lifecycle/drafts/'+opid)[0],400)
        self.assertEqual(self.live.request('POST',self.baseurl+'/operations',value={**value,'payload':{'force':True}})[0],400)
        self.assertNotEqual(self.live.request('GET',self.baseurl+'/lifecycle/drafts/..%2f..%2fsecret')[0],200)


@unittest.skipUnless(HAS_FLASK and HAS_WAITRESS and HAS_PLAYWRIGHT,'Real pinned Edge required')
class LifecycleBrowserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.gate,cls.accepted=public_fixtures()
    def setUp(self):
        from playwright.sync_api import sync_playwright,expect
        expect.set_options(timeout=30000)
        self.tmp=tempfile.TemporaryDirectory(prefix='LW10 Edge Кириллица ');self.addCleanup(self.tmp.cleanup);self.base=Path(self.tmp.name)
        self.live=LiveServer(self.tmp.name);self.addCleanup(self.live.close)
        self.play=sync_playwright().start();self.addCleanup(self.play.stop)
        self.browser=self.play.chromium.launch(channel=os.environ.get('PH_LW_04_BROWSER_CHANNEL','msedge'),headless=True);self.addCleanup(self.browser.close)
        self.page=self.browser.new_page(viewport={'width':1440,'height':1050});self.page.set_default_timeout(30000)
        self.errors=[];self.urls=[];self.page.on('pageerror',lambda e:self.errors.append(str(e)));self.page.on('request',lambda r:self.urls.append(r.url))
    def open(self,source):
        from playwright.sync_api import expect
        self.root=self.base/'project';shutil.copytree(source,self.root);self.pid=self.live.service.register_existing(self.root,kind='project')
        self.page.goto(self.live.origin + '/');expect(self.page.locator('#connection-state')).to_have_text('Сервер готов')
        self.assertEqual(self.errors,[],self.errors)
        self.page.locator('.project-button').click();self.page.locator('[data-screen="gates"]').click()
        try:expect(self.page.locator('#lifecycle-summary')).not_to_have_text('Выберите проект.')
        except AssertionError:
            raise AssertionError({'page_errors':self.errors,'notice':self.page.locator('#notice').inner_text(),'requests':self.urls}) from None
    def prepare(self,action):
        from playwright.sync_api import expect
        try:self.page.locator('[data-lifecycle="'+action+'"]').click()
        except Exception as exc:
            raise AssertionError({'action':action,'page_errors':self.errors,'notice':self.page.locator('#notice').inner_text(),
                'summary':self.page.locator('#lifecycle-summary').inner_text(),'view':self.page.evaluate('state.view'),
                'context':self.page.locator('#lifecycle-context').inner_text()}) from exc
        expect(self.page.locator('#lifecycle-form-panel')).to_be_visible()
        expect(self.page.locator('#lifecycle-apply')).to_be_enabled()
    def field(self,path):return self.page.locator('[data-field="'+path+'"]')
    def apply(self):
        self.page.locator('#lifecycle-actor').fill('ACT-EDGE-LW10-REVIEWER');self.page.locator('#lifecycle-apply').click()
    def screenshot(self,name):
        folder=Path(os.environ.get('PH_LW_10_SCREENSHOT_DIR',str(self.base/'screenshots')));folder.mkdir(parents=True,exist_ok=True)
        self.page.screenshot(path=str(folder/name),full_page=True)
    def check_browser(self):
        self.assertEqual(self.errors,[]);self.assertTrue(all(u.startswith(self.live.origin+'/') for u in self.urls),self.urls)

    def test_edge_prototype_accept_alpha_form_plan_first_ready_reload(self):
        from playwright.sync_api import expect
        self.open(self.gate);before=byte_snapshot(self.root);self.page.reload(wait_until='networkidle');expect(self.page.locator('#lifecycle-summary')).to_contain_text('VERIFYING');self.assertEqual(before,byte_snapshot(self.root))
        self.prepare('prepare-stage-approval')
        # The actor selects every exact subject/result/source in the real form.
        model=json.loads(self.page.locator('#lifecycle-json').input_value())['stage_approval'];candidates={}
        for candidate in model['evidence_candidates']:
            for subject in candidate['compatible_subject_refs']:candidates[subject]=candidate['ref']
        for field,key in [('outcome_results','outcome_ref'),('criteria_results','criterion_ref'),('hard_constraint_results','constraint_ref'),('profile_control_results','control_ref')]:
            for i,item in enumerate(model[field]):
                prefix=f'stage_approval.{field}.{i}.'
                self.field(prefix+'status').select_option('PASS');self.field(prefix+'evidence_refs').select_option(candidates[item[key]])
                self.field(prefix+'rationale').fill('Reviewed exact fixture source for this subject.');self.field(prefix+'validator').fill('ACT-EDGE-LW10-REVIEWER')
        self.field('stage_approval.permitted_use.status').select_option('CONFIRMED')
        self.field('stage_approval.known_limitations').fill('Synthetic local CLI only. <img src="https://forbidden.invalid/x">')
        self.field('stage_approval.next_stage_gaps').fill('Review the next active Stage within accepted scope.')
        self.screenshot('stage-review.png');self.apply();expect(self.page.locator('#lifecycle-levels')).to_contain_text('ALPHA',timeout=90000)
        self.assertEqual(stage_status(self.root)['highest_accepted_level'],'PROTOTYPE')
        self.prepare('prepare-active-stage-plan');self.apply();expect(self.page.locator('#lifecycle-summary')).to_contain_text('READY_FOR_CODEX',timeout=90000)
        self.page.locator('[data-screen="tasks"]').click();expect(self.page.locator('#task-prompt')).not_to_have_value('');self.assertIn('ALPHA',self.page.locator('#task-prompt').input_value())
        self.screenshot('alpha-first-ready.png');self.check_browser()

    def test_edge_levelup_target_nearest_and_maintenance_cancel(self):
        from playwright.sync_api import expect
        self.open(self.accepted);self.prepare('prepare-maintenance')
        # Normal form covers all mandatory fields; no JSON import/private ref lookup.
        for path,value in {'objective':'Clarify current usage','rationale':'Same-level documentation',
             'work_package.title':'README maintenance','work_package.objective':'Document current CLI',
             'work_package.tasks.0.title':'Clarify README','work_package.tasks.0.purpose':'Current usage',
             'work_package.tasks.0.expected_result':'Reviewed README','work_package.tasks.0.produces_artifacts':'README.md',
             'work_package.tasks.0.scope.read':'README.md','work_package.tasks.0.scope.write':'README.md',
             'work_package.tasks.0.verification.expected_paths':'README.md','work_package.tasks.0.verification.manual_checks':'README describes current CLI',
             'work_package.tasks.0.acceptance_criteria':'README describes current CLI'}.items():self.field('maintenance_plan.'+path).fill(value)
        self.apply();expect(self.page.locator('#lifecycle-summary')).to_contain_text('MAINTENANCE',timeout=90000)
        self.prepare('prepare-maintenance-cancel');self.field('maintenance_cancel_approval.rationale').fill('Cancel before product changes.');self.apply();expect(self.page.locator('#lifecycle-summary')).to_contain_text('TARGET_LEVEL_REACHED',timeout=90000)
        self.prepare('prepare-level-up');self.field('level_up_approval.target_level').select_option('RELEASE');self.apply();expect(self.page.locator('#lifecycle-levels')).to_contain_text('ALPHA',timeout=90000)
        self.assertEqual(stage_status(self.root)['target_level'],'RELEASE');self.assertEqual(stage_status(self.root)['highest_accepted_level'],'PROTOTYPE');self.screenshot('level-up-nearest.png');self.check_browser()

    def test_edge_missing_semantic_review_cannot_accept(self):
        from playwright.sync_api import expect
        self.open(self.gate);self.prepare('prepare-stage-approval');self.apply()
        expect(self.page.locator('#lifecycle-operation')).to_contain_text('BLOCKED',timeout=60000)
        self.assertEqual(stage_status(self.root)['highest_accepted_level'],'NONE');self.check_browser()

    def test_edge_supported_migration_confirmation_and_restart_replay(self):
        from playwright.sync_api import expect
        from tests.test_engine import prepare_demo
        from tests.test_ph_051_10_migration_recovery import downgrade_to_v050
        root=prepare_demo(self.base/'legacy')[2];history=downgrade_to_v050(root)
        pid=self.live.service.register_existing(root,kind='migration')
        self.page.goto(self.live.origin + '/');expect(self.page.locator('#connection-state')).to_have_text('Сервер готов')
        self.page.locator('.project-button').click();self.page.locator('[data-screen="maintenance"]').click()
        expect(self.page.locator('[data-lifecycle="prepare-migration"]')).to_be_enabled();self.prepare('prepare-migration')
        self.apply();expect(self.page.locator('#lifecycle-operation')).to_contain_text('MIGRATED',timeout=90000)
        for rel,data in history.items():self.assertEqual((root/rel).read_bytes(),data)
        self.page.reload(wait_until='networkidle');self.prepare('prepare-migration');self.apply()
        expect(self.page.locator('#lifecycle-operation')).to_contain_text('NO_ACTION',timeout=90000)
        self.screenshot('migration-replay.png');self.check_browser()

    def test_edge_brownfield_assessment_unknown_and_stale_readonly(self):
        from playwright.sync_api import expect
        from tests.test_engine import load_fixture,add_brownfield_approval
        from project_harness.intake import start_intake
        from project_harness.serialization import write_data
        data=load_fixture();data['project']['mode']='BROWNFIELD';data['implementation']['claimed_current_level']='BETA';add_brownfield_approval(data)
        inp=self.base/'input.json';write_data(inp,data);repo=self.base/'repository';repo.mkdir();(repo/'README.md').write_text('# beta','utf-8')
        ws=self.base/'intake';start_intake(ws,project_name='Brownfield fixture',mode='BROWNFIELD',repository=repo,initial_input=inp)
        self.live.service.register_existing(ws,kind='workspace');before=byte_snapshot(repo)
        self.page.goto(self.live.origin + '/');expect(self.page.locator('#connection-state')).to_have_text('Сервер готов')
        self.page.locator('.project-button').click();self.page.locator('[data-screen="maintenance"]').click()
        self.page.on('dialog',lambda d:d.accept());expect(self.page.locator('[data-lifecycle="assess-maturity"]')).to_be_enabled()
        self.page.locator('[data-lifecycle="assess-maturity"]').click();expect(self.page.locator('#lifecycle-gaps')).to_contain_text('UNKNOWN',timeout=90000)
        self.assertEqual(before,byte_snapshot(repo));self.assertIn('highest_satisfied_candidate_level',self.page.locator('#lifecycle-gaps').inner_text())
        (repo/'README.md').write_text('# beta changed','utf-8');self.page.locator('#refresh').click()
        expect(self.page.locator('#lifecycle-context')).to_contain_text('"stale": true');expect(self.page.locator('[data-lifecycle="assess-maturity"]')).to_have_count(0)
        self.screenshot('brownfield-stale.png');self.check_browser()


if __name__=='__main__':unittest.main()
