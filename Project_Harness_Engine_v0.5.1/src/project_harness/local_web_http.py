"""PH-LW-04: same-origin Local Web shell without local login (manual only).

Flask is imported only by the UI launcher; console/core use no web dependency.
The only listener is the pre-bound IPv4 loopback socket owned by Waitress.
Neither this module nor browser assets implement an arbitrary filesystem route,
shell invocation, provider integration or automatic Codex execution.
"""
from __future__ import annotations

from importlib import resources
from io import BytesIO
import json
from typing import Any

from .errors import HarnessError, ValidationFailure
from .local_web_service import LocalWebService, OperationRequest


# The WSGI-facing limit is separately enforced by Waitress, *before* Flask
# receives a buffered body. JSON requests have a narrower application limit.
WSGI_BODY_LIMIT = 64 * 1024 * 1024
JSON_BODY_LIMIT = 512 * 1024
SMALL_JSON_BODY_LIMIT = 4096

CSP = "; ".join((
    "default-src 'none'",
    "base-uri 'none'",
    "script-src 'self'",
    "style-src 'self'",
    "connect-src 'self'",
    "img-src 'self'",
    "font-src 'none'",
    "object-src 'none'",
    "frame-src 'none'",
    "frame-ancestors 'none'",
    "form-action 'self'",
    "worker-src 'none'",
))


class WebError(Exception):
    def __init__(self, http_status: int, code: str, message: str) -> None:
        super().__init__(message)
        self.http_status = http_status
        self.code = code
        self.message = message


def _reject_pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
    result = {}
    for key, value in items:
        if key in result:
            raise ValueError('duplicate JSON key')
        result[key] = value
    return result


def _reject_constant(_value: str) -> None:
    raise ValueError('non-finite JSON value')


def create_app(service: LocalWebService, *, port: int):
    """Create Flask WSGI app with an exact 127.0.0.1:<bound-port> origin.

    Callable from an installed wheel independent of source working directory.
    The local interface opens directly; no accounts, sessions or login tokens.
    """
    from flask import Flask, Response, g, jsonify, request, send_file
    from werkzeug.exceptions import HTTPException

    if not isinstance(port, int) or not 1 <= port <= 65535:
        raise ValueError('Waitress must bind an actual loopback port before Flask initialization')
    origin = f'http://127.0.0.1:{port}'
    host = f'127.0.0.1:{port}'
    app = Flask(__name__, static_folder=None)
    app.config.update(DEBUG=False, TESTING=False, PROPAGATE_EXCEPTIONS=False,
                      MAX_CONTENT_LENGTH=WSGI_BODY_LIMIT, MAX_FORM_MEMORY_SIZE=JSON_BODY_LIMIT)
    from .local_web_desktop import DesktopLifecycle, read_resume, save_resume
    desktop = getattr(service, 'desktop_lifecycle', None)
    if desktop is None:
        desktop = DesktopLifecycle(service)
        service.desktop_lifecycle = desktop

    def fail(http_status: int, code: str, message: str):
        raise WebError(http_status, code, message)

    @app.before_request
    def exact_loopback_origin():
        # Compare the *raw* Host, including port. Never rely on DNS, localhost
        # alias resolution or proxy-derived host metadata.
        if request.environ.get('HTTP_HOST') != host or request.scheme != 'http':
            fail(403, 'HOST_REJECTED', 'Недопустимый Host или порт локального сервера.')
        if any(name in request.headers for name in ('Forwarded', 'X-Forwarded-Host',
                                                     'X-Forwarded-Proto', 'X-Original-URL')):
            fail(403, 'PROXY_REJECTED', 'Прокси-заголовки запрещены.')
        given_origin = request.environ.get('HTTP_ORIGIN')
        if given_origin is not None and given_origin != origin:
            fail(403, 'ORIGIN_REJECTED', 'Запрос поступил с другого Origin.')
        if request.method not in ('GET', 'HEAD', 'POST'):
            fail(405, 'METHOD_REJECTED', 'Метод HTTP не поддерживается.')
        if request.method == 'POST' and given_origin != origin:
            fail(403, 'ORIGIN_REQUIRED', 'Требуется точный Origin, включая порт.')
        if request.query_string:
            fail(400, 'QUERY_FORBIDDEN', 'Данные в URL query запрещены; используйте предусмотренные формы запросов.')
        if request.headers.get('Content-Encoding') not in (None, 'identity'):
            fail(415, 'ENCODING_REJECTED', 'Сжатые HTTP bodies не принимаются.')
        fetch_site = request.headers.get('Sec-Fetch-Site')
        if fetch_site is not None and fetch_site not in ('same-origin', 'none'):
            fail(403, 'CROSS_SITE_REJECTED', 'Межсайтовый запрос запрещён.')
        if request.method == 'POST' and request.path != '/api/desktop/stop':
            if not desktop.enter():
                fail(409, 'SERVER_STOPPING', 'Harness завершает работу. Новые изменения запрещены.')
            g.desktop_admitted = True

    @app.teardown_request
    def leave_desktop(_error):
        if getattr(g, 'desktop_admitted', False):
            desktop.leave()
            g.desktop_admitted = False

    @app.after_request
    def security_headers(response):
        response.headers['Content-Security-Policy'] = CSP
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Referrer-Policy'] = 'no-referrer'
        response.headers['Permissions-Policy'] = 'camera=(), microphone=(), geolocation=()'
        response.headers['Cache-Control'] = 'private, no-store, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        response.headers.pop('Access-Control-Allow-Origin', None)
        response.headers.pop('Access-Control-Allow-Credentials', None)
        return response

    @app.errorhandler(WebError)
    def web_error(exc: WebError):
        return jsonify({'status': 'FAILED', 'error': {'code': exc.code,
             'message_ru': exc.message, 'next_action_ru': 'Проверьте данные и актуальный статус.'}}), exc.http_status

    @app.errorhandler(HTTPException)
    def http_error(exc: HTTPException):
        return jsonify({'status': 'FAILED', 'error': {'code': 'HTTP_ERROR',
                        'message_ru': 'Неверный адрес или формат HTTP-запроса.',
                        'next_action_ru': 'Исправьте запрос и повторите явно.'}}), exc.code or 400

    @app.errorhandler(Exception)
    def internal_error(exc: Exception):
        from .local_web_cli import CliError
        if isinstance(exc, CliError):
            return jsonify({'status': 'FAILED', 'error': exc.public()}), exc.http_status
        from .local_web_exchange_contract import ExchangeError
        if isinstance(exc, ExchangeError):
            conflict = any(word in exc.exchange_code for word in ('STALE', 'CONFLICT', 'RECOVERY', 'CANCEL', 'PENDING', 'MISMATCH'))
            return jsonify({'status': 'FAILED', 'error': exc.public()}), 409 if conflict else 400
        # Keep private details (project paths, source filenames, traceback and
        # secrets) out of HTTP. Validation messages from the service are also
        # replaced by a stable, path-free status envelope.
        if isinstance(exc, HarnessError):
            public = LocalWebService.present_error(exc)
            code = public['code']
            status = 409 if code in ('STALE_FINGERPRINT', 'OPERATION_CONFLICT', 'ACTION_DISABLED') else 400
            return jsonify({'status': 'FAILED', 'error': public}), status
        return jsonify({'status': 'FAILED', 'error': {
            'code': 'INTERNAL_ERROR', 'message_ru': 'Операция не выполнена: внутренняя ошибка.',
            'next_action_ru': 'Не повторяйте изменение автоматически; проверьте локальную диагностику.'}}), 500

    def json_object(*, limit: int, fields: frozenset[str]) -> dict[str, Any]:
        if request.mimetype != 'application/json':
            fail(415, 'CONTENT_TYPE_REQUIRED', 'Требуется application/json.')
        if request.content_length is not None and request.content_length > limit:
            fail(413, 'BODY_TOO_LARGE', 'Превышен лимит тела HTTP-запроса.')
        payload = request.stream.read(limit + 1)
        if len(payload) > limit:
            fail(413, 'BODY_TOO_LARGE', 'Превышен лимит тела HTTP-запроса.')
        try:
            parsed = json.loads(payload.decode('utf-8', errors='strict'),
                                object_pairs_hook=_reject_pairs, parse_constant=_reject_constant)
        except (UnicodeError, ValueError, TypeError, RecursionError):
            fail(400, 'JSON_INVALID', 'Неверный JSON/UTF-8 или повторяющиеся ключи.')
        if not isinstance(parsed, dict) or set(parsed) != fields:
            fail(400, 'FIELDS_INVALID', 'Схема HTTP-запроса содержит недостающие или лишние поля.')
        return parsed

    @app.get('/health')
    def public_health():
        return jsonify({'status': 'ok'})  # no private paths or version details

    @app.get('/api/ui/resume')
    def desktop_resume():
        return jsonify(read_resume(service))

    @app.post('/api/ui/resume')
    def desktop_select():
        body = json_object(limit=SMALL_JSON_BODY_LIMIT,
                           fields=frozenset({'project_id', 'screen', 'expected_revision'}))
        return jsonify(save_resume(service, **body))

    @app.post('/api/desktop/stop')
    def desktop_stop():
        json_object(limit=SMALL_JSON_BODY_LIMIT, fields=frozenset())
        return jsonify(desktop.stop())

    @app.get('/')
    def index():
        page = resources.files('project_harness').joinpath(
            'resources/local_web/assets/index.html').read_bytes()
        return Response(page, mimetype='text/html; charset=utf-8')

    @app.get('/assets/<name>')
    def local_asset(name: str):
        types = {'app.js': 'text/javascript; charset=utf-8',
                 'interview.js': 'text/javascript; charset=utf-8',
                 'approvals.js': 'text/javascript; charset=utf-8',
                 'preparation.js': 'text/javascript; charset=utf-8',
                 'tasks.js': 'text/javascript; charset=utf-8',
                 'lifecycle.js': 'text/javascript; charset=utf-8',
                 'app.css': 'text/css; charset=utf-8'}
        if name not in types:
            fail(404, 'ASSET_UNKNOWN', 'Локальный asset не найден.')
        contents = resources.files('project_harness').joinpath('resources/local_web/assets', name).read_bytes()
        return Response(contents, content_type=types[name])

    # PH-LW-05: explicit project-owned source import; no path-bearing JSON.
    @app.post('/api/intakes')
    def create_provisional_intake():
        value = json_object(limit=JSON_BODY_LIMIT, fields=frozenset({
            'project_name', 'no_documentation', 'idempotency_key'}))
        result = service.create_provisional_intake(**value)
        return jsonify(result), 201 if not result['replayed'] else 200

    @app.get('/api/projects/<project_id>/sources')
    def source_inventory(project_id: str):
        raw = service.list_sources(project_id)
        allowed_source = ('source_ref', 'original_name', 'safe_storage_name', 'byte_size',
                          'sha256', 'format', 'import_revision')
        allowed_doc = ('document_ref', 'source_ref', 'original_name', 'source_relative_path',
                       'byte_size', 'sha256', 'import_revision', 'extraction_provenance', 'encoding')
        return jsonify({'project_id': project_id, 'source_revision': raw['source_revision'],
            'snapshot_ref': raw['snapshot_ref'], 'documentation_choice': raw['documentation_choice'],
            'analysis_status': raw['analysis_status'],
            'sources': [{k: item.get(k) for k in allowed_source} for item in raw['sources']],
            'documents': [{k: item.get(k) for k in allowed_doc} for item in raw['documents']],
            'skipped': raw['skipped']})

    @app.get('/api/projects/<project_id>/documents/<document_ref>/preview')
    def document_preview(project_id: str, document_ref: str):
        return jsonify(service.preview_source(project_id, document_ref))

    @app.post('/api/projects/<project_id>/sources/upload')
    def upload_documents(project_id: str):
        from .local_web_imports import HTTP_BODY_MAX, MAX_UPLOADS
        if request.mimetype != 'multipart/form-data':
            fail(415, 'CONTENT_TYPE_REQUIRED', 'Для документов требуется multipart/form-data.')
        if request.content_length is not None and request.content_length > HTTP_BODY_MAX:
            fail(413, 'BODY_TOO_LARGE', 'Размер HTTP-запроса превышает 64 MiB.')
        scalar_fields = {'mode', 'expected_fingerprint', 'expected_source_revision'}
        if (set(request.form) != scalar_fields or
                any(len(request.form.getlist(field)) != 1 for field in scalar_fields)):
            fail(400, 'FIELDS_INVALID', 'Неверные поля формы импорта.')
        if set(request.files) != {'files'}:
            fail(400, 'FIELDS_INVALID', 'Ожидаются только файлы под полем files.')
        try:
            revision = int(request.form['expected_source_revision'])
            if str(revision) != request.form['expected_source_revision'] or revision < 0:
                raise ValueError
        except (ValueError, TypeError):
            fail(400, 'FIELDS_INVALID', 'Недопустимая ревизия источников.')
        files = request.files.getlist('files')
        if not 1 <= len(files) <= MAX_UPLOADS or any(not item.filename for item in files):
            fail(400, 'UPLOAD_COUNT_LIMIT', 'Выберите от 1 до 100 MD/ZIP файлов.')
        result = service.upload_sources(project_id, [(file.filename, file.stream) for file in files],
                    mode=request.form['mode'], expected_fingerprint=request.form['expected_fingerprint'],
                    expected_source_revision=revision)
        return jsonify(result)

    @app.post('/api/projects/<project_id>/sources/no-documentation')
    def confirm_no_docs(project_id: str):
        value = json_object(limit=JSON_BODY_LIMIT, fields=frozenset({
            'expected_fingerprint', 'expected_source_revision'}))
        return jsonify(service.select_no_documentation(project_id, **value))

    @app.post('/api/projects/<project_id>/sources/recover')
    def recover_import(project_id: str):
        value = json_object(limit=JSON_BODY_LIMIT, fields=frozenset({'confirm'}))
        if value['confirm'] is not True:
            fail(400, 'CONFIRM_REQUIRED', 'Восстановление требует явного подтверждения.')
        return jsonify(service.recover_source_import(project_id))

    # PH-LW-06: typed answers use update-draft; check-intake remains an explicit
    # operation POST. This separate namespace never invokes provider APIs.
    @app.get('/api/projects/<project_id>/interview')
    def read_interview(project_id: str):
        return jsonify(service.get_interview(project_id))

    @app.get('/api/cli')
    def cli_status():
        return jsonify(service.get_cli_connection())

    @app.post('/api/cli/connect')
    def cli_connect():
        json_object(limit=1024, fields=frozenset())
        return jsonify(service.connect_cli())

    @app.post('/api/projects/<project_id>/analysis/package')
    def analysis_package(project_id: str):
        value = json_object(limit=4096, fields=frozenset({'expected_fingerprint', 'idempotency_key'}))
        return jsonify(service.create_analysis_export(project_id, **value)), 201

    @app.get('/api/projects/<project_id>/cli/analysis')
    def cli_analysis_status(project_id: str):
        return jsonify(service.get_cli_analysis(project_id))

    @app.post('/api/projects/<project_id>/cli/analysis')
    def cli_analysis_start(project_id: str):
        value = json_object(limit=4096, fields=frozenset({'expected_fingerprint', 'idempotency_key'}))
        return jsonify(service.start_cli_analysis(project_id, **value)), 202

    @app.post('/api/projects/<project_id>/cli/analysis/<job_id>/cancel')
    def cli_analysis_cancel(project_id: str, job_id: str):
        json_object(limit=1024, fields=frozenset())
        return jsonify(service.cancel_cli_analysis(project_id, job_id))

    @app.get('/api/projects/<project_id>/gpt/export-review')
    def gpt_export_review(project_id: str):
        return jsonify(service.get_export_review(project_id))

    @app.post('/api/projects/<project_id>/gpt/exports')
    def gpt_export(project_id: str):
        value = json_object(limit=JSON_BODY_LIMIT, fields=frozenset({
            'expected_fingerprint', 'review_digest', 'classifications', 'draft_classification',
            'consent', 'idempotency_key'}))
        return jsonify(service.create_gpt_export(project_id, **value))

    @app.get('/api/projects/<project_id>/gpt/exports/<exchange_id>/archive.zip')
    def gpt_archive(project_id: str, exchange_id: str):
        data = service.read_gpt_export_archive(project_id, exchange_id)
        return send_file(BytesIO(data), mimetype='application/zip', as_attachment=True,
                         download_name='harness-analysis.zip', max_age=0, conditional=False)

    @app.get('/api/projects/<project_id>/gpt/exports/<exchange_id>/<name>')
    def gpt_download(project_id: str, exchange_id: str, name: str):
        data = service.read_gpt_export(project_id, exchange_id, name)
        return send_file(BytesIO(data), mimetype='text/markdown; charset=utf-8', as_attachment=True,
                         download_name=name, max_age=0, conditional=False)

    @app.post('/api/projects/<project_id>/gpt/replies/preview')
    def gpt_preview(project_id: str):
        # JSON wrapper escapes the pasted JSON string, up to twice its bytes.
        value = json_object(limit=2 * JSON_BODY_LIMIT + 4096, fields=frozenset({'text', 'expected_fingerprint'}))
        result = service.preview_gpt_reply(project_id, **value)
        return jsonify(result), 422 if result['status'] == 'REJECTED' else 200

    @app.post('/api/projects/<project_id>/gpt/replies/<import_id>/commit')
    def gpt_commit(project_id: str, import_id: str):
        value = json_object(limit=4096, fields=frozenset({'preview_digest', 'expected_fingerprint'}))
        return jsonify(service.commit_gpt_reply(project_id, import_id, **value))

    @app.post('/api/projects/<project_id>/gpt/replies/<import_id>/cancel')
    def gpt_cancel(project_id: str, import_id: str):
        value = json_object(limit=4096, fields=frozenset({'preview_digest'}))
        return jsonify(service.cancel_gpt_reply(project_id, import_id, **value))

    @app.post('/api/projects/<project_id>/gpt/replies/recover')
    def gpt_recover(project_id: str):
        value = json_object(limit=4096, fields=frozenset({'confirm'}))
        if value['confirm'] is not True:
            fail(400, 'CONFIRM_REQUIRED', 'Сверка требует явного действия.')
        return jsonify(service.recover_gpt_reply(project_id))

    @app.get('/api/projects/<project_id>/approvals')
    def approval_review(project_id: str):
        return jsonify(service.get_approval_review(project_id))

    @app.post('/api/projects/<project_id>/approvals/actor')
    def approval_actor(project_id: str):
        value = json_object(limit=4096, fields=frozenset({'actor', 'expected_fingerprint'}))
        return jsonify(service.set_approval_actor(project_id, **value))

    @app.post('/api/projects/<project_id>/approvals/decisions')
    def approval_decision(project_id: str):
        value = json_object(limit=16384, fields=frozenset({'subject', 'decision', 'comment',
            'review_digest', 'subject_digest', 'expected_fingerprint', 'idempotency_key', 'confirm'}))
        return jsonify(service.decide_approval(project_id, **value))

    @app.post('/api/projects/<project_id>/approvals/recover')
    def approval_recovery(project_id: str):
        value = json_object(limit=4096, fields=frozenset({'confirm'}))
        if value['confirm'] is not True:
            fail(400, 'CONFIRM_REQUIRED', 'Сверка требует явного действия.')
        return jsonify(service.recover_approval(project_id))

    @app.post('/api/local-selection')
    def local_selection():
        value = json_object(limit=4096, fields=frozenset({'purpose', 'project_name', 'mode', 'idempotency_key'}))
        from .local_web_selection import select
        return jsonify(select(service, **value)), 201

    @app.get('/api/projects')
    def projects():
        return jsonify({'projects': service.list_projects()})

    @app.get('/api/projects/<project_id>/preparation')
    def preparation_status(project_id: str):
        from .local_web_preparation import get_preparation
        return jsonify(get_preparation(service, project_id))

    @app.post('/api/projects/<project_id>/preparation/target')
    def preparation_target(project_id: str):
        from .local_web_preparation import confirm_target
        value = json_object(limit=4096, fields=frozenset({'folder_name', 'binding_digest', 'expected_fingerprint', 'confirm'}))
        return jsonify(confirm_target(service, project_id, **value))

    @app.post('/api/projects/<project_id>/preparation/start')
    def preparation_start(project_id: str):
        from .local_web_preparation import submit_preparation
        value = json_object(limit=4096, fields=frozenset({'target_id', 'binding_digest', 'expected_fingerprint', 'idempotency_key'}))
        op = submit_preparation(service, project_id, **value)
        return jsonify({'operation_id': op['operation_id'], 'state': op['state']}), 202

    @app.post('/api/projects/<project_id>/preparation/recover')
    def preparation_recover(project_id: str):
        from .local_web_preparation import recover_preparation
        value = json_object(limit=4096, fields=frozenset({'confirm'}))
        op = recover_preparation(service, project_id, **value)
        return jsonify({'operation_id': op['operation_id'], 'state': op['state']})

    @app.get('/api/projects/<project_id>/preparation/<operation_id>/prompt')
    def preparation_prompt(project_id: str, operation_id: str):
        from .local_web_preparation import read_preparation_artifact
        return jsonify({'prompt': read_preparation_artifact(service, project_id, operation_id, prompt=True).decode('utf-8')})

    @app.post('/api/projects/<project_id>/preparation/open-folder')
    def preparation_open_folder(project_id: str):
        from .local_web_preparation import open_prepared_folder
        value = json_object(limit=4096, fields=frozenset({'confirm'}))
        return jsonify(open_prepared_folder(service, project_id, **value))

    @app.get('/api/projects/<project_id>/lifecycle')
    def lifecycle_view(project_id: str):
        from .local_web_lifecycle import view
        return jsonify(view(service, project_id))

    @app.get('/api/projects/<project_id>/lifecycle/drafts/<draft_id>')
    def lifecycle_draft(project_id: str, draft_id: str):
        from .local_web_lifecycle import read_draft
        return jsonify(read_draft(service, project_id, draft_id))

    @app.get('/api/projects/<project_id>/tasks')
    def task_view(project_id: str):
        from .local_web_tasks import view
        return jsonify(view(service,project_id))

    @app.post('/api/projects/<project_id>/tasks/result-upload')
    def task_result_upload(project_id: str):
        from .local_web_tasks import stage_result
        if request.mimetype != 'multipart/form-data':
            fail(415,'CONTENT_TYPE_REQUIRED','Выберите JSON-файл результата.')
        if request.content_length is None or request.content_length > 1024*1024+16384:
            fail(413,'BODY_TOO_LARGE','Result upload ограничен 1 MiB.')
        if set(request.form)!={'expected_fingerprint','binding_digest'} or any(len(request.form.getlist(k))!=1 for k in request.form):
            fail(400,'FIELDS_INVALID','Требуются exact revision и Run binding.')
        if set(request.files)!={'result'} or len(request.files.getlist('result'))!=1:
            fail(400,'FIELDS_INVALID','Требуется один result file.')
        raw=request.files['result'].stream.read(1024*1024+1)
        return jsonify(stage_result(service,project_id,raw,**request.form.to_dict())),201

    @app.post('/api/projects/<project_id>/operations/<operation_id>/reconcile')
    def reconcile_task_operation(project_id: str,operation_id: str):
        value=json_object(limit=1024,fields=frozenset({'confirm'}))
        if value['confirm'] is not True: fail(400,'CONFIRM_REQUIRED','Требуется явная сверка без повторного запуска.')
        operation=service.get_operation(project_id,operation_id)
        if operation['action'] not in {'next','receive-result','manual-evidence','verify','complete','block','resume'}:
            fail(400,'ACTION_DISABLED','Используйте форму соответствующей операции.')
        result=service.reconcile_operation(project_id,operation_id)
        return jsonify({'operation_id':result['operation_id'],'state':result['state'],'error':result['error']})

    @app.get('/api/projects/<project_id>')
    def project_status(project_id: str):
        return jsonify({'project': service.get_status(project_id)})

    @app.get('/api/projects/<project_id>/operations/<operation_id>')
    def operation_status(project_id: str, operation_id: str):
        value = service.get_operation(project_id, operation_id)
        # Whitelist only public, bounded status; omit original request, raw
        # core result data and idempotency keys from the browser response.
        fields = ('operation_id', 'state', 'phase', 'action', 'updated_at',
                  'finished_at', 'error', 'result')
        return jsonify({'operation': {key: value.get(key) for key in fields}})

    @app.post('/api/projects/<project_id>/operations')
    def submit_operation(project_id: str):
        value = json_object(limit=JSON_BODY_LIMIT, fields=frozenset({
            'action', 'payload', 'idempotency_key', 'expected_fingerprint'}))
        if value['action'] == 'prepare':
            fail(409, 'PREPARATION_TARGET_REQUIRED', 'Подтвердите новую папку во вкладке «Согласования».')
        if value['action'] == 'publish-project':
            fail(409, 'PREPARATION_TARGET_REQUIRED', 'Используйте отдельную форму подготовки с подтверждённой папкой.')
        request_dto = OperationRequest(project_id, value['action'], value['payload'],
                                       value['idempotency_key'], value['expected_fingerprint'])
        # Service resolves exact replay before admission against current state.
        # A committed operation necessarily makes its original revision stale.
        outcome = service.submit(request_dto, check_current=True)
        return jsonify({'operation_id': outcome['operation_id'], 'state': outcome['state']}), 202

    @app.get('/api/projects/<project_id>/artifacts/<artifact_id>')
    def handoff_download(project_id: str, artifact_id: str):
        data = service.read_handoff_artifact(project_id, artifact_id)
        return send_file(BytesIO(data), mimetype='application/zip', as_attachment=True,
                         download_name='harness-handoff.zip', max_age=0, conditional=False)

    return app
