"""PH-LW-11 OS ownership and mutually authenticated local launcher channel.

The DPAPI-protected record is private app state, never a diagnostic/export.
There is no command/path forwarding, HTTP bootstrap endpoint or process kill.
"""
from __future__ import annotations
import base64
import ctypes
from ctypes import wintypes
import hashlib
import hmac
import json
import os
from pathlib import Path
import secrets
import socket
import threading
import time

from .errors import ValidationFailure
from .platform_fs import ensure_native_path
from .serialization import write_data


def user_mutex_name() -> str:
    # SID, unlike a username or environment variable, identifies the OS user.
    adv = ctypes.WinDLL('advapi32', use_last_error=True)
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    adv.OpenProcessToken.argtypes = [wintypes.HANDLE, wintypes.DWORD, ctypes.POINTER(wintypes.HANDLE)]
    adv.GetTokenInformation.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p,
                                        wintypes.DWORD, ctypes.POINTER(wintypes.DWORD)]
    token = wintypes.HANDLE()
    if not adv.OpenProcessToken(kernel.GetCurrentProcess(), 8, ctypes.byref(token)):
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        size = wintypes.DWORD()
        adv.GetTokenInformation(token, 1, None, 0, ctypes.byref(size))
        buffer = ctypes.create_string_buffer(size.value)
        if not adv.GetTokenInformation(token, 1, buffer, size, ctypes.byref(size)):
            raise ctypes.WinError(ctypes.get_last_error())
        sid = ctypes.cast(buffer, ctypes.POINTER(ctypes.c_void_p))[0]
        value = wintypes.LPWSTR()
        adv.ConvertSidToStringSidW.argtypes = [ctypes.c_void_p, ctypes.POINTER(wintypes.LPWSTR)]
        if not adv.ConvertSidToStringSidW(sid, ctypes.byref(value)):
            raise ctypes.WinError(ctypes.get_last_error())
        try:
            return 'Global\\ProjectHarness-' + hashlib.sha256(value.value.encode()).hexdigest()[:32]
        finally:
            kernel.LocalFree.argtypes = [ctypes.c_void_p]
            kernel.LocalFree(value)
    finally:
        kernel.CloseHandle(token)


class UserInstanceLock:
    def __init__(self):
        self.handle = None
        self.setup_fence = None
        self.owned = False

    def __enter__(self):
        if os.name != 'nt':
            raise ValidationFailure('One-start launcher requires native Windows')
        self.kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        self.kernel.CreateMutexW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR]
        self.kernel.CreateMutexW.restype = wintypes.HANDLE
        self.kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
        self.kernel.ReleaseMutex.argtypes = [wintypes.HANDLE]
        self.kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        self.handle = self.kernel.CreateMutexW(None, False, user_mutex_name())
        if not self.handle:
            raise ctypes.WinError(ctypes.get_last_error())
        status = self.kernel.WaitForSingleObject(self.handle, 0)
        self.owned = status in (0, 0x80)  # abandoned mutex is safe to acquire
        if self.owned:
            self.setup_fence = self.kernel.CreateMutexW(None, False, 'Local\\ProjectHarnessLocalWeb')
            if not self.setup_fence:
                self.__exit__()
                raise ValidationFailure('Cannot create installer running fence')
        if status not in (0, 0x80, 258):
            self.__exit__()
            raise ValidationFailure('Cannot acquire per-user instance mutex')
        return self

    def __exit__(self, *_):
        if self.setup_fence:
            self.kernel.CloseHandle(self.setup_fence)
            self.setup_fence = None
        if self.handle:
            if self.owned:
                self.kernel.ReleaseMutex(self.handle)
            self.kernel.CloseHandle(self.handle)
            self.handle = None


def protect(data: bytes, *, decrypt: bool = False) -> bytes:
    class Blob(ctypes.Structure):
        _fields_ = [('size', wintypes.DWORD), ('data', ctypes.POINTER(ctypes.c_byte))]
    memory = ctypes.create_string_buffer(data)
    source = Blob(len(data), ctypes.cast(memory, ctypes.POINTER(ctypes.c_byte)))
    target = Blob()
    crypt = ctypes.WinDLL('crypt32', use_last_error=True)
    func = crypt.CryptUnprotectData if decrypt else crypt.CryptProtectData
    # CRYPTPROTECT_UI_FORBIDDEN; current-user DPAPI, never LOCAL_MACHINE.
    if not func(ctypes.byref(source), None, None, None, None, 1, ctypes.byref(target)):
        raise ValidationFailure('Local launcher credential cannot be decrypted')
    try:
        return ctypes.string_at(target.data, target.size)
    finally:
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel.LocalFree.argtypes = [ctypes.c_void_p]
        kernel.LocalFree(target.data)


def _send(stream, value):
    stream.sendall(json.dumps(value, separators=(',', ':')).encode('ascii') + b'\n')


def _receive(stream):
    data = bytearray()
    while len(data) <= 4096:
        byte = stream.recv(1)
        if not byte:
            raise ValidationFailure('Local handshake closed')
        if byte == b'\n':
            value = json.loads(data)
            if not isinstance(value, dict):
                raise ValidationFailure('Invalid local handshake')
            return value
        data.extend(byte)
    raise ValidationFailure('Local handshake too large')


def _mac(key, *values):
    return hmac.new(key, '\n'.join(values).encode('ascii'), hashlib.sha256).hexdigest()


class LauncherChannel:
    def __init__(self, app_data: Path, auth, port: int, stopping: threading.Event):
        from .local_web_launcher import open_bound_loopback_socket
        self.sock = open_bound_loopback_socket()
        self.sock.settimeout(.2)
        self.key = secrets.token_bytes(32)
        self.path = app_data / 'launcher-private.json'
        self.auth, self.port, self.stopping = auth, port, stopping
        self.closed = threading.Event()
        self.identity = secrets.token_hex(16)
        write_data(self.path, {'version': 1, 'port': self.sock.getsockname()[1],
            'identity': self.identity, 'key_dpapi': base64.b64encode(protect(self.key)).decode()})
        self.thread = threading.Thread(target=self._serve, name='harness-local-launcher', daemon=True)
        self.thread.start()

    def _serve(self):
        while not self.closed.is_set():
            try:
                client, _ = self.sock.accept()
            except (socket.timeout, OSError):
                continue
            with client:
                client.settimeout(2)
                try:
                    hello = _receive(client)
                    nonce = hello.get('nonce')
                    if set(hello) != {'nonce'} or not isinstance(nonce, str) or len(nonce) != 64:
                        continue
                    bytes.fromhex(nonce)
                    challenge = secrets.token_hex(32)
                    port = str(self.port)
                    _send(client, {'challenge': challenge, 'port': self.port,
                        'proof': _mac(self.key, 'server', nonce, challenge, port)})
                    request = _receive(client)
                    if set(request) != {'proof'} or not hmac.compare_digest(str(request['proof']),
                            _mac(self.key, 'client', nonce, challenge, port)) or self.stopping.is_set():
                        continue
                    token = self.auth.issue_bootstrap()
                    _send(client, {'token': token, 'proof': _mac(self.key, 'result', nonce, challenge, port, token)})
                except (OSError, ValueError, TypeError, ValidationFailure):
                    pass  # Never log peer bytes, credentials or exceptions containing them.

    def close(self):
        self.closed.set()
        self.sock.close()
        self.thread.join(3)
        try:
            if json.loads(self.path.read_text('utf-8'))['identity'] == self.identity:
                self.path.unlink()
        except (FileNotFoundError, ValueError, KeyError):
            pass


def connect_existing(app_data: Path) -> str:
    """Return a one-time URL only after verifying the server's fresh HMAC."""
    path = app_data / 'launcher-private.json'
    ensure_native_path(path, file_ok=True)
    if path.stat().st_size > 8192:
        raise ValidationFailure('Invalid instance record')
    record = json.loads(path.read_text('utf-8'))
    if set(record) != {'version', 'port', 'identity', 'key_dpapi'} or record['version'] != 1:
        raise ValidationFailure('Invalid instance record')
    port = record['port']
    if type(port) is not int or not 1 <= port <= 65535:
        raise ValidationFailure('Invalid instance port')
    key = protect(base64.b64decode(record['key_dpapi'], validate=True), decrypt=True)
    if len(key) != 32:
        raise ValidationFailure('Invalid instance credential')
    nonce = secrets.token_hex(32)
    with socket.create_connection(('127.0.0.1', port), timeout=3) as client:
        _send(client, {'nonce': nonce})
        reply = _receive(client)
        challenge, web_port = reply.get('challenge'), reply.get('port')
        if (not isinstance(challenge, str) or len(challenge) != 64 or type(web_port) is not int
                or not 1 <= web_port <= 65535 or not hmac.compare_digest(str(reply.get('proof')),
                _mac(key, 'server', nonce, challenge, str(web_port)))):
            raise ValidationFailure('Existing listener is not the authenticated Harness instance')
        _send(client, {'proof': _mac(key, 'client', nonce, challenge, str(web_port))})
        result = _receive(client)
        token = result.get('token')
        if (not isinstance(token, str) or not 40 <= len(token) <= 128 or not token.isascii()
                or not hmac.compare_digest(str(result.get('proof')),
                    _mac(key, 'result', nonce, challenge, str(web_port), token))):
            raise ValidationFailure('Launcher result authentication failed')
        return f'http://127.0.0.1:{web_port}/#bootstrap={token}'


def wait_existing(app_data: Path) -> str:
    for _ in range(30):
        try:
            return connect_existing(app_data)
        except (OSError, ValueError, ValidationFailure):
            time.sleep(.1)
    raise ValidationFailure('Harness уже запущен, но безопасное соединение не установлено. '
                            'Неизвестный процесс не остановлен. Повторите запуск позже.')
