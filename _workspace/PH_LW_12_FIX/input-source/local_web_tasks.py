"""Private upload staging and application orchestration for PH-LW-09."""
from __future__ import annotations
import hashlib
import re
from pathlib import Path
from .errors import ValidationFailure
from .operation_guard import project_operation_guard
from .platform_fs import ensure_native_path
from .serialization import load_data, write_data
from . import manual_tasks as core

TASK_ACTIONS = {'receive-result','manual-evidence','verify','complete','block','resume','next'}
FIELDS = {'receive-result':{'upload_id','binding_digest'}, 'verify':{'binding_digest','plan_digest','consent'},
          'complete':{'binding_digest'}, 'block':{'run_ref','reason'}, 'resume':{'blocker_ref','resolution'},
          'manual-evidence':{'document','confirmed'}}

def root_for(service, project_id):
    root, kind = service._registered(project_id)
    if kind != 'project': raise ValidationFailure('TASK_PROJECT_REQUIRED')
    return root

def view(service, project_id):
    root = root_for(service,project_id)
    with project_operation_guard(root):
        return {**core.task_console(root), 'project_id':project_id, 'fingerprint':service.core_fingerprint(root,'project')}

def stage_result(service, project_id, raw, *, expected_fingerprint, binding_digest):
    root = root_for(service,project_id)
    with project_operation_guard(root):
        if service.core_fingerprint(root,'project') != expected_fingerprint: raise ValidationFailure('STALE_FINGERPRINT')
        core.validate_manual_result(root,raw,binding_digest=binding_digest)
        upload_id='LWR-'+hashlib.sha256((project_id+binding_digest).encode()+raw).hexdigest().upper()
        directory=service.app_data/'task-results'; directory.mkdir(exist_ok=True,mode=0o700)
        ensure_native_path(directory,tree=True)
        if len(list(directory.glob('*.json'))) >= 1000 and not (directory/(upload_id+'.json')).exists():
            raise ValidationFailure('RESULT_STAGING_LIMIT')
        record={'project_id':project_id,'binding_digest':binding_digest,'raw_sha256':hashlib.sha256(raw).hexdigest()}
        path=directory/(upload_id+'.bin'); meta=directory/(upload_id+'.json')
        if meta.exists():
            if load_data(meta)!=record or path.read_bytes()!=raw: raise ValidationFailure('RESULT_CHANGED')
        else:
            if path.exists() and path.read_bytes()!=raw: raise ValidationFailure('RESULT_CHANGED')
            if not path.exists():
                with path.open('xb') as stream: stream.write(raw)
            write_data(meta,record)
        return {'status':'STAGED_UNVERIFIED','upload_id':upload_id,'binding_digest':binding_digest}

def execute(service, project_id, action, payload):
    root=root_for(service,project_id)
    if action in FIELDS and (set(payload)!=FIELDS[action]) and not (action=='verify' and not payload):
        raise ValidationFailure('TASK_FIELDS_INVALID')
    if action=='receive-result':
        raw=None; uid=payload['upload_id']
        if uid is not None:
            if not isinstance(uid,str) or not re.fullmatch('LWR-[A-F0-9]{64}',uid): raise ValidationFailure('RESULT_UPLOAD_UNKNOWN')
            directory=service.app_data/'task-results'; ensure_native_path(directory,tree=True)
            meta=load_data(directory/(uid+'.json')); path=directory/(uid+'.bin')
            if path.stat().st_nlink!=1 or path.stat().st_size>1024*1024: raise ValidationFailure('RESULT_INVALID')
            raw=path.read_bytes()
            if meta!={'project_id':project_id,'binding_digest':payload['binding_digest'],'raw_sha256':hashlib.sha256(raw).hexdigest()}:
                raise ValidationFailure('RESULT_UPLOAD_MISMATCH')
        return core.ingest_manual_result(root,binding_digest=payload['binding_digest'],raw=raw)
    if action=='verify':
        if not payload:
            # Existing public service clients retain command-disabled checks.
            # The core independently rejects automatic projects and missing proof.
            from .runtime import verify_current
            return verify_current(root,allow_command_execution=False)
        return core.verify_manual_task(root,**payload)
    if action=='manual-evidence':
        from .task_manual_evidence import record_manual_evidence
        return record_manual_evidence(root, **payload)
    if action=='complete': return core.complete_manual_task(root,**payload)
    if action=='block': return core.block_manual_task(root,**payload)
    if action=='resume': return core.resume_manual_task(root,**payload)
    raise ValidationFailure('ACTION_DISABLED')
