"""Generate a synthetic PH-LW-01 accepted-stage + active-maintenance fixture via public CLI.

Test-only source generator (NOT shipped as public GUI API). Explicit opt-in is mandatory:
  PYTHONPATH=src:. python local_web/fixtures/generate_advanced_state.py \
    --output /tmp/new-test-fixture-dir --test-only-synthetic-approval

This invokes real local test commands from the pre-existing PH-F06 fixtures; it is
NEVER acceptable as evidence/approval of a real user's project. The folder must
not exist; no destructive overwrite or usage of user Project Instances.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import json


def main() -> int:
    p = argparse.ArgumentParser(description='Create a synthetic accepted PROTOTYPE / maintenance Golden test state')
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--test-only-synthetic-approval', action='store_true')
    args = p.parse_args()
    if not args.test_only_synthetic_approval:
        p.error('Synthetic fixture can NEVER be used as real user approval; explicit test-only opt-in is required.')
    out = args.output.expanduser().resolve()
    if out.exists():
        p.error(f'Refuse to overwrite existing path: {out}')
    from project_harness.serialization import write_data
    from tests.ph_f06_fixtures import prepared, accept, cli
    from tests.maintenance_fixtures import maintenance_plan_document
    # Uses public CLI for state changes; test helpers supply bounded, specific
    # locally run verification sources. Does not directly mutate .harness.
    out.mkdir(parents=True)
    project = prepared(out / 'new', target='PROTOTYPE')
    result = accept(project, out / 'stage_records', 'PROTOTYPE')
    assert result['highest_accepted_level'] == 'PROTOTYPE'
    assert cli('next', '--project', project)['status'] == 'TARGET_LEVEL_REACHED'
    path = out / 'maintenance-test-only.json'
    write_data(path, maintenance_plan_document(project, suffix='PHLW01', task_count=1))
    started = cli('start-maintenance', '--project', project, '--plan', path)
    assert started['route'] == 'MAINTAIN_CURRENT_STAGE'
    status = cli('stage-status', '--project', project)
    assert status['highest_accepted_level'] == 'PROTOTYPE'
    validation = cli('validate-project', '--project', project)
    assert validation['status'] == 'PASS'
    receipt = {'fixture':'PH-LW-01-TEST-ONLY-SYNTHETIC-ACCEPTED-MAINTENANCE',
               'project_root':str(project), 'authoritative_test_only':False,
               'real_user_approval':False, 'real_external_compliance_evidence':False,
               'accepted_level':'PROTOTYPE','active_maintenance_route':started['route'],
               'public_cli_validation':validation['status'],
               'warning':'Synthetic test operator records do not authorize real projects.'}
    (out / 'TEST_ONLY_FIXTURE_RECEIPT.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(receipt,indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
