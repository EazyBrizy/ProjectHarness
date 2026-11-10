"""PH-LW-04: bind-first one-user Waitress launcher for native loopback UI."""
from __future__ import annotations

import os
from pathlib import Path
import socket
import sys
import webbrowser
import threading
from importlib.metadata import PackageNotFoundError, version

from .errors import ValidationFailure
from .local_web_service import LocalWebService


def default_app_data() -> Path:
    if os.name == 'nt':
        local_app_data = os.environ.get('LOCALAPPDATA')
        if not local_app_data:
            raise ValidationFailure('Для Local Web требуется локальный LOCALAPPDATA')
        return Path(local_app_data) / 'ProjectHarness'
    return Path(os.environ.get('XDG_DATA_HOME') or Path.home() / '.local' / 'share') / 'ProjectHarness'


def open_bound_loopback_socket() -> socket.socket:
    """Exclusive IPv4 loopback bind on port 0 prevents find-free-port races."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        if hasattr(socket, 'SO_EXCLUSIVEADDRUSE'):
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        sock.bind(('127.0.0.1', 0))
        sock.listen(16)
        if sock.getsockname()[0] != '127.0.0.1':
            raise RuntimeError('Loopback bind validation failed')
        return sock
    except BaseException:
        sock.close()
        raise


def create_loopback_server(service: LocalWebService, auth, sock: socket.socket):
    """One production WSGI configuration, also exercised by native acceptance."""
    from waitress import create_server
    from .local_web_http import WSGI_BODY_LIMIT, create_app
    address, port = sock.getsockname()
    if sock.family != socket.AF_INET or address != '127.0.0.1':
        raise ValidationFailure('Local Web requires a prebound IPv4 loopback socket')
    app = create_app(service, port=port, auth=auth)
    return create_server(app, sockets=[sock], threads=4, connection_limit=32,
                         backlog=16, channel_timeout=20,
                         max_request_body_size=WSGI_BODY_LIMIT,
                         max_request_header_size=16 * 1024,
                         clear_untrusted_proxy_headers=True,
                         trusted_proxy=None, expose_tracebacks=False,
                         ident='ProjectHarnessLocal')


def run_local_web(*, app_data: Path | None = None, open_browser: bool = True) -> int:
    """Start actual Waitress before opening a browser, never Flask dev server.

    For failure to auto-open, stdout shows a *non-authenticated*, copyable
    address only. Never print/log a bootstrap secret. Restart with a working
    browser integration to obtain a new one-time authenticated launch.
    """
    try:
        from flask import Flask  # validate both requirements before binding/listening
        from waitress import create_server
        if version('Flask') != '3.1.3' or version('Waitress') != '3.0.2':
            raise ValidationFailure('Для ui требуются строго Flask==3.1.3 и Waitress==3.0.2')
    except (ImportError, PackageNotFoundError) as exc:
        raise ValidationFailure('Для команды ui нужны pinned Flask и Waitress из Local Web lock; '
                                'никакой HTTP/Flask development-server fallback не допускается') from exc
    from .local_web_http import LocalWebAuth

    if os.name == 'nt':
        from .local_web_instance import UserInstanceLock, wait_existing
        # Identity is per OS user, irrespective of supplied app-data path.
        with UserInstanceLock() as owner:
            base = default_app_data() if app_data is None else app_data
            if not owner.owned:
                if open_browser:
                    open_local_browser(wait_existing(base))
                else:
                    raise ValidationFailure('Harness already running for this Windows user')
                return 0
            return _serve(base, open_browser=open_browser, desktop=True)
    return _serve(default_app_data() if app_data is None else app_data,
                  open_browser=open_browser, desktop=False)


def open_local_browser(url: str) -> bool:
    try:
        opened = webbrowser.open(url, new=1, autoraise=True)
    except (OSError, webbrowser.Error):
        opened = False
    if not opened:
        if os.name == 'nt':
            import ctypes
            # Native local display only: no stdout, query string or file log.
            # Ctrl+C in a Windows message box copies its displayed contents.
            origin, token = url.split('/#bootstrap=', 1)
            ctypes.windll.user32.MessageBoxW(None,
                'Браузер не открылся. Откройте адрес вручную:\n' + origin + '/\n\n'
                'Введите на странице одноразовый код (90 секунд):\n' + token + '\n\n'
                'Ctrl+C копирует текст этого окна. Новый запуск Harness выдаёт новый код. '
                'Сервер продолжает работать; завершите его кнопкой «Завершить Harness».',
                'Project Harness — локальный вход', 0x40)
        elif sys.stdout:
            print('Браузер не открылся. Повторите запуск с работающим браузером.', flush=True)
    return opened


def _serve(app_data: Path, *, open_browser: bool, desktop: bool) -> int:
    from .local_web_http import LocalWebAuth
    from .local_web_desktop import DesktopLifecycle
    sock = open_bound_loopback_socket()
    port = sock.getsockname()[1]
    origin = f'http://127.0.0.1:{port}'
    try:
        with LocalWebService(app_data) as service:
            auth = LocalWebAuth()
            service.desktop_lifecycle = DesktopLifecycle(service)
            # sockets=[already-bound socket] is the Waitress API for atomic
            # bind → server setup; do NOT release/rebind the chosen port.
            server = create_loopback_server(service, auth, sock)
            channel = None
            thread = threading.Thread(target=server.run, name='harness-waitress', daemon=True)
            try:
                thread.start()
                if desktop:
                    from .local_web_instance import LauncherChannel
                    channel = LauncherChannel(service.app_data, auth, port, service.desktop_lifecycle.stopping)
                if sys.stdout:
                    print(f'Локальный адрес (без секрета): {origin}/', flush=True)
                if open_browser:
                    token = auth.issue_bootstrap()
                    # The fragment never reaches the HTTP listener or Referer.
                    open_local_browser(f'{origin}/#bootstrap={token}')
                    del token
                elif sys.stdout:
                    print('Режим --no-browser не создаёт доступной из HTTP авторизации. '
                          'Используйте обычный запуск ui для входа.', flush=True)
                while thread.is_alive() and not service.desktop_lifecycle.stopping.wait(.2):
                    pass
                if not service.desktop_lifecycle.stopping.is_set():
                    raise ValidationFailure('Local Web listener stopped unexpectedly')
            except KeyboardInterrupt:
                # Block admissions and wait for committed/queued work; never kill it.
                service.desktop_lifecycle.stopping.set()
            finally:
                service.desktop_lifecycle.stopping.set()
                if channel:
                    channel.close()
                service.close()
                server.close()
                server.task_dispatcher.shutdown()
                thread.join(5)
        return 0
    finally:
        sock.close()
