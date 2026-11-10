"""Per-user instance lock and plain loopback address discovery; no login."""
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


class LauncherInstance:
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
        ensure_native_path(legacy, file_ok=True)
        _native_io_path(legacy).unlink(missing_ok=True)

    def close(self):
        try:
            if _read_record(self.path) == self.record:
                _native_io_path(self.path).unlink()
        except (OSError, ValueError, ValidationFailure):
            pass  # never remove an unknown replacement record

def _read_record(path: Path):
    ensure_native_path(path, file_ok=True)
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
