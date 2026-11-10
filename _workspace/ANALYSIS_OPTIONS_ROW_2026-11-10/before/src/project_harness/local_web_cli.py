"""Reusable native Codex CLI connection and bounded owned-process transport.

Only fixed callers use invoke(); HTTP never accepts executable paths or argv.
This is a document-analysis connection, not the product Task executor.
"""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import threading
import time

from .errors import HarnessError, ValidationFailure
from .platform_fs import ensure_native_path, _native_io_path
from .serialization import write_data

OUTPUT_LIMIT = 2 * 1024 * 1024
STDERR_LIMIT = 512 * 1024
CREATE_HIDDEN = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0


class CliError(ValidationFailure):
    def __init__(self, code: str, message: str, status: int = 400):
        super().__init__(message)
        self.cli_code, self.http_status = code, status

    def public(self):
        return {'code': self.cli_code, 'message_ru': self.message,
                'next_action_ru': 'Проверьте подключение CLI или используйте ручной пакет.'}


def checked_file(path: Path, maximum: int) -> bytes:
    ensure_native_path(path, file_ok=True)
    io = _native_io_path(path)
    if not io.exists():
        raise FileNotFoundError(path)
    if not io.is_file() or io.stat().st_size > maximum or io.stat().st_nlink != 1:
        raise CliError('CLI_FILE_INVALID', 'Локальные данные CLI отсутствуют или повреждены.')
    with io.open('rb') as stream:
        data = stream.read(maximum + 1)
    if len(data) > maximum:
        raise CliError('CLI_FILE_TOO_LARGE', 'Результат CLI превышает допустимый размер.')
    return data


def executable_digest(path: Path):
    ensure_native_path(path, file_ok=True)
    if path.name.lower() != 'codex.exe' or not _native_io_path(path).is_file():
        raise CliError('CLI_NOT_FOUND', 'Codex CLI не найден. Установите его на этом компьютере.', 503)
    digest = hashlib.sha256()
    with _native_io_path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def find_cli() -> Path:
    if os.name != 'nt':
        raise CliError('CLI_PLATFORM_UNSUPPORTED', 'Подключение CLI поддерживается в Windows.', 503)
    local = Path(os.environ.get('LOCALAPPDATA', ''))
    candidates = [local/'Programs/OpenAI/Codex/bin/codex.exe',
                  Path.home()/'.local/bin/codex.exe']
    # No implicit current-directory search and no .cmd/.bat/shell wrappers.
    safe_path = os.pathsep.join(p for p in os.environ.get('PATH', '').split(os.pathsep)
                               if p and Path(p).is_absolute())
    found = shutil.which('codex.exe', path=safe_path)
    if found:
        candidates.append(Path(found))
    for path in candidates:
        try:
            # The official installer uses a versioned launcher junction. Only
            # trusted OS-discovered executable candidates are resolved here;
            # project/upload paths still use the strict no-reparse policy.
            path = path.resolve(strict=True)
            executable_digest(path)
            return path.absolute()
        except (OSError, HarnessError):
            continue
    raise CliError('CLI_NOT_FOUND', 'Codex CLI не найден. Установите его на этом компьютере, затем нажмите «Подключить CLI».', 503)


def _stop_owned(process):
    if process.poll() is not None:
        return
    if os.name == 'nt':
        subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                       creationflags=CREATE_HIDDEN, timeout=8, check=False)
    else:
        process.kill()
    process.wait(timeout=10)


def invoke(argv: list[str], *, cwd: Path, stdin: bytes = b'', timeout: float = 15,
           cancel: threading.Event | None = None):
    """Bounded binary transport. Callers supply trusted fixed argv, never HTTP data."""
    ensure_native_path(cwd)
    cancel = cancel or threading.Event()
    if cancel.is_set():
        raise CliError('CLI_CANCELLED', 'Анализ остановлен.')
    env = dict(os.environ)
    for key in ('PROJECT_HARNESS_HOME', 'PYTHONPATH', 'PYTHONHOME', 'BASH_ENV', 'ENV',
                'OPENAI_API_KEY', 'CODEX_API_KEY', 'OPENAI_BASE_URL'):
        env.pop(key, None)
    try:
        process = subprocess.Popen(argv, cwd=_native_io_path(cwd), env=env,
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            shell=False, creationflags=CREATE_HIDDEN)
    except OSError as exc:
        raise CliError('CLI_START_FAILED', 'Не удалось запустить установленный Codex CLI.', 503) from exc
    buffers = [bytearray(), bytearray()]
    overflow = threading.Event()

    def read(stream, index, limit):
        try:
            while chunk := stream.read(16384):
                if len(buffers[index]) + len(chunk) > limit:
                    overflow.set()
                    return
                buffers[index].extend(chunk)
        finally:
            stream.close()

    def send():
        try:
            process.stdin.write(stdin)
            process.stdin.close()
        except (BrokenPipeError, OSError, ValueError):
            pass
        finally:
            try:
                process.stdin.close()
            except (OSError, ValueError):
                pass

    threads = [threading.Thread(target=read, args=(process.stdout, 0, OUTPUT_LIMIT), daemon=True),
               threading.Thread(target=read, args=(process.stderr, 1, STDERR_LIMIT), daemon=True),
               threading.Thread(target=send, daemon=True)]
    for thread in threads:
        thread.start()
    deadline = time.monotonic() + timeout
    try:
        while process.poll() is None:
            if cancel.is_set():
                raise CliError('CLI_CANCELLED', 'Анализ остановлен.')
            if overflow.is_set():
                raise CliError('CLI_OUTPUT_TOO_LARGE', 'Codex CLI вернул слишком большой ответ.')
            if time.monotonic() >= deadline:
                raise CliError('CLI_TIMEOUT', 'Анализ занял слишком много времени. Можно повторить его или использовать ручной пакет.')
            cancel.wait(.05)
        for thread in threads:
            thread.join(2)
        if overflow.is_set():
            raise CliError('CLI_OUTPUT_TOO_LARGE', 'Codex CLI вернул слишком большой ответ.')
        return process.returncode, bytes(buffers[0]), bytes(buffers[1])
    finally:
        _stop_owned(process)
        for thread in threads:
            thread.join(2)


class CliConnection:
    def __init__(self, app_data: Path):
        self.base = app_data
        self.path = app_data/'codex-cli-connection.json'
        self.lock = threading.Lock()

    def _record(self):
        try:
            value = json.loads(checked_file(self.path, 4096))
        except FileNotFoundError:
            return None
        except (ValueError, OSError, ValidationFailure) as exc:
            raise CliError('CLI_CONNECTION_INVALID', 'Настройки подключения CLI повреждены. Подключите CLI заново.', 409) from exc
        if (not isinstance(value, dict) or set(value) != {'version', 'executable', 'sha256', 'cli_version'}
            or type(value['version']) is not int or value['version'] != 1
            or not all(isinstance(value[k], str) for k in ('executable', 'sha256', 'cli_version'))
            or not re.fullmatch('[a-f0-9]{64}', value['sha256']) or not Path(value['executable']).is_absolute()
            or len(value['executable']) > 4096 or len(value['cli_version']) > 120):
            raise CliError('CLI_CONNECTION_INVALID', 'Настройки подключения CLI повреждены. Подключите CLI заново.', 409)
        return value

    def status(self):
        """Only persisted nonsecret state; never starts a process from GET."""
        record = self._record()
        return {'connected': bool(record), 'version': record['cli_version'] if record else None,
                'message_ru': 'Codex CLI подключён.' if record else 'Codex CLI пока не подключён.'}

    def connect(self):
        with self.lock:
            ensure_native_path(self.path, file_ok=True)
            _native_io_path(self.path).unlink(missing_ok=True)
            executable = find_cli()
            fingerprint = executable_digest(executable)
            code, version, _ = invoke([str(executable), '--version'], cwd=self.base)
            text = version.decode('utf-8', 'replace').strip()
            if code or not text.startswith('codex-cli ') or len(text) > 120:
                raise CliError('CLI_VERSION_UNSUPPORTED', 'Найденная программа не распознана как Codex CLI.', 503)
            code, help_text, _ = invoke([str(executable), 'exec', '--help'], cwd=self.base)
            if code or any(flag not in help_text for flag in (b'--ignore-user-config', b'--ephemeral', b'--output-schema', b'--output-last-message')):
                raise CliError('CLI_VERSION_UNSUPPORTED', 'Обновите Codex CLI: эта версия не поддерживает анализ из приложения.', 503)
            code, auth, err = invoke([str(executable), 'login', 'status'], cwd=self.base)
            if code or b'logged in' not in (auth + err).lower():
                raise CliError('CLI_LOGIN_REQUIRED', 'Выполните вход в Codex CLI командой «codex login», затем подключите его снова.', 409)
            if executable_digest(executable) != fingerprint:
                raise CliError('CLI_EXECUTABLE_CHANGED', 'Codex CLI обновился во время подключения. Повторите подключение.', 409)
            write_data(self.path, {'version': 1, 'executable': str(executable), 'sha256': fingerprint, 'cli_version': text})
            return self.status()

    def require_ready(self) -> Path:
        record = self._record()
        if not record:
            raise CliError('CLI_NOT_CONNECTED', 'Сначала нажмите «Подключить CLI».', 409)
        executable = Path(record['executable'])
        if executable_digest(executable) != record['sha256']:
            raise CliError('CLI_EXECUTABLE_CHANGED', 'Codex CLI обновился. Нажмите «Подключить CLI», чтобы обновить подключение.', 409)
        return executable


def analysis_argv(executable: Path, directory: Path, schema: Path, answer: Path):
    return [str(executable), '-c', 'approval_policy="never"', '--disable', 'shell_tool',
            '--disable', 'view_image', '--disable', 'apps', '--disable', 'multi_agent',
            '--disable', 'plugins', '--disable', 'remote_plugin', '--disable', 'skill_search',
            '--disable', 'skill_mcp_dependency_install', '--disable', 'shell_snapshot',
            '-c', 'web_search="disabled"', '-c', 'project_doc_max_bytes=0', 'exec', '--ignore-user-config', '--ignore-rules',
            '--ephemeral', '--sandbox', 'read-only', '--skip-git-repo-check',
            '--cd', str(directory), '--output-schema', str(schema),
            '--output-last-message', str(answer), '--color', 'never', '--json', '-']
