"""Public PH-LW-09 manual Task API. Kernel owns ingestion and phase boundaries.

These APIs never dispatch an agent. Uploaded results are untrusted claims;
receipts bind bytes, exact Run/Task, Run snapshot and current product baseline.
"""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import shutil
from typing import Any

from .errors import ValidationFailure, SafetyViolation
from .operation_guard import guarded_mutation, project_operation_guard
from .platform_fs import ensure_native_path, safe_relative, _native_io_path, native_resolve
from .serialization import canonical_json_bytes, load_data, write_data
from .hashing import sha256_file
from .util import resolve_inside, utc_now
from .workspace import (AGENT_RESULT_MAX_BYTES, snapshot_product, check_control_plane,
    secure_read_agent_result, assert_agent_result_unchanged, record_phase_boundary, load_phase_boundary)
from . import runtime


def digest(value: Any) -> str:
    return 'sha256:' + hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def _read(root: Path, relative: str) -> Any:
    safe_relative(relative, field='canonical artifact')
    path = resolve_inside(root, relative)
    ensure_native_path(path.parent)
    if not _native_io_path(path).is_file() or _native_io_path(path).is_symlink() or _native_io_path(path).stat().st_nlink != 1 or _native_io_path(path).stat().st_size > 8*1024*1024:
        raise ValidationFailure('TASK_ARTIFACT_INVALID')
    return load_data(path)


def _policy(root: Path) -> str:
    return _read(root, '.harness/config/PROJECT_LOCK.yaml')['project_lock'].get('execution', {}).get('mode', 'MANUAL_HANDOFF')


def _active(root: Path) -> dict:
    ensure_native_path(root, tree=True)
    active = runtime._state(root)[1]['state'].get('active_run')
    if _policy(root) != 'MANUAL_HANDOFF' or (active and runtime.automatic_run_phase(root, active)):
        raise ValidationFailure('AUTOMATIC_DISABLED: внешний manual result не закрывает automatic Run')
    if not isinstance(active, dict):
        raise ValidationFailure('NO_ACTIVE_RUN')
    if check_control_plane(root, active)['status'] != 'PASS':
        raise SafetyViolation('CONTROL_TAMPER: восстановите доверенное состояние; in-place resume запрещён')
    return active


def _dependencies(root: Path, task: dict) -> None:
    state = runtime._state(root)[1]['state']
    completed = {str(ref).split('@')[0] for ref in state.get('completed_task_refs') or []}
    if not set(task.get('depends_on_tasks') or []).issubset(completed):
        raise ValidationFailure('TASK_DEPENDENCIES_MISSING')


@guarded_mutation
def next_manual_task(root: Path) -> dict:
    state = runtime._state(root)[1]['state']
    if _policy(root) != 'MANUAL_HANDOFF': raise ValidationFailure('AUTOMATIC_DISABLED')
    if state.get('active_run'): _active(root)
    route = runtime.project_status(root)['next_operator_route']['route']
    if route not in {'RESERVE_READY_TASK','VERIFY_CURRENT_TASK','COMPLETE_VERIFIED_TASK'}:
        raise ValidationFailure('TASK_ROUTE_UNAVAILABLE: Stage actions require a separate workflow')
    task = runtime._task(root,state['current_task_ref'])[0]
    _dependencies(root,task)
    return runtime.next_task(root)


def _binding(root: Path, active: dict) -> dict:
    return {'run_ref': active['run_ref'], 'task_ref': active['task_ref'],
        'snapshot_ref': active['snapshot_ref'], 'snapshot_sha256': 'sha256:'+sha256_file(root/active['snapshot_path']),
        'product_baseline': digest(snapshot_product(root))}


def _receipt_path(active: dict) -> str:
    return '.harness/runtime/MANUAL_RESULTS/' + active['run_ref'] + '.json'


def _receipt(root: Path, active: dict) -> dict | None:
    relative = _receipt_path(active)
    if not (_native_io_path(root/relative)).exists(): return None
    value = _read(root, relative)
    if value.get('schema') != 'LOCAL_MANUAL_RESULT_RECEIPT_V1' or value.get('binding') != _binding(root, active):
        raise ValidationFailure('STALE_RESULT_BASELINE: результат привязан к другой версии продукта')
    _, raw_digest, _ = secure_read_agent_result(root, active['allowed_agent_output_path'])
    if raw_digest != value.get('result_sha256'):
        raise ValidationFailure('RESULT_CHANGED: полученный result изменился')
    return value


def parse_result(raw: bytes, active: dict) -> dict:
    if not isinstance(raw, bytes) or not 0 < len(raw) <= AGENT_RESULT_MAX_BYTES:
        raise ValidationFailure('RESULT_INVALID: лимит 1 MiB')
    def pairs(items):
        obj = {}
        for key, value in items:
            if key in obj: raise ValueError('duplicate key')
            obj[key] = value
        return obj
    def constant(value): raise ValueError('nonfinite number')
    try: value = json.loads(raw.decode('utf-8'), object_pairs_hook=pairs, parse_constant=constant)
    except (UnicodeError, ValueError, RecursionError) as exc: raise ValidationFailure('RESULT_INVALID: strict JSON required') from exc
    try: runtime._validate_agent_result(value, active)
    except (TypeError, ValueError) as exc: raise ValidationFailure('RESULT_INVALID: schema types') from exc
    for paths in value['changes'].values():
        if len(paths) != len(set(paths)): raise ValidationFailure('RESULT_INVALID: duplicate paths')
        for path in paths: safe_relative(path, field='result change', windows=True)
    if type(value['schema_version']) is not int or any(not isinstance(x, str) for x in value.get('stage_scope_violations', [])):
        raise ValidationFailure('RESULT_INVALID: strict schema types required')
    return value


def validate_manual_result(root: Path, raw: bytes, *, binding_digest: str) -> dict:
    """Read-only admission; publication always revalidates inside the fence."""
    with project_operation_guard(root):
        active = _active(root)
        binding = _binding(root, active)
        if digest(binding) != binding_digest: raise ValidationFailure('STALE_RESULT_BASELINE')
        value = parse_result(raw, active)
        return {'status':'VALIDATED_UNVERIFIED', 'binding':binding, 'result':value}


@guarded_mutation
def ingest_manual_result(root: Path, *, binding_digest: str, raw: bytes | None = None) -> dict:
    """One exact immutable result per Run, from upload or its canonical channel.

    Interrupted publication is fail-closed: no overwrite, no inferred PASS and
    no automatic replay of external commands. The operator inspects core state.
    """
    root = native_resolve(root); active = _active(root); binding = _binding(root, active)
    if digest(binding) != binding_digest: raise ValidationFailure('STALE_RESULT_BASELINE')
    output = root / active['allowed_agent_output_path']
    existing = _receipt(root, active)
    if raw is None:
        # The path is kernel-selected, never supplied by the browser.
        _, expected_hash, metadata = secure_read_agent_result(root, active['allowed_agent_output_path'])
        with _native_io_path(output).open('rb') as stream: raw = stream.read(AGENT_RESULT_MAX_BYTES+1)
        if 'sha256:'+hashlib.sha256(raw).hexdigest()!=expected_hash: raise ValidationFailure('RESULT_CHANGED')
        assert_agent_result_unchanged(root,metadata)
    value = parse_result(raw, active)
    result_hash = 'sha256:' + hashlib.sha256(raw).hexdigest()
    if existing:
        if existing['result_sha256'] != result_hash: raise ValidationFailure('RESULT_CHANGED')
        return {'status':'RESULT_RECEIVED', 'run_ref':active['run_ref'], 'result_sha256':result_hash}
    if _native_io_path(output).exists():
        _, current_hash, _ = secure_read_agent_result(root, active['allowed_agent_output_path'])
        if current_hash != result_hash: raise ValidationFailure('RESULT_CHANGED: canonical channel already occupied')
    else:
        with _native_io_path(output).open('xb') as stream:
            stream.write(raw); stream.flush(); os.fsync(stream.fileno())
    _, published_hash, metadata = secure_read_agent_result(root,active['allowed_agent_output_path'])
    if published_hash != result_hash or binding != _binding(root,active):
        raise ValidationFailure('STALE_RESULT_BASELINE: publication interrupted; inspect exact channel')
    if check_control_plane(root,active)['status']!='PASS': raise SafetyViolation('CONTROL_TAMPER')
    assert_agent_result_unchanged(root,metadata)
    receipt = {'schema':'LOCAL_MANUAL_RESULT_RECEIPT_V1', 'binding':binding,
        'result_sha256':result_hash, 'agent_status':value['status'], 'received_at':utc_now()}
    relative = _receipt_path(active)
    write_data(root/relative, receipt)
    record_phase_boundary(root, active, phase='MANUAL_RESULT_RECEIVED',
        kernel_written_paths=[active['allowed_agent_output_path'], relative], recorded_at=utc_now())
    return {'status':'RESULT_RECEIVED', 'run_ref':active['run_ref'], 'result_sha256':result_hash}


def _plan(root: Path, active: dict) -> dict:
    verification = runtime._trusted_task(root, active).get('verification') or {}
    commands = []
    for item in verification.get('commands') or []:
        argv, cwd, timeout = runtime._normalize_command(item, int(verification.get('timeout_seconds', 300)))
        resolved_cwd = resolve_inside(root, cwd)
        # Mirror subprocess executable resolution; never install missing tools.
        executable = Path(argv[0])
        if executable.is_absolute(): available = _native_io_path(executable).is_file()
        elif len(executable.parts) > 1: available = (_native_io_path(resolved_cwd/executable)).is_file()
        else: available = shutil.which(argv[0]) is not None
        commands.append({'argv':argv, 'cwd':str(resolved_cwd), 'timeout_seconds':timeout,
            'prerequisite':None if available and _native_io_path(resolved_cwd).is_dir() else 'PRODUCT_TOOLCHAIN_OR_CWD_MISSING'})
    plan = {'run_ref':active['run_ref'], 'task_ref':active['task_ref'], 'commands':commands,
        'manual_checks':verification.get('manual_checks') or [], 'expected_paths':verification.get('expected_paths') or []}
    return {**plan, 'digest':digest(plan)}


@guarded_mutation
def verify_manual_task(root: Path, *, binding_digest: str, plan_digest: str, consent: bool) -> dict:
    active = _active(root)
    if digest(_binding(root, active)) != binding_digest: raise ValidationFailure('STALE_RESULT_BASELINE')
    if not _receipt(root, active): raise ValidationFailure('RESULT_REQUIRED: сначала получите exact результат')
    plan = _plan(root, active)
    if plan['digest'] != plan_digest or type(consent) is not bool: raise ValidationFailure('STALE_VERIFICATION_PLAN')
    if consent and any(x['prerequisite'] for x in plan['commands']):
        raise ValidationFailure('PRODUCT_TOOLCHAIN_MISSING: установите нужный продукту инструмент отдельно')
    return runtime.verify_current(root, allow_command_execution=consent)


@guarded_mutation
def complete_manual_task(root: Path, *, binding_digest: str) -> dict:
    active = _active(root)
    if digest(_binding(root, active)) != binding_digest: raise ValidationFailure('STALE_RESULT_BASELINE')
    if not _receipt(root, active): raise ValidationFailure('RESULT_REQUIRED')
    return runtime.complete_current(root, root/active['allowed_agent_output_path'])


def _note(value: Any) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > 4000 or '\x00' in value:
        raise ValidationFailure('TASK_NOTE_INVALID: требуется текст 1–4000 символов')
    return value.strip()


@guarded_mutation
def block_manual_task(root: Path, *, run_ref: str, reason: str) -> dict:
    active = _active(root)
    if active['run_ref'] != run_ref: raise ValidationFailure('STALE_RUN')
    return runtime.block_current(root, _note(reason))


@guarded_mutation
def resume_manual_task(root: Path, *, blocker_ref: str, resolution: str) -> dict:
    resolution = _note(resolution)
    if _policy(root) != 'MANUAL_HANDOFF': raise ValidationFailure('AUTOMATIC_DISABLED')
    state = runtime._state(root)[1]['state']
    refs = [str(x)+'@1' for x in state.get('open_blocker_refs') or []]
    if blocker_ref not in refs or state.get('next_route') != 'RESOLVE_BLOCKER_OR_CHANGE_SCOPE':
        raise ValidationFailure('STALE_BLOCKER: требуется exact OPEN blocker revision')
    blocker = _read(root, '.harness/blockers/'+blocker_ref+'.yaml')['blocker']
    if blocker.get('kind') != 'EXECUTION_BLOCKER': raise ValidationFailure('TASK_RECOVERY_UNSUPPORTED')
    active = {'run_ref':blocker['run_ref'], 'task_ref':blocker['task_ref']}
    if check_control_plane(root, active)['status'] != 'PASS': raise SafetyViolation('CONTROL_TAMPER')
    _dependencies(root,runtime._task(root,str(blocker['task_ref']).split('@')[0])[0])
    return runtime.resume_blocked(root, resolution=resolution, blocker_ref=blocker_ref.rsplit('@',1)[0])


def task_console(root: Path) -> dict:
    """Read-only exact current-stage projection. Future stages remain outlines."""
    with project_operation_guard(root):
        ensure_native_path(root, tree=True)
        state = runtime._state(root)[1]['state']; status = runtime.project_status(root)
        stage = status['implementation']['active_stage']; active = state.get('active_run')
        tasks, packages = [], []
        for dirname, envelope, target in [('tasks','task',tasks), ('work-packages','work_package',packages)]:
            index = _read(root, '.harness/'+dirname+'/INDEX.yaml')[envelope+'_index']
            if len(index['current']) > 1000: raise ValidationFailure('TASK_VIEW_LIMIT')
            for relative in index['current'].values():
                obj = _read(root, relative)[envelope]
                target.append({key:obj.get(key) for key in ('id','revision','title','status','implementation_stage',
                    'depends_on_tasks','depends_on_work_packages','mandatory_task_refs')})
        current = runtime._trusted_task(root, active) if active else (runtime._task(root,state['current_task_ref'])[0] if state.get('current_task_ref') else None)
        # Future stages deliberately have no detailed Work Packages. Read their
        # canonical Stage Plan outlines instead of manufacturing future Tasks.
        levels = ['PROTOTYPE','ALPHA','BETA','MVP','RELEASE']
        future_levels = levels[levels.index(stage)+1:]
        plan_index = _read(root,'.harness/stages/PLANS/INDEX.yaml')['stage_plan_index']
        outlines = []
        for level in future_levels:
            plan_id = plan_index.get('by_level',{}).get(level)
            if not plan_id: continue
            plan = _read(root,plan_index['current'][plan_id])['stage_plan']
            outlines.append({'level':level,'ref':f"{plan['id']}@{plan['revision']}",
                'status':plan['status'],'work_package_outlines':plan.get('work_package_outlines') or [],
                'required_outcomes':plan.get('required_outcomes') or []})
        mode = _policy(root); automatic = mode != 'MANUAL_HANDOFF' or bool(active and runtime.automatic_run_phase(root,active))
        result = {'schema':'LOCAL_WEB_TASK_VIEW_V1','execution_mode':mode,'status':status,
            'active_stage':stage,'tasks':[x for x in tasks if x['implementation_stage']==stage],
            'work_packages':[x for x in packages if x['implementation_stage']==stage],
            'future_outlines':outlines,
            'current':current,'active_run':active,'prompt_text':None,'context':None,'verification_plan':None,
            'result':{'status':'NOT_RECEIVED'},'verification_report':None,'blockers':[],
            'binding_digest':None,'disabled_reason':'AUTOMATIC_EXECUTOR: NO-GO; внешний manual result запрещён' if automatic else None,
            'control_status':None}
        for ref in state.get('open_blocker_refs') or []:
            result['blockers'].append(_read(root,'.harness/blockers/'+ref+'@1.yaml')['blocker'])
        if active:
            control = check_control_plane(root, active); result['control_status']=control
            if control['status'] != 'PASS':
                result['disabled_reason']='CONTROL_TAMPER: восстановите доверенный handoff; не повторяйте операции'
                return result
            result['binding_digest']=digest(_binding(root,active))
            bundle = _read(root,active['prompt_bundle_path'])['compiled_prompt_bundle']
            prompt_path = resolve_inside(root,active['prompt_markdown_path'])
            if _native_io_path(prompt_path).stat().st_size > 256*1024 or 'sha256:'+sha256_file(prompt_path) != bundle['prompt_text_sha256']:
                raise ValidationFailure('JIT_DIGEST_MISMATCH')
            if bundle['task_ref'] != active['task_ref'] or bundle['run_ref'] != active['run_ref']:
                raise ValidationFailure('JIT_REF_MISMATCH')
            result['prompt_text']=_native_io_path(prompt_path).read_text('utf-8'); result['context']=_read(root,active['context_packet_path'])
            result['verification_plan']=_plan(root,active)
            if not automatic and result['verification_plan']['manual_checks']:
                from .task_manual_evidence import manual_evidence_context
                result['manual_evidence']=manual_evidence_context(root)
            try:
                receipt = _receipt(root,active)
                if receipt: result['result']={'status':'RESULT_RECEIVED', **receipt}
                elif (_native_io_path(root/active['allowed_agent_output_path'])).exists(): result['result']={'status':'CANONICAL_CHANNEL_PENDING_INTAKE'}
            except ValidationFailure as exc: result['result']={'status':'STALE_OR_CHANGED','error':exc.message}
            if active.get('verification_report_path'):
                result['verification_report']=_read(root,active['verification_report_path'])['validation_report']
        return result
