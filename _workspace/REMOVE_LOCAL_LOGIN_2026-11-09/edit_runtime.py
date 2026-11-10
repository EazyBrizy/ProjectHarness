"""Apply the explicit no-local-login contract to the inspected runtime."""
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
SRC=ROOT/'Project_Harness_Engine_v0.5.1/src/project_harness'

def save(path,text): path.write_text(text,'utf-8')
def replace(text,old,new):
    assert old in text,old[:100]
    return text.replace(old,new)

p=SRC/'local_web_http.py';s=p.read_text('utf-8')
s=replace(s,'same-origin authenticated Local Web shell','same-origin Local Web shell without local login')
for line in ('from dataclasses import dataclass\n','from hashlib import sha256\n','from hmac import compare_digest\n','import secrets\n','from threading import Lock\n','import time\n'):
    s=replace(s,line,'')
s=replace(s,'from typing import Any, Callable','from typing import Any')
start=s.index('BOOTSTRAP_BODY_LIMIT =');end=s.index('\nCSP =',start)
s=s[:start]+'SMALL_JSON_BODY_LIMIT = 4096\n'+s[end:]
start=s.index('@dataclass\nclass _Session:');end=s.index('class WebError',start)
s=s[:start]+s[end:]
s=replace(s,'def create_app(service: LocalWebService, *, port: int,\n               auth: LocalWebAuth | None = None):','def create_app(service: LocalWebService, *, port: int):')
s=replace(s,'    Bootstrap access belongs exclusively to the caller, not to any HTTP route.\n','    The local interface opens directly; no accounts, sessions or login tokens.\n')
s=replace(s,'from flask import Flask, Response, g, jsonify, make_response, request, send_file','from flask import Flask, Response, g, jsonify, request, send_file')
s=replace(s,'    auth = auth if auth is not None else LocalWebAuth()\n','')
s=replace(s,'MAX_FORM_MEMORY_SIZE=JSON_BODY_LIMIT,\n                      SESSION_COOKIE_NAME=SESSION_COOKIE)','MAX_FORM_MEMORY_SIZE=JSON_BODY_LIMIT)')
s=replace(s,"    app.extensions['harness_local_auth'] = auth\n",'')
s=replace(s,'def exact_origin_and_session():','def exact_loopback_origin():')
s=replace(s,'Данные в URL query запрещены; не передавайте туда коды входа или пути.','Данные в URL query запрещены; используйте предусмотренные формы запросов.')
start=s.index("        if request.path == '/health' or");end=s.index("        if request.method == 'POST' and request.path != '/api/desktop/stop':",start)
s=s[:start]+s[end:]
s=replace(s,'Проверьте сессию, данные и актуальный статус.','Проверьте данные и актуальный статус.')
s=s.replace('BOOTSTRAP_BODY_LIMIT','SMALL_JSON_BODY_LIMIT')
start=s.index("    @app.post('/api/session/bootstrap')");end=s.index('    # PH-LW-05:',start)
s=s[:start]+s[end:];save(p,s)

p=SRC/'local_web_launcher.py';s=p.read_text('utf-8')
s=replace(s,'def create_loopback_server(service: LocalWebService, auth, sock: socket.socket):','def create_loopback_server(service: LocalWebService, sock: socket.socket):')
s=replace(s,'create_app(service, port=port, auth=auth)','create_app(service, port=port)')
s=s.replace('    from .local_web_http import LocalWebAuth\n','')
start=s.index('    For failure to auto-open, stdout shows');end=s.index('    """',start)
s=s[:start]+'    The plain loopback address opens the application directly.\n'+s[end:]
start=s.index('            # Native local display only:');end=s.index('        elif sys.stdout:',start)
s=s[:start]+'''            ctypes.windll.user32.MessageBoxW(None,
                'Браузер не открылся. Откройте этот адрес вручную:\\n' + url +
                '\\n\\nHarness продолжает работать.', 'Project Harness', 0x40)
'''+s[end:]
s=replace(s,'            auth = LocalWebAuth()\n','')
s=replace(s,'create_loopback_server(service, auth, sock)','create_loopback_server(service, sock)')
s=replace(s,'                    from .local_web_instance import LauncherChannel\n                    channel = LauncherChannel(service.app_data, auth, port, service.desktop_lifecycle.stopping)',
'''                    from .local_web_instance import LauncherInstance
                    channel = LauncherInstance(service.app_data, port)''')
start=s.index('                if open_browser:\n',s.index('def _serve('));end=s.index('                while thread.is_alive()',start)
s=s[:start]+'''                if open_browser:
                    open_local_browser(origin + '/')
'''+s[end:]
s=s.replace('Локальный адрес (без секрета):','Локальный адрес:');save(p,s)

p=SRC/'local_web_instance.py';s=p.read_text('utf-8')
mutex=s[s.index('def user_mutex_name()'):s.index('def protect(')]
header='''"""Per-user instance lock and plain loopback address discovery; no login."""
from __future__ import annotations
import ctypes
from ctypes import wintypes
import hashlib
import http.client
import json
import os
from pathlib import Path
import time
from .errors import ValidationFailure
from .platform_fs import ensure_native_path, _native_io_path
from .serialization import write_data

'''
tail='''class LauncherInstance:
    """Publish only this process ID and its loopback HTTP port."""
    def __init__(self, app_data: Path, port: int):
        ensure_native_path(app_data)
        if not isinstance(port, int) or isinstance(port, bool) or not 1 <= port <= 65535:
            raise ValidationFailure('Invalid loopback port')
        self.path = app_data / 'launcher-instance.json'
        self.record = {'version': 2, 'pid': os.getpid(), 'port': port}
        write_data(self.path, self.record)
        # Retire the former login rendezvous only after acquiring the user lock.
        legacy = app_data / 'launcher-private.json'
        ensure_native_path(legacy)
        _native_io_path(legacy).unlink(missing_ok=True)

    def close(self):
        try:
            if _read_record(self.path) == self.record:
                _native_io_path(self.path).unlink()
        except (OSError, ValueError, ValidationFailure):
            pass  # never remove an unknown replacement record

def _read_record(path: Path):
    ensure_native_path(path)
    with _native_io_path(path).open('rb') as stream:
        raw = stream.read(4097)
    if len(raw) > 4096:
        raise ValidationFailure('Invalid launcher instance record')
    value = json.loads(raw)
    if (not isinstance(value, dict) or set(value) != {'version', 'pid', 'port'} or value['version'] != 2
        or type(value['pid']) is not int or value['pid'] <= 0
        or type(value['port']) is not int or not 1 <= value['port'] <= 65535):
        raise ValidationFailure('Invalid launcher instance record')
    return value

def _process_running(pid: int):
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    handle = kernel.OpenProcess(0x1000, False, pid)
    if not handle:
        return False
    try:
        code = wintypes.DWORD()
        return bool(kernel.GetExitCodeProcess(handle, ctypes.byref(code))) and code.value == 259
    finally:
        kernel.CloseHandle(handle)

def connect_existing(app_data: Path) -> str:
    record = _read_record(app_data / 'launcher-instance.json')
    if not _process_running(record['pid']):
        raise ValidationFailure('Recorded Harness process is not running')
    connection = http.client.HTTPConnection('127.0.0.1', record['port'], timeout=2)
    try:
        connection.request('GET', '/health')
        response = connection.getresponse()
        raw = response.read(257)
        if response.status != 200 or len(raw) > 256 or json.loads(raw) != {'status': 'ok'}:
            raise ValidationFailure('Recorded Harness address is not ready')
    finally:
        connection.close()
    return f"http://127.0.0.1:{record['port']}/"

def wait_existing(app_data: Path) -> str:
    for _ in range(30):
        try:
            return connect_existing(app_data)
        except (OSError, ValueError, ValidationFailure):
            time.sleep(.1)
    raise ValidationFailure('Harness уже запущен, но его адрес пока недоступен. Повторите запуск позже.')
'''
save(p,header+mutex+tail)

ASSETS=SRC/'resources/local_web/assets'
p=ASSETS/'app.js';s=p.read_text('utf-8')
start=s.index('// Consume the fragment');end=s.index('const state =',start)
s=s[:start]+s[end:]
s=replace(s,'{ csrf: null, projects:','{ connected: false, projects:')
s=replace(s,"    if (state.csrf) headers['X-CSRF-Token'] = state.csrf;\n",'')
s=replace(s,"credentials: 'same-origin'","credentials: 'omit'")
s=replace(s,'    if (response.status === 401) lockSession();\n','')
start=s.index('function lockSession()');end=s.index('function selectScreen(',start)
s=s[:start]+s[end:]
start=s.index('async function logout()');end=s.index('for (const button of document.querySelectorAll',start)
s=s[:start]+s[end:]
s=replace(s,"  if (!state.csrf) return documentError('Локальная сессия завершена. Войдите снова через ярлык Harness.', 'new-project-name');\n",'')
s=replace(s,"  xhr.setRequestHeader('X-CSRF-Token', state.csrf);\n",'')
s=replace(s,"$('logout').addEventListener('click', logout);\n",'')
s=replace(s,'  if (!state.csrf) return;','  if (!state.connected) return;')
s=replace(s,"    lockSession(); showNotice('Harness завершает работу. Эту вкладку можно закрыть. Проекты сохранены.', 'success');",'''    state.connected = false;
    $('refresh').disabled = true; $('stop-harness').disabled = true;
    text('connection-state', 'Сервер остановлен');
    showNotice('Harness завершает работу. Эту вкладку можно закрыть. Проекты сохранены.', 'success');''')
start=s.index("$('manual-login').addEventListener");end=s.index('async function restoreDesktop(',start)
s=s[:start]+s[end:]
s=replace(s,'async function restoreDesktop(launcherSelection = false)','async function restoreDesktop()')
start=s.index('  // A new cookie-authenticated tab');end=s.index('  try { selectScreen(',start)
s=s[:start]+"  const fallbackScreen = saved.screen || 'projects';\n"+s[end:]
start=s.index('(async function initialize()')
s=s[:start]+'''(async function initialize() {
  try {
    await restoreDesktop();
    state.connected = true;
    $('refresh').disabled = false; $('stop-harness').disabled = false;
    text('connection-state', 'Сервер готов');
  } catch (err) {
    text('connection-state', 'Нет соединения');
    showNotice('Не удалось подключиться к Harness. Запустите его через ярлык и обновите страницу.', 'error');
  }
})();
''';save(p,s)
for name in ('interview.js','approvals.js','preparation.js','tasks.js','lifecycle.js'):
    p=ASSETS/name;s=p.read_text('utf-8')
    s=s.replace('!state.csrf || ','').replace('!state.csrf ||','')
    save(p,s)
p=ASSETS/'index.html';s=p.read_text('utf-8')
s=replace(s,'<span id="session-state" role="status" class="status">Проверка входа…</span>',
    '<span id="connection-state" role="status" class="status">Подключение…</span>')
s=replace(s,'          <button type="button" id="logout" class="quiet" disabled>Выйти</button>\n','')
start=s.index('      <section id="session-gate"');end=s.index('      <section id="content"',start)
s=s[:start]+s[end:];s=replace(s,'<section id="content" class="hidden"','<section id="content"')
save(p,s)
