"""PH-LW-03: local-only application service for the MANUAL Local Web companion.

No HTTP server, raw shell gateway or product automatic executor. The explicit
CLI document-analysis connection is separate from product Task execution. The catalog and
operation receipts are external, non-authoritative app data.  Core Python APIs
alone perform governed mutations, under one shared cross-process fence.
"""
from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
import hashlib
from importlib import resources
import json
import os
from pathlib import Path
import re
from threading import Lock, RLock
from typing import Any

from .errors import HarnessError, ValidationFailure
from .hashing import sha256_file
from .local_web_drafts import draft_input_digest, preview_draft_update, update_provisional_draft
from .operation_guard import project_operation_guard
from .platform_fs import ensure_native_path, _native_io_path, native_resolve, native_glob
from .project_input import validate_project_input
from .serialization import canonical_json_bytes, load_data, write_data
from .util import utc_now

_PROJECT_ID = re.compile(r'^LWP-[A-F0-9]{20}$')
_OPERATION_ID = re.compile(r'^LWO-[A-F0-9]{32}$')
_KEY = re.compile(r'^[a-zA-Z0-9_.:-]{16,160}$')
_FINGERPRINT = re.compile(r'^sha256:[a-f0-9]{64}$')
_ACTIVE = frozenset({'QUEUED', 'RUNNING'})
_TERMINAL = frozenset({'SUCCEEDED', 'FAILED', 'BLOCKED', 'CANCELLED', 'INTERRUPTED'})

# Only these API actions are enabled in PH-LW-03. Other CONTROL_MAP actions
# remain visible with truthful disabled reasons, not simulated success.
_ACTIONS = {
    'update-draft': {'kind': 'workspace', 'fields': frozenset({'patch', 'expected_input_digest'}), 'id': 'LW-DRAFT'},
    'check-intake': {'kind': 'workspace', 'fields': frozenset(), 'id': 'LW-C03'},
    'prepare': {'kind': 'workspace', 'fields': frozenset(), 'id': 'LW-C04'},
    'publish-project': {'kind': 'workspace', 'fields': frozenset({'target_id', 'binding_digest'}), 'id': 'LW-C04'},
    'next': {'kind': 'project', 'fields': frozenset(), 'id': 'LW-C09'},
    'validate-project': {'kind': 'project', 'fields': frozenset(), 'id': 'LW-C06'},
    'verify': {'kind': 'project', 'fields': frozenset({'binding_digest','plan_digest','consent'}), 'id': 'LW-C12'},
    'receive-result': {'kind':'project','fields':frozenset({'upload_id','binding_digest'}),'id':'LW-RESULT'},
    'manual-evidence': {'kind':'project','fields':frozenset({'document','confirmed'}),'id':'LW-MANUAL-EVIDENCE'},
    'complete': {'kind':'project','fields':frozenset({'binding_digest'}),'id':'LW-C13'},
    'block': {'kind':'project','fields':frozenset({'run_ref','reason'}),'id':'LW-C14'},
    'resume': {'kind':'project','fields':frozenset({'blocker_ref','resolution'}),'id':'LW-C15'},
}
from .local_web_lifecycle import ACTIONS as _LIFECYCLE_ACTIONS, compatible as lifecycle_compatible
_ACTIONS.update(_LIFECYCLE_ACTIONS)

_RU = {
    'MANUAL_EVIDENCE_CONSENT_REQUIRED': ('Требуется отдельное подтверждение независимого manual review.', 'Проверьте пункты и источники, затем подтвердите observations.'),
    'MANUAL_EVIDENCE_INVALID': ('Manual evidence неполное либо имеет недопустимые поля.', 'Укажите reviewer, каждый точный check, PASS/FAIL, observations и просмотренные файлы.'),
    'MANUAL_EVIDENCE_STALE': ('Task/Run, verification plan или product sources изменились.', 'Обновите форму и выполните review текущих файлов.'),
    'MANUAL_EVIDENCE_CHANGED': ('Review этого Run уже зафиксирован либо публикация прервана.', 'Не заменяйте evidence; проверьте canonical состояние, при необходимости block/resume в новый Run.'),
    'MANUAL_EVIDENCE_DISABLED': ('Для этой Task manual evidence не разрешено.', 'Используйте текущий verification plan и core route.'),
    'AUTOMATIC_DISABLED': ('Automatic executor недоступен; manual fallback запрещён.', 'Откройте диагностику; режим проекта сохранён.'),
    'STALE_RESULT_BASELINE': ('Product baseline или exact Run изменился.', 'Обновите Task view; для исправленного результата создайте новый Run через block/resume.'),
    'RESULT_CHANGED': ('Принятый result изменён или канал уже занят другим содержанием.', 'Не заменяйте result; используйте новый Run через block/resume.'),
    'RESULT_REQUIRED': ('Exact Agent Task Result ещё не получен.', 'Выберите файл или примите существующий canonical channel.'),
    'PRODUCT_TOOLCHAIN_MISSING': ('Не найден инструмент или cwd продуктовой проверки.', 'Установите необходимый продукту toolchain отдельно, затем обновите план; скрытой установки нет.'),
    'STALE_VERIFICATION_PLAN': ('План проверки изменился.', 'Обновите точные argv/cwd/timeout и отдельно подтвердите выполнение.'),
    'CONTROL_TAMPER': ('Обнаружено изменение защищённого control plane.', 'Восстановите доверенный handoff; in-place resume запрещён.'),
    'DESTINATION_EXISTS': ('Папка уже существует; её содержимое сохранено.', 'Выберите новое имя папки.'),
    'DESTINATION_COLLISION': ('Папка пересекается с рабочими данными Harness.', 'Выберите отдельный каталог проекта.'),
    'TARGET_INVALID': ('Недопустимое имя новой папки.', 'Используйте одно имя без пути и служебных символов Windows.'),
    'STALE_PREPARATION': ('Input, источники, согласования или сборка изменились.', 'Перечитайте согласования; прежнюю публикацию нельзя повторить с другим содержанием.'),
    'PREPARATION_APPROVALS_REQUIRED': ('Нужны все актуальные отдельные согласования.', 'Завершите согласования перед подготовкой.'),
    'PREPARATION_ALREADY_STARTED': ('Подготовка уже зафиксирована.', 'Откройте её результат или явно выполните сверку.'),
    'PREPARATION_REPLAY_CONFLICT': ('Запрос относится к другому input или каталогу.', 'Используйте исходный подтверждённый target.'),
    'INCOMPLETE_COMPILE': ('Сборка прервалась до получения полных outputs. Файлы сохранены.', 'Требуется локальная диагностика; автоматический повтор и удаление запрещены.'),
    'PREPARATION_IO_BLOCKED': ('Размещение прервано из-за доступа к файлам или занятого handle.', 'Освободите файл или место на диске и выполните явную сверку подготовки.'),
    'VALIDATION_FAILED': ('Запрос или состояние проекта не прошли проверку.', 'Проверьте данные и текущий статус, затем создайте новое действие.'),
    'STALE_FINGERPRINT': ('Состояние проекта изменилось после открытия формы.', 'Обновите статус и повторите действие с новым ключом.'),
    'OPERATION_CONFLICT': ('С этим проектом уже работает другая операция.', 'Получите статус существующей операции и повторите позже.'),
    'UNKNOWN_ACTION': ('Запрошенное действие не поддерживается.', 'Выберите доступную операцию из списка.'),
    'ACTION_DISABLED': ('Действие ещё недоступно в этом этапе.', 'Используйте доступный ручной маршрут.'),
    'AMBIGUOUS_COMMIT': ('Результат прерванной операции не доказан.', 'Проверьте состояние ядра и выполните явное восстановление; повтор автоматически запрещён.'),
    'UNEXPECTED_ERROR': ('Операцию не удалось завершить.', 'Проверьте core status и журнал операции; не повторяйте её автоматически.'),
    'WAITING_INPUT': ('Для продолжения не хватает данных.', 'Заполните недостающие поля черновика.'),
    'WAITING_DECISION': ('Не получены необходимые решения.', 'Подтвердите каждый required subject отдельно.'),
    'UPLOAD_BODY_LIMIT': ('Размер загруженных данных превышает 64 MiB.', 'Уменьшите размер пакета.'),
    'ZIP_ENTRY_SIZE_LIMIT': ('Один элемент ZIP превышает 8 MiB.', 'Уменьшите отдельный документ.'),
    'ZIP_ENTRY_COUNT_LIMIT': ('ZIP превышает лимит 1000 элементов.', 'Разделите архив.'),
    'ZIP_EXTRACTED_BYTES_LIMIT': ('Распакованные данные превышают 128 MiB.', 'Уменьшите архив.'),
    'ZIP_COMPRESSION_RATIO_LIMIT': ('Обнаружена недопустимая степень сжатия ZIP.', 'Используйте небольшой обычный ZIP.'),
    'ZIP_DEPTH_LIMIT': ('ZIP содержит слишком глубокие пути.', 'Допустимо не более 16 уровней.'),
    'ZIP_UNSAFE_PATH': ('ZIP содержит опасный путь.', 'Исправьте архив до повторного импорта.'),
    'ZIP_LINK_OR_SPECIAL_FILE': ('ZIP содержит ссылку либо специальный файл.', 'Допускаются обычные MD-файлы и каталоги.'),
    'ZIP_UNICODE_OR_CASE_COLLISION': ('ZIP содержит конфликт имён Unicode/регистр.', 'Переименуйте конфликтующие файлы.'),
    'ZIP_DUPLICATE_PATH': ('ZIP содержит дублирующееся имя.', 'Исправьте архив.'),
    'ZIP_INVALID_OR_CRC_FAILED': ('Архив не прошёл проверку ZIP/CRC.', 'Подготовьте корректный ZIP.'),
    'ZIP_CRC_OR_COMPRESSION_INVALID': ('Данные ZIP повреждены или не поддерживаются.', 'Подготовьте корректный архив.'),
    'ZIP_ENCRYPTION_UNSUPPORTED': ('Зашифрованный ZIP не поддерживается.', 'Предоставьте обычный ZIP без пароля.'),
    'NESTED_ZIP_UNSUPPORTED': ('ZIP внутри ZIP не поддерживается.', 'Передайте отдельный ZIP.'),
    'MARKDOWN_ENCODING_UNSUPPORTED': ('Документ не является допустимым UTF-8.', 'Сохраните Markdown как UTF-8.'),
    'SOURCE_NAME_CHANGED_USE_REPLACE': ('Имя источника совпало, но байты различаются.', 'Выберите явную замену источников.'),
    'SOURCE_RECOVERY_REQUIRED': ('Обнаружен незавершённый импорт.', 'Выполните явное восстановление импорта.'),
    'SOURCE_REFRESH_AFTER_PREPARE_UNSUPPORTED': ('Изменение источников после подготовки handoff недоступно.', 'Используйте поддержанный новый governed цикл.'),
    'STALE_SOURCE_REVISION': ('Ревизия документов изменилась.', 'Обновите список документов и повторите.'),
    'UPLOAD_COUNT_LIMIT': ('Некорректное количество файлов.', 'Выберите от 1 до 100 файлов.'),
    'NO_SUPPORTED_DOCUMENTS': ('Не найдено ни одного MD документа.', 'Загрузите MD либо выберите «Документации нет». '),
    'SOURCE_REFRESH_RECOVERED_RETRY_WITH_CURRENT_FINGERPRINT': ('После прерывания выполнено восстановление импорта.', 'Перечитайте состояние и повторите явно.'),
}


@dataclass(frozen=True)
class OperationRequest:
    project_id: str
    action: str
    payload: dict[str, Any]
    idempotency_key: str
    expected_fingerprint: str

    def __post_init__(self) -> None:
        if not isinstance(self.project_id, str) or not _PROJECT_ID.fullmatch(self.project_id):
            raise ValidationFailure('Неверный зарегистрированный project ID')
        if not isinstance(self.action, str) or not self.action or len(self.action) > 64:
            raise ValidationFailure('Неверное имя действия')
        if not isinstance(self.payload, dict):
            raise ValidationFailure('Payload должен быть объектом')
        if not isinstance(self.idempotency_key, str) or not _KEY.fullmatch(self.idempotency_key):
            raise ValidationFailure('Неверный idempotency key (16–160 символов)')
        if not isinstance(self.expected_fingerprint, str) or not _FINGERPRINT.fullmatch(self.expected_fingerprint):
            raise ValidationFailure('Неверный expected fingerprint')
        try:
            encoded = canonical_json_bytes(self.payload)
        except (TypeError, ValueError, RecursionError) as exc:
            raise ValidationFailure('Payload не является ограниченным JSON') from exc
        if len(encoded) > 512 * 1024:
            raise ValidationFailure('Payload превышает лимит 512 KiB')


class LocalWebService:
    """Durable single-worker service. Polling never calls a mutating core API.

    Construct with a trusted, private application-data directory. Registration
    is an explicit operator-only call, never an action payload path. Operations
    are durable independently of browser connection; a service process crash
    does NOT cause unsafe automatic replay on restart.
    """

    def __init__(self, app_data: Path, *, projects_directory: Path | None = None):
        ensure_native_path(Path(app_data), tree=True)
        base = Path(app_data).expanduser()
        if _native_io_path(base).is_symlink():
            raise ValidationFailure('Каталог Local Web не должен быть ссылкой')
        self.app_data = native_resolve(base)
        # Trusted local configuration only; never accepted from HTTP JSON.
        projects = projects_directory if projects_directory is not None else Path.home() / 'HarnessProjects'
        ensure_native_path(Path(projects))
        self.projects_directory = Path(projects).absolute()
        _native_io_path(self.app_data).mkdir(parents=True, exist_ok=True, mode=0o700)
        if _native_io_path(self.app_data).is_symlink() or not _native_io_path(self.app_data).is_dir():
            raise ValidationFailure('Каталог приложения должен быть обычной директорией')
        if os.name != 'nt' and _native_io_path(self.app_data).stat().st_mode & 0o077:
            raise ValidationFailure('Каталог приложения должен быть приватным (0700)')
        for name in ('operations', 'artifacts'):
            path = self.app_data / name
            _native_io_path(path).mkdir(exist_ok=True, mode=0o700)
            if _native_io_path(path).is_symlink() or not _native_io_path(path).is_dir():
                raise ValidationFailure('Небезопасная директория данных Local Web', name)
        self._worker = ThreadPoolExecutor(max_workers=1, thread_name_prefix='harness-local-web')
        self._futures: dict[str, Future[None]] = {}
        self._futures_lock = Lock()
        from .local_web_cli import CliConnection
        self.cli_connection = CliConnection(self.app_data)
        self._cli_lock = RLock()
        self._cli_cancel = {}
        self._closed = False

    @staticmethod
    def _hash(value: Any) -> str:
        return 'sha256:' + hashlib.sha256(canonical_json_bytes(value)).hexdigest()

    def _catalog_path(self) -> Path:
        return self.app_data / 'catalog.json'

    def _catalog(self) -> dict[str, Any]:
        path = self._catalog_path()
        if _native_io_path(path).is_symlink():
            raise ValidationFailure('Каталог Local Web не может быть ссылкой')
        if not _native_io_path(path).exists():
            return {'version': 1, 'projects': {}}
        if not _native_io_path(path).is_file():
            raise ValidationFailure('Каталог Local Web должен быть обычным файлом')
        catalog = load_data(path)
        if (not isinstance(catalog, dict) or set(catalog) != {'version', 'projects'}
                or catalog['version'] != 1 or not isinstance(catalog['projects'], dict)):
            raise ValidationFailure('Повреждён каталог Local Web; не пытайтесь восстановить его из UI')
        return catalog

    def register_existing(self, root: Path, *, kind: str) -> str:
        """Trusted local operator registration, not accessible via action payload."""
        if kind not in {'workspace', 'project', 'migration'}:
            raise ValidationFailure('Неизвестный тип регистрируемого корня', kind)
        raw = Path(root).expanduser()
        if _native_io_path(raw).is_symlink():
            raise ValidationFailure('Ссылка не может быть корнем проекта')
        ensure_native_path(raw, tree=True)
        canonical = native_resolve(raw, strict=True)
        if not _native_io_path(canonical).is_dir() or any(_native_io_path(p).is_symlink() for p in [canonical, *canonical.parents]):
            raise ValidationFailure('Небезопасный project/workspace root')
        if canonical == self.app_data or canonical in self.app_data.parents or self.app_data in canonical.parents:
            raise ValidationFailure('Project root и app-data должны быть раздельными')
        marker = (('PROJECT_INPUT.yaml', 'STATE.yaml') if kind == 'workspace' else
                  ('.harness/state/CURRENT_STATE.yaml', '.harness/config/PROJECT_LOCK.yaml') if kind == 'migration' else
                  ('.harness/state/CURRENT_STATE.yaml', '.harness/stages/STAGE_STATE.yaml'))
        if any(not (_native_io_path(canonical / name)).is_file() or (_native_io_path(canonical / name)).is_symlink() for name in marker):
            raise ValidationFailure('У корня отсутствуют необходимые canonical файлы', kind)
        # Ensure root is a real compatible instance, not a renamed arbitrary folder.
        if kind == 'workspace':
            data = load_data(canonical / 'PROJECT_INPUT.yaml')
            if not isinstance(data, dict) or not isinstance(data.get('project'), dict):
                raise ValidationFailure('PROJECT_INPUT не является корректным черновиком')
        elif kind == 'migration':
            from .lifecycle_forms import migration_preview
            migration_preview(canonical)
        else:
            from .runtime import project_status
            project_status(canonical)
        with project_operation_guard(self.app_data):
            catalog = self._catalog()
            for project_id, item in catalog['projects'].items():
                if item.get('root') == str(canonical):
                    if item.get('kind') == 'migration' and kind == 'project':
                        item['kind'] = 'project'
                        write_data(self._catalog_path(), catalog)
                        return project_id
                    if item.get('kind') != kind:
                        raise ValidationFailure('Корень уже зарегистрирован с другим типом')
                    return project_id
            from secrets import token_hex
            project_id = 'LWP-' + token_hex(10).upper()
            catalog['projects'][project_id] = {'root': str(canonical), 'kind': kind, 'created_at': utc_now()}
            write_data(self._catalog_path(), catalog)
            return project_id

    def _registered(self, project_id: str, *, migration_receipt: bool = False,
                    operation_snapshot: bool = False) -> tuple[Path, str]:
        if not isinstance(project_id, str) or not _PROJECT_ID.fullmatch(project_id):
            raise ValidationFailure('Неизвестный project ID')
        item = self._catalog()['projects'].get(project_id)
        if not isinstance(item, dict) or item.get('kind') not in ('workspace', 'project', 'migration'):
            raise ValidationFailure('Project ID не найден в локальном каталоге')
        stored = item.get('root')
        if not isinstance(stored, str):
            raise ValidationFailure('Повреждена запись проекта')
        raw = Path(stored)
        # An owned migration receipt is app data. Polling must not enumerate a
        # canonical/backup tree while the worker swaps or removes it. Ancestor
        # and root reparse checks still apply; mutations use the full check.
        # A companion journal GET reads no canonical descendants. A recursive
        # scan can race a worker's atomic temp-file rename and falsely fail the
        # snapshot. Root/ancestor reparse and exact catalog checks still apply;
        # mutation admission retains the full tree check.
        ensure_native_path(raw, tree=not (migration_receipt or operation_snapshot))
        from .lifecycle_forms import migration_recovery_context
        pending_migration = migration_receipt or (item['kind'] in {'project','migration'} and migration_recovery_context(raw))
        if _native_io_path(raw).is_symlink() or native_resolve(raw, strict=not bool(pending_migration)) != raw:
            raise ValidationFailure('Путь проекта изменился или стал ссылкой')
        return raw, item['kind']

    @staticmethod
    def core_fingerprint(root: Path, kind: str) -> str:
        """Read-only and binds project control refs and product baseline."""
        from .lifecycle_forms import migration_recovery_context
        if kind in {'project', 'migration'}:
            recovery = migration_recovery_context(root)
            if recovery: return LocalWebService._hash({'kind': kind, 'migration_recovery': recovery})
        if kind == 'workspace':
            names = ('PROJECT_INPUT.yaml', 'STATE.yaml', 'READINESS.json',
                     'SESSION.yaml', 'SOURCE_INVENTORY.yaml', 'REPOSITORY_INVENTORY.yaml', 'MATURITY_ASSESSMENT.yaml')
        elif kind in {'project', 'migration'}:
            names = ('.harness/state/CURRENT_STATE.yaml', '.harness/stages/STAGE_STATE.yaml',
                     '.harness/tasks/INDEX.yaml', '.harness/work-packages/INDEX.yaml',
                     '.harness/stages/STAGE_PLANS/INDEX.yaml', '.harness/stages/STAGE_GATES/INDEX.yaml',
                     '.harness/runtime/ACTIVE_RUN.yaml')
        else:
            raise ValidationFailure('Неизвестный тип fingerprint')
        digest_set = {}
        for name in names:
            path = root / name
            if _native_io_path(path).is_symlink():
                raise ValidationFailure('Canonical fingerprint path is a link', name)
            digest_set[name] = sha256_file(path) if _native_io_path(path).is_file() else None
        if kind in {'project', 'migration'}:
            from .stages import product_baseline_revision
            digest_set['product_baseline_revision'] = product_baseline_revision(root)
            from .workspace import scan_protected_control_plane
            digest_set['control_files'] = scan_protected_control_plane(root)
        if kind == 'workspace':
            from .lifecycle_forms import repository_binding
            binding = repository_binding(root)
            if binding is not None:
                digest_set['repository_binding'] = binding
        return LocalWebService._hash({'kind': kind, 'core': digest_set})

    def get_status(self, project_id: str) -> dict[str, Any]:
        """No check_intake, next_task, recovery, diagnostic execution or writes."""
        root, kind = self._registered(project_id)
        from .lifecycle_forms import migration_recovery_context
        if kind in {'project','migration'} and migration_recovery_context(root):
            return {'project_id': project_id, 'kind': kind, 'core_status': 'MIGRATION_RECOVERY_REQUIRED', 'core_route': {},
                'fingerprint': self.core_fingerprint(root, kind), 'done': [], 'current': None, 'blockers': ['Interrupted migration'],
                'required_user_action': 'Явно подтвердите recovery existing migration journal.', 'refs': {},
                'available_actions': [{'id':'LW-C07','action':'recover-migration','enabled':True,'disabled_reason':None}]}
        if kind == 'migration':
            from .lifecycle_forms import migration_preview
            with project_operation_guard(root):
                preview = migration_preview(root)
                return {'project_id': project_id, 'kind': kind, 'core_status': 'MIGRATION_REVIEW',
                    'core_route': {}, 'fingerprint': self.core_fingerprint(root, kind), 'done': [], 'current': None,
                    'blockers': preview['validation'].get('errors', []), 'required_user_action': 'Просмотрите план и явно подтвердите migration.',
                    'refs': {}, 'available_actions': [{'id': 'LW-C07' if a == 'migrate-project' else 'LW-PREPARE-MIGRATION',
                        'action': a, 'enabled': True, 'disabled_reason': None}
                        for a in ('prepare-migration', 'migrate-project')]}
        if kind == 'workspace' and root.name == 'intake' and (_native_io_path(root.parent / 'imports' / 'pending.json')).exists():
            raise ValidationFailure('SOURCE_RECOVERY_REQUIRED')
        with project_operation_guard(root):
            fingerprint = self.core_fingerprint(root, kind)
            if kind == 'workspace':
                input_data = load_data(root / 'PROJECT_INPUT.yaml')
                readiness = validate_project_input(input_data, require_approvals=True)
                stored = load_data(root / 'STATE.yaml').get('state') or {}
                status = readiness['status']
                route = {'WAITING_INPUT': 'ANSWER_QUESTIONS', 'WAITING_DECISION': 'APPROVE_BASELINES',
                         'READY_FOR_HANDOFF': 'PREPARE_CODEX_HANDOFF', 'INVALID': 'FIX_INPUT'}.get(status, 'FIX_INPUT')
                refs = {'session_ref': stored.get('session_ref'), 'input_digest': draft_input_digest(root),
                        'target_level': input_data.get('implementation', {}).get('target_level')}
                done, current, blockers = [], None, readiness.get('missing_fields') or readiness.get('errors') or []
                if status == 'WAITING_DECISION':
                    blockers = (['implementation.target_level'] if
                                input_data.get('implementation', {}).get('target_level') == 'UNSURE' else [])
                    blockers += readiness.get('missing_fields', []) + readiness.get('missing_approvals', [])
                action = 'Заполните недостающие поля' if status == 'WAITING_INPUT' else (
                    'Подтвердите решения' if status == 'WAITING_DECISION' else (
                    'Подготовьте handoff' if status == 'READY_FOR_HANDOFF' else 'Исправьте черновик'))
            else:
                from .runtime import project_status
                from .stages import stage_status
                persisted = project_status(root)
                stage = stage_status(root)
                status = persisted['status']
                route = persisted.get('next_operator_route') or {}
                refs = {'current_task': persisted.get('current_task'), 'active_run': persisted.get('active_run'),
                        'stage_plan_ref': stage.get('stage_plan_ref'), 'stage_plan_revision': stage.get('stage_plan_revision'),
                        'gate_ref': stage.get('gate_ref'), 'gate_revision': stage.get('gate_revision'),
                        'baseline_revision': stage.get('baseline_revision'), 'target_level': stage.get('target_level'),
                        'active_stage': stage.get('active_stage'), 'highest_accepted_level': stage.get('highest_accepted_level')}
                done = list(persisted.get('completed_task_refs') or [])
                current = persisted.get('current_task')
                blockers = list(persisted.get('blocked_task_refs') or []) + list(stage.get('critical_blockers') or [])
                action = route.get('command') or route.get('reason') or route.get('route') or 'Откройте текущую задачу'
            available = self.available_actions(kind, status, route)
            lifecycle_enabled = set()
            if kind == 'workspace':
                from .lifecycle_forms import repository_binding
                rb = repository_binding(root)
                if rb is not None and not rb['stale']: lifecycle_enabled.add('assess-maturity')
            if kind == 'project':
                from .manual_tasks import task_console
                task_view = task_console(root)
                active = task_view['active_run']
                manual = not task_view['disabled_reason']
                if manual:
                    lifecycle_enabled.update(_LIFECYCLE_ACTIONS)
                    lifecycle_enabled.discard('recover-migration')
                allowed = {'validate-project'}
                if manual:
                    if isinstance(route,dict) and route.get('route') in {'RESERVE_READY_TASK','VERIFY_CURRENT_TASK','COMPLETE_VERIFIED_TASK'}:
                        allowed.add('next')
                    if active: allowed.update({'verify','receive-result','manual-evidence','block'})
                    if active and task_view['result']['status']=='RESULT_RECEIVED' and (task_view['verification_report'] or {}).get('status')=='PASS': allowed.add('complete')
                    if isinstance(route,dict) and route.get('route')=='RESUME_BLOCKED_TASK': allowed.add('resume')
                for item in available:
                    if item['action'] in {'next','verify','complete','block','resume'}:
                        item['enabled']=item['action'] in allowed
                        item['disabled_reason']=None if item['enabled'] else (task_view['disabled_reason'] or 'Нужен текущий Task/Run и допустимый core route.')
                available.append({'id':'LW-RESULT','action':'receive-result','enabled':'receive-result' in allowed,
                    'disabled_reason':None if 'receive-result' in allowed else (task_view['disabled_reason'] or 'Нет активного manual Run.')})
                available.append({'id':'LW-MANUAL-EVIDENCE','action':'manual-evidence','enabled':'manual-evidence' in allowed,
                    'disabled_reason':None if 'manual-evidence' in allowed else (task_view['disabled_reason'] or 'Нет активного manual Run.')})
            for item in available:
                if item['action'] in _LIFECYCLE_ACTIONS:
                    item['enabled'] = item['action'] in lifecycle_enabled
                    item['disabled_reason'] = None if item['enabled'] else 'Нужен manual проект либо актуальный Brownfield/Hybrid intake.'
            known = {item['action'] for item in available}
            available.extend({'id': 'LW-LIFECYCLE-' + a.upper(), 'action': a, 'enabled': a in lifecycle_enabled,
                              'disabled_reason': None if a in lifecycle_enabled else 'Выберите применимый manual проект.'}
                             for a in _LIFECYCLE_ACTIONS if a not in known and lifecycle_compatible(a, kind))
            return {'project_id': project_id, 'kind': kind, 'core_status': status,
                    'core_route': route, 'persisted_next_route': stored.get('next_route') if kind == 'workspace' else persisted.get('next_route'),
                    'fingerprint': fingerprint, 'done': done, 'current': current, 'blockers': blockers,
                    'required_user_action': action, 'refs': refs, 'available_actions': available}

    @staticmethod
    def available_actions(kind: str, status: str | None, route: Any) -> list[dict[str, Any]]:
        """Exactly the 26 PH-LW-01 mapped controls + explicit draft-update."""
        contents = resources.files('project_harness').joinpath('resources/local_web/control_map_v1.json').read_text(encoding='utf-8')
        controls = json.loads(contents)['commands']
        enabled = {'check-intake', 'update-draft', 'prepare'} if kind == 'workspace' else {'next', 'validate-project', 'verify'}
        if kind == 'workspace' and status != 'READY_FOR_HANDOFF':
            enabled.discard('prepare')
        if kind == 'project' and (not isinstance(route, dict) or not route.get('command')):
            enabled.discard('next')
        if kind == 'project' and status not in {'ACTIVE', 'VERIFYING'}:
            enabled.discard('verify')
        response = []
        for item in controls:
            cmd = item['cli']
            if cmd == 'status':
                response.append({'id': item['id'], 'action': 'get-status', 'enabled': True, 'disabled_reason': None})
                continue
            if cmd == 'stage-status' and kind == 'project':
                response.append({'id': item['id'], 'action': cmd, 'enabled': True, 'disabled_reason': None})
                continue
            if cmd in enabled:
                response.append({'id': item['id'], 'action': cmd, 'enabled': True, 'disabled_reason': None})
            else:
                reason = ('Автоматический исполнитель отключён в Local Web manual; Podman/egress acceptance остаётся NO-GO.' if cmd in {'execute-current','executor-doctor'}
                          else ('Нужна готовность черновика и отдельные approvals.' if cmd == 'prepare' and kind == 'workspace'
                          else ('Невозможно выполнить из текущего состояния core.' if cmd in _ACTIONS
                                else 'В текущем Local Web интерфейсе эта операция не реализована.')))
                response.append({'id': item['id'], 'action': cmd, 'enabled': False, 'disabled_reason': reason})
        response.append({'id': 'LW-DRAFT', 'action': 'update-draft', 'enabled': kind == 'workspace',
                         'disabled_reason': None if kind == 'workspace' else 'Редактирование доступно только в intake workspace.'})
        return response

    def list_projects(self) -> list[dict[str, Any]]:
        """Read-only catalog projection; no implicit registration or core mutation."""
        projects = self._catalog()['projects']
        if len(projects) > 128:
            raise ValidationFailure('Превышен лимит записей локального каталога')
        result: list[dict[str, Any]] = []
        for project_id in sorted(projects):
            if not _PROJECT_ID.fullmatch(project_id):
                raise ValidationFailure('Повреждён ID в каталоге проектов')
            try:
                view = self.get_status(project_id)
                result.append({'project_id': project_id, 'kind': view['kind'],
                               'core_status': view['core_status'],
                               'active_stage': view['refs'].get('active_stage'),
                               'target_level': view['refs'].get('target_level')})
            except (HarnessError, OSError, ValueError):
                result.append({'project_id': project_id, 'kind': projects[project_id].get('kind'),
                               'core_status': 'UNAVAILABLE', 'active_stage': None, 'target_level': None})
        return result

    def read_handoff_artifact(self, project_id: str, artifact_id: str) -> bytes:
        """Resolve one immutable service-owned ZIP by opaque operation ID, not a path.

        Only the successful *owning* project and operation are eligible. The
        file is checked against the already recorded digest before any bytes
        are published by HTTP, with a finite read budget.
        """
        op = self.get_operation(project_id, artifact_id)
        if op['action'] == 'publish-project' and op['state'] == 'SUCCEEDED':
            from .local_web_preparation import read_preparation_artifact
            return read_preparation_artifact(self, project_id, artifact_id)
        if (op['action'] != 'prepare' or op['state'] != 'SUCCEEDED'
                or not isinstance(op.get('result'), dict)
                or op['result'].get('artifact_ref') != artifact_id):
            raise ValidationFailure('Артефакт не принадлежит завершённой операции prepare')
        directory = self.app_data / 'artifacts' / artifact_id
        path = directory / 'handoff.zip'
        if (_native_io_path(directory).is_symlink() or not _native_io_path(directory).is_dir() or _native_io_path(path).is_symlink()
                or not _native_io_path(path).is_file() or native_resolve(path) != self.app_data / 'artifacts' / artifact_id / 'handoff.zip'):
            raise ValidationFailure('Недоступен безопасный архив операции')
        stat = _native_io_path(path).stat()
        if stat.st_nlink != 1 or stat.st_size > 128 * 1024 * 1024:
            raise ValidationFailure('Архив операции не является ограниченным обычным файлом')
        with _native_io_path(path).open('rb') as source:
            data = source.read(128 * 1024 * 1024 + 1)
        if len(data) > 128 * 1024 * 1024:
            raise ValidationFailure('Архив операции превышает лимит')
        expected = op['result'].get('zip_sha256')
        actual = 'sha256:' + hashlib.sha256(data).hexdigest()
        if expected != actual:
            raise ValidationFailure('INTEGRITY_ERROR: архив операции изменён')
        return data

    # PH-LW-05: typed, explicitly scoped source operations. File streams only
    # come from authenticated upload POST. No generic path-bearing dispatcher.
    def create_provisional_intake(self, *, project_name: str, idempotency_key: str,
                                  no_documentation: bool = False) -> dict[str, Any]:
        from .local_web_sources_service import create_intake
        return create_intake(self, project_name=project_name, idempotency_key=idempotency_key,
                             no_documentation=no_documentation)

    def upload_sources(self, project_id: str, uploads: Any, *, mode: str,
                       expected_fingerprint: str, expected_source_revision: int) -> dict[str, Any]:
        from .local_web_sources_service import upload_sources
        return upload_sources(self, project_id, uploads, mode=mode,
                              expected_fingerprint=expected_fingerprint,
                              expected_source_revision=expected_source_revision)

    def select_no_documentation(self, project_id: str, *, expected_fingerprint: str,
                                expected_source_revision: int) -> dict[str, Any]:
        from .local_web_sources_service import select_no_documentation
        return select_no_documentation(self, project_id, expected_fingerprint=expected_fingerprint,
                                        expected_source_revision=expected_source_revision)

    def list_sources(self, project_id: str) -> dict[str, Any]:
        from .local_web_sources_service import list_sources
        return list_sources(self, project_id)

    def preview_source(self, project_id: str, document_ref: str) -> dict[str, Any]:
        from .local_web_sources_service import preview
        return preview(self, project_id, document_ref)

    def recover_source_import(self, project_id: str) -> dict[str, Any]:
        from .local_web_sources_service import recover
        return recover(self, project_id)

    def get_interview(self, project_id: str) -> dict[str, Any]:
        from .local_web_exchange import interview
        return interview(self, project_id)

    def get_approval_review(self, project_id: str) -> dict[str, Any]:
        from .local_web_approvals import review
        return review(self, project_id)

    def set_approval_actor(self, project_id: str, **request: Any) -> dict[str, Any]:
        from .local_web_approvals import set_actor
        return set_actor(self, project_id, **request)

    def decide_approval(self, project_id: str, **request: Any) -> dict[str, Any]:
        from .local_web_approvals import decide
        return decide(self, project_id, **request)

    def recover_approval(self, project_id: str) -> dict[str, Any]:
        from .local_web_approvals import recover
        return recover(self, project_id)

    def get_export_review(self, project_id: str) -> dict[str, Any]:
        from .local_web_exchange import export_review
        return export_review(self, project_id)

    def get_cli_connection(self):
        return self.cli_connection.status()

    def connect_cli(self):
        return self.cli_connection.connect()

    def select_cli_model(self, **request):
        return self.cli_connection.select_model(**request)

    def create_analysis_export(self, project_id: str, **request):
        from .local_web_exchange import create_analysis_export
        return create_analysis_export(self, project_id, **request)

    def start_cli_analysis(self, project_id: str, **request):
        from .local_web_cli_analysis import start
        return start(self, project_id, **request)

    def get_cli_analysis(self, project_id: str):
        from .local_web_cli_analysis import latest
        return latest(self, project_id)

    def cancel_cli_analysis(self, project_id: str, job_id: str):
        from .local_web_cli_analysis import cancel
        return cancel(self, project_id, job_id)

    def create_gpt_export(self, project_id: str, **request: Any) -> dict[str, Any]:
        from .local_web_exchange import create_export
        return create_export(self, project_id, **request)

    def read_gpt_export(self, project_id: str, exchange_id: str, name: str) -> bytes:
        from .local_web_exchange import download_export
        return download_export(self, project_id, exchange_id, name)

    def read_gpt_export_archive(self, project_id: str, exchange_id: str) -> bytes:
        from .local_web_exchange import download_archive
        return download_archive(self, project_id, exchange_id)

    def preview_gpt_reply(self, project_id: str, **request: Any) -> dict[str, Any]:
        from .local_web_exchange import preview_reply
        return preview_reply(self, project_id, **request)

    def answer_interview_question(self, project_id: str, **request):
        from .local_web_answers import answer_question
        return answer_question(self,project_id,**request)

    def commit_gpt_reply(self, project_id: str, import_id: str, **request: Any) -> dict[str, Any]:
        from .local_web_exchange import commit_reply
        return commit_reply(self, project_id, import_id, **request)

    def cancel_gpt_reply(self, project_id: str, import_id: str, **request: Any) -> dict[str, Any]:
        from .local_web_exchange import cancel_reply
        return cancel_reply(self, project_id, import_id, **request)

    def recover_gpt_reply(self, project_id: str) -> dict[str, Any]:
        from .local_web_exchange import recover_reply
        return recover_reply(self, project_id)

    def _path(self, operation_id: str) -> Path:
        if not isinstance(operation_id, str) or not _OPERATION_ID.fullmatch(operation_id):
            raise ValidationFailure('Неверный operation ID')
        return self.app_data / 'operations' / f'{operation_id}.json'

    @staticmethod
    def _operation_id(request: OperationRequest) -> str:
        data = f'{request.project_id}:{request.idempotency_key}'.encode('utf-8')
        return 'LWO-' + hashlib.sha256(data).hexdigest()[:32].upper()

    def _receipt(self, request: OperationRequest, opid: str, request_digest: str) -> dict[str, Any]:
        return {'kind': 'LOCAL_WEB_OPERATION_RECEIPT', 'receipt_version': 1,
                'operation_id': opid, 'project_ref': request.project_id,
                'action_id': _ACTIONS[request.action]['id'], 'idempotency_key': request.idempotency_key,
                'request_sha256': request_digest, 'expected_core_fingerprint': request.expected_fingerprint,
                'core_outcome': 'NOT_STARTED', 'created_at': utc_now(),
                **({'verification_consent':dict(request.payload)} if request.action=='verify' and request.payload else {})}

    def _load_op(self, opid: str) -> dict[str, Any]:
        path = self._path(opid)
        if not _native_io_path(path).is_file() or _native_io_path(path).is_symlink():
            raise ValidationFailure('Операция не найдена')
        value = load_data(path)
        if (not isinstance(value, dict) or value.get('operation_id') != opid
                or value.get('state') not in _ACTIVE | _TERMINAL or not isinstance(value.get('receipt'), dict)):
            raise ValidationFailure('Журнал операции повреждён; требуется ручная проверка')
        integrity = value.get('record_digest')
        if not isinstance(integrity, str) or integrity != self._hash(
                {k: v for k, v in value.items() if k != 'record_digest'}):
            raise ValidationFailure('INTEGRITY_ERROR: журнал операции не соответствует digest')
        if value['receipt'].get('operation_id') != opid or value['receipt'].get('project_ref') != value.get('project_id'):
            raise ValidationFailure('INTEGRITY_ERROR: несовпадение receipt и операции')
        return value

    def _save_op(self, op: dict[str, Any]) -> None:
        op['updated_at'] = utc_now()
        op['record_digest'] = self._hash({k: v for k, v in op.items() if k != 'record_digest'})
        if op.get('action') in {'publish-project','next','receive-result','manual-evidence','verify','complete','block','resume'} | set(_LIFECYCLE_ACTIONS):
            from .local_web_preparation import _write_record
            _write_record(self._path(op['operation_id']), op)
        else:
            write_data(self._path(op['operation_id']), op)

    def get_operation(self, project_id: str, operation_id: str) -> dict[str, Any]:
        op = self._load_op(operation_id)
        if op.get('project_id') != project_id:
            raise ValidationFailure('Операция не принадлежит этому проекту')
        self._registered(project_id, migration_receipt=op.get('action') in {'migrate-project','recover-migration'},
                         operation_snapshot=True)
        return op

    def submit(self, request: OperationRequest, *, check_current: bool = False) -> dict[str, Any]:
        """Idempotent enqueue. Same key different action/payload/fingerprint = conflict.

        HTTP admission checks current capabilities after resolving exact replay;
        all new operations still recheck the fingerprint inside the worker fence.
        """
        if self._closed:
            raise ValidationFailure('Сервис завершает работу')
        root, kind = self._registered(request.project_id)
        if kind == 'workspace':
            from .local_web_exchange import assert_no_pending_exchange
            assert_no_pending_exchange(root)
        spec = _ACTIONS.get(request.action)
        if spec is None:
            mapped = json.loads(resources.files('project_harness').joinpath(
                'resources/local_web/control_map_v1.json').read_text(encoding='utf-8'))['commands']
            code = 'ACTION_DISABLED' if any(item['cli'] == request.action for item in mapped) else 'UNKNOWN_ACTION'
            raise ValidationFailure(code + ': ' + _RU[code][0])
        from .local_web_lifecycle import compatible
        if not (compatible(request.action, kind) if request.action in _LIFECYCLE_ACTIONS else spec['kind'] == kind):
            raise ValidationFailure('Операция несовместима с типом корня')
        unknown = set(request.payload) - spec['fields']
        missing = spec['fields'] - set(request.payload) if request.action in set(_LIFECYCLE_ACTIONS) | {'update-draft', 'publish-project','receive-result','manual-evidence','complete','block','resume'} or (request.action=='verify' and request.payload) else set()
        if unknown or missing:
            raise ValidationFailure('Payload содержит лишние или недостающие поля', {'unknown': sorted(unknown), 'missing': sorted(missing)})
        if request.action == 'update-draft':
            if not isinstance(request.payload.get('expected_input_digest'), str) or not _FINGERPRINT.fullmatch(request.payload['expected_input_digest']):
                raise ValidationFailure('Требуется точный input digest')
        digest = self._hash({'action': request.action, 'payload': request.payload, 'fingerprint': request.expected_fingerprint})
        opid = self._operation_id(request)
        path = self._path(opid)
        # Serialize journaling across multiple service instances; operation root
        # fence is acquired later by the worker before the real core mutation.
        with project_operation_guard(self.app_data):
            if _native_io_path(path).exists():
                prior = self._load_op(opid)
                if prior['project_id'] != request.project_id or prior['request_digest'] != digest:
                    raise ValidationFailure('OPERATION_CONFLICT: ключ уже связан с другим запросом')
                return prior
            if check_current:
                current = self.get_status(request.project_id)
                enabled = {entry['action'] for entry in current['available_actions'] if entry['enabled']}
                if request.action not in enabled:
                    raise ValidationFailure('ACTION_DISABLED: действие недоступно в текущем статусе')
                if request.expected_fingerprint != current['fingerprint']:
                    raise ValidationFailure('STALE_FINGERPRINT: состояние изменилось, обновите статус')
            if len(list(native_glob(self.app_data / 'operations','*.json'))) >= 10_000:
                raise ValidationFailure('Журнал операций достиг установленного лимита')
            rec = {'operation_id': opid, 'project_id': request.project_id, 'action': request.action,
                   'request_digest': digest, 'expected_fingerprint': request.expected_fingerprint,
                   'created_at': utc_now(), 'updated_at': utc_now(), 'started_at': None,
                   'finished_at': None, 'state': 'QUEUED', 'phase': 'QUEUED',
                   'core_before': None, 'core_after': None, 'before_active_run_ref': None, 'expected_draft_after': None,
                   'result': None, 'error': None, 'receipt': self._receipt(request, opid, digest)}
            self._save_op(rec)
        with self._futures_lock:
            self._futures[opid] = self._worker.submit(self._execute, opid, root, kind, request)
        return self._load_op(opid)

    @staticmethod
    def _result_view(action: str, result: dict[str, Any]) -> dict[str, Any]:
        # Never persist prompts, source documents, full questionnaires, command
        # output or environment values in app-data's debug/operation journal.
        safe_keys = {'status', 'next_route', 'run_ref', 'task_ref', 'active_run', 'stage_plan_ref',
                     'gate_ref', 'first_ready_task_ref', 'first_jit_ref', 'session_ref',
                     'before_digest', 'after_digest', 'changed_fields', 'changed',
                     'approvals_invalidated', 'readiness_status', 'missing_approvals'}
        return {'action': action, 'core_status': result.get('status') or result.get('readiness_status') or 'COMPLETED',
                'refs': {k: v for k, v in result.items() if k in safe_keys and
                         (v is None or isinstance(v, (str, bool, int, list)))}}

    def _execute(self, opid: str, root: Path, kind: str, request: OperationRequest) -> None:
        try:
            with project_operation_guard(root):
                # Reconfirm catalog ownership and canonical state *inside* OS fence.
                current_root, current_kind = self._registered(request.project_id)
                if current_root != root or current_kind != kind:
                    raise ValidationFailure('STALE_FINGERPRINT: каталог проекта изменился')
                if kind == 'workspace':
                    from .local_web_exchange import assert_no_pending_exchange
                    assert_no_pending_exchange(root)
                    if request.action != 'publish-project':
                        from .local_web_preparation import _record_path
                        if _native_io_path(_record_path(self, request.project_id)).exists():
                            raise ValidationFailure('PREPARATION_ALREADY_STARTED: intake зафиксирован для публикации')
                op = self._load_op(opid)
                if op['state'] == 'CANCELLED':
                    return
                if op['state'] != 'QUEUED':
                    return
                actual = self.core_fingerprint(root, kind)
                if actual != request.expected_fingerprint:
                    raise ValidationFailure('STALE_FINGERPRINT: canonical state изменилось')
                op['core_before'] = actual
                if request.action == 'next':
                    from .runtime import project_status
                    before_active = project_status(root).get('active_run')
                    op['before_active_run_ref'] = before_active.get('run_ref') if isinstance(before_active, dict) else None
                if request.action == 'update-draft':
                    proposal = preview_draft_update(root, request.payload['patch'],
                                                    expected_input_digest=request.payload['expected_input_digest'])
                    op['expected_draft_after'] = proposal['after_digest']
                op['state'] = 'RUNNING'
                op['phase'] = 'PREPARED_INTENT'
                op['started_at'] = utc_now()
                op['receipt']['core_outcome'] = 'PENDING'
                self._save_op(op)
                # A safe cancellation is possible until this durable boundary;
                # after MUTATING, a UI cancel is explicitly forbidden.
                op['phase'] = 'MUTATING'
                self._save_op(op)
                if request.action == 'update-draft':
                    outcome = update_provisional_draft(root, request.payload['patch'],
                                    expected_input_digest=request.payload['expected_input_digest'])
                elif request.action == 'check-intake':
                    from .intake import check_intake
                    outcome = check_intake(root)
                elif request.action == 'publish-project':
                    from .local_web_preparation import execute_preparation
                    outcome = execute_preparation(self, request.project_id, opid, request.payload)
                elif request.action == 'prepare':
                    from .compiler import prepare_handoff
                    artifact_dir = self.app_data / 'artifacts' / opid
                    if _native_io_path(artifact_dir).exists():
                        raise ValidationFailure('OUTPUT_COLLISION: artifact directory already exists; explicit reconciliation required')
                    _native_io_path(artifact_dir).mkdir(mode=0o700)
                    output = artifact_dir / 'handoff.zip'
                    directory = artifact_dir / 'handoff'
                    outcome = prepare_handoff(root, output, keep_directory=directory)
                    if not _native_io_path(output).is_file() or not _native_io_path(directory).is_dir():
                        raise ValidationFailure('Core prepare returned without required outputs')
                    outcome = {'status': outcome.get('status', 'READY_FOR_CODEX'),
                               'artifact_ref': opid, 'zip_sha256': 'sha256:' + sha256_file(output)}
                elif request.action == 'next':
                    from .manual_tasks import next_manual_task
                    outcome = next_manual_task(root)
                elif request.action == 'validate-project':
                    from .validation import validate_project_directory
                    outcome = validate_project_directory(root)
                elif request.action == 'verify':
                    from .local_web_tasks import execute
                    outcome = execute(self,request.project_id,request.action,request.payload)
                elif request.action in {'receive-result','manual-evidence','complete','block','resume'}:
                    from .local_web_tasks import execute
                    outcome = execute(self,request.project_id,request.action,request.payload)
                elif request.action in _LIFECYCLE_ACTIONS:
                    from .local_web_lifecycle import execute
                    outcome = execute(self, request.project_id, opid, request.action, request.payload)
                else:
                    raise ValidationFailure('ACTION_DISABLED')
                if not isinstance(outcome, dict):
                    raise ValidationFailure('Core API returned invalid result')
                op['core_after'] = self.core_fingerprint(root, kind)
                op['result'] = self._result_view(request.action, outcome)
                if request.action in _LIFECYCLE_ACTIONS:
                    op['result']['lifecycle'] = outcome
                if request.action == 'publish-project':
                    op['result'] = outcome
                if request.action == 'prepare':
                    op['result']['artifact_ref'] = opid
                    op['result']['zip_sha256'] = outcome['zip_sha256']
                op['state'] = 'BLOCKED' if request.action in _LIFECYCLE_ACTIONS and outcome.get('status') in {'BLOCKED', 'FAIL'} else 'SUCCEEDED'
                op['phase'] = 'DONE'
                op['receipt']['core_outcome'] = 'CONFIRMED_COMMITTED'
                op['finished_at'] = utc_now()
                self._save_op(op)
        except BaseException as exc:  # Worker must persist interruption, never fabricate a success.
            try:
                op = self._load_op(opid)
                # A power-loss between core commit and this write leaves RUNNING;
                # an ordinary exception also requires reconciliation if core
                # changed or intent may have begun. Never auto-retry.
                code = 'VALIDATION_FAILED'
                if isinstance(exc, HarnessError):
                    code = self.present_error(exc)['code']
                    if 'STALE_FINGERPRINT' in exc.message:
                        code = 'STALE_FINGERPRINT'
                    elif 'OPERATION_CONFLICT' in exc.message or 'LOCKED' in exc.message:
                        code = 'OPERATION_CONFLICT'
                    elif exc.code == 'WAITING_INPUT':
                        code = 'WAITING_INPUT'
                    elif exc.code == 'WAITING_DECISION':
                        code = 'WAITING_DECISION'
                elif not isinstance(exc, Exception):
                    code = 'UNEXPECTED_ERROR'
                elif isinstance(exc, OSError) and request.action == 'publish-project':
                    code = 'PREPARATION_IO_BLOCKED'
                if op['state'] not in _TERMINAL:
                    op['state'] = 'BLOCKED' if op['phase'] == 'MUTATING' else 'FAILED'
                    op['phase'] = 'RECONCILIATION_REQUIRED' if op['state'] == 'BLOCKED' else 'REJECTED'
                    op['error'] = {'code': code, 'message_ru': _RU[code][0], 'next_action_ru': _RU[code][1]}
                    if request.action in _LIFECYCLE_ACTIONS and isinstance(exc, HarnessError):
                        # Actual validation errors are essential to a reviewed form.
                        op['error']['message_ru'] = exc.message
                        op['error']['details'] = exc.details
                    op['receipt']['core_outcome'] = 'UNKNOWN_RECONCILE' if op['state'] == 'BLOCKED' else 'CONFIRMED_REJECTED'
                    op['finished_at'] = utc_now()
                    self._save_op(op)
            except Exception:
                # A filesystem failure is not a success; the persisted RUNNING
                # intent remains for explicit crash reconciliation.
                pass
            if not isinstance(exc, Exception):
                raise

    def cancel_queued(self, project_id: str, operation_id: str) -> dict[str, Any]:
        root, _ = self._registered(project_id)
        with project_operation_guard(root):
            op = self.get_operation(project_id, operation_id)
            if op['state'] != 'QUEUED':
                raise ValidationFailure('CANCELLATION_UNSAFE: mutation started or result already final')
            op['state'] = 'CANCELLED'
            op['phase'] = 'BEFORE_MUTATION'
            op['finished_at'] = utc_now()
            op['receipt']['core_outcome'] = 'CONFIRMED_REJECTED'
            self._save_op(op)
            return op

    def reconcile_operation(self, project_id: str, operation_id: str) -> dict[str, Any]:
        """Explicit post-crash reconciliation. Never replays a core API/command.

        Durable core refs are checked first; Stage recovery uses the existing
        governed journal only when necessary, never a journal invented by UI.
        """
        root, kind = self._registered(project_id)
        with project_operation_guard(root):
            op = self.get_operation(project_id, operation_id)
            if op['action'] == 'publish-project':
                from .local_web_preparation import recover_preparation
                return recover_preparation(self, project_id, confirm=True)
            if op['state'] == 'SUCCEEDED' or op['state'] == 'CANCELLED':
                return op
            if op['state'] == 'QUEUED':
                op['state'] = 'INTERRUPTED'
                op['phase'] = 'NOT_STARTED'
                op['receipt']['core_outcome'] = 'CONFIRMED_REJECTED'
            elif op['state'] in {'RUNNING', 'BLOCKED'}:
                # Explicitly reconcile any incomplete canonical Stage journal
                # through the existing kernel recovery algorithm, never a UI
                # rollback or replay of next/verify/complete.
                if kind in {'project', 'migration'}:
                    from .stage_transactions import recover_stage_transactions
                    recover_stage_transactions(root)
                resolved = None
                if op['action'] in _LIFECYCLE_ACTIONS:
                    from .local_web_lifecycle import reconcile
                    resolved = reconcile(self, project_id, op)
                elif op['action'] == 'update-draft' and op.get('expected_draft_after'):
                    if draft_input_digest(root) == op['expected_draft_after']:
                        resolved = {'core_status': 'DRAFT_UPDATED', 'refs': {'after_digest': op['expected_draft_after']}}
                elif op['action'] == 'next':
                    # A changed active Run ref is NOT proof of *this* UI
                    # operation: an unrelated CLI/user may have started a
                    # later Run after the worker crash. The core has no
                    # operation-ID provenance field yet, so fail closed.
                    # Read the persisted Run for operator diagnosis only;
                    # never convert it into a fabricated UI success.
                    from .runtime import project_status
                    project_status(root)
                elif op['action'] == 'prepare':
                    archive = self.app_data / 'artifacts' / operation_id / 'handoff.zip'
                    if _native_io_path(archive).is_file() and not _native_io_path(archive).is_symlink():
                        from .validation import validate_handoff
                        verified = validate_handoff(archive)
                        if verified.get('status') == 'PASS':
                            resolved = {'core_status': 'READY_FOR_CODEX', 'artifact_ref': operation_id,
                                        'zip_sha256': 'sha256:' + sha256_file(archive)}
                if resolved:
                    op['state'] = 'SUCCEEDED'
                    op['phase'] = 'RECONCILED_FROM_CORE'
                    op['result'] = resolved
                    op['core_after'] = self.core_fingerprint(root, kind)
                    op['receipt']['core_outcome'] = 'CONFIRMED_COMMITTED'
                else:
                    op['state'] = 'BLOCKED'
                    op['phase'] = 'AMBIGUOUS_NEEDS_CORE_REVIEW'
                    op['error'] = {'code': 'AMBIGUOUS_COMMIT', 'message_ru': _RU['AMBIGUOUS_COMMIT'][0],
                                   'next_action_ru': _RU['AMBIGUOUS_COMMIT'][1]}
                    op['receipt']['core_outcome'] = 'UNKNOWN_RECONCILE'
            op['finished_at'] = utc_now()
            self._save_op(op)
            return op

    @staticmethod
    def present_error(exc: Exception) -> dict[str, str]:
        """Stable Russian user error envelope for future HTTP adapters."""
        if isinstance(exc, HarnessError):
            code = next((key for key in _RU if key in exc.message), exc.code)
            if code not in _RU:
                code = 'VALIDATION_FAILED'
        else:
            code = 'UNEXPECTED_ERROR'
        message, action = _RU[code]
        return {'code': code, 'message_ru': message, 'next_action_ru': action}

    def wait_for(self, operation_id: str, *, timeout: float | None = None) -> dict[str, Any]:
        """Local test/operator convenience; does not run/cancel an operation."""
        with self._futures_lock:
            future = self._futures.get(operation_id)
        if future is not None:
            future.result(timeout=timeout)
        return self._load_op(operation_id)

    def close(self) -> None:
        self._closed = True
        self._worker.shutdown(wait=True, cancel_futures=False)

    def __enter__(self) -> 'LocalWebService':
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()
