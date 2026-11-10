"""Noncanonical UI resume and admission/drain; no Task/Run state writes."""
from __future__ import annotations
import json
import threading
from .errors import ValidationFailure
from .operation_guard import project_operation_guard
from .platform_fs import ensure_native_path
from .serialization import write_data

SCREENS = {'projects', 'documents', 'interview', 'approvals', 'overview',
           'tasks', 'gates', 'maintenance', 'diagnostics'}


class DesktopLifecycle:
    def __init__(self, service):
        self.service = service
        self.lock = threading.Lock()
        self.stopping = threading.Event()
        self.active = 0

    def enter(self):
        with self.lock:
            if self.stopping.is_set():
                return False
            self.active += 1
            return True

    def leave(self):
        with self.lock:
            self.active -= 1

    def stop(self):
        with self.lock, self.service._futures_lock:
            if self.active or any(not future.done() for future in self.service._futures.values()):
                raise ValidationFailure('OPERATION_CONFLICT: дождитесь завершения mutations; commit не отменён')
            self.stopping.set()
        return {'status': 'STOPPING'}


def read_resume(service):
    path = service.app_data / 'ui-resume.json'
    ensure_native_path(path, file_ok=True)
    if not path.exists():
        return {'revision': 0, 'project_id': None, 'screen': 'projects'}
    if path.stat().st_size > 4096:
        raise ValidationFailure('Invalid resume record')
    value = json.loads(path.read_text('utf-8'))
    if set(value) != {'revision', 'project_id', 'screen'} or value['screen'] not in SCREENS:
        raise ValidationFailure('Invalid resume record')
    return value


def save_resume(service, *, project_id, screen, expected_revision):
    if (not isinstance(screen, str) or screen not in SCREENS or type(expected_revision) is not int
            or expected_revision < 0):
        raise ValidationFailure('Invalid resume selection')
    if project_id is not None:
        service._registered(project_id)
    with project_operation_guard(service.app_data):
        current = read_resume(service)
        if current['revision'] != expected_revision:
            raise ValidationFailure('OPERATION_CONFLICT: stale UI resume revision')
        value = {'revision': expected_revision + 1, 'project_id': project_id, 'screen': screen}
        write_data(service.app_data / 'ui-resume.json', value)
        return value
