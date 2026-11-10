"""Concrete product checks installed in the bounded local-CLI integration fixture.

These are fixture product tests, not Harness tests. Each exported test identifies
one actual behavior used by subject-specific supplied evidence.
"""
PRODUCT_CHECKS = r'''from pathlib import Path
import contextlib
import io
import json
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from task_cli import add_task, complete_task, list_tasks


class LocalCliAcceptance(unittest.TestCase):
    def command(self, *args, cwd=None):
        return subprocess.run([sys.executable, str(Path(__file__).resolve().parents[1] / "task_cli.py"), *map(str, args)],
                              cwd=cwd, capture_output=True, text=True, timeout=10)

    def test_core_cli_contract(self):
        with tempfile.TemporaryDirectory() as temp:
            data = Path(temp) / 'tasks.json'
            first = self.command('--data', data, 'add', 'One')
            self.assertEqual((first.returncode, first.stdout.strip()), (0, 'Added 1: One'))
            self.assertEqual(self.command('--data', data, 'list').stdout.strip(), '[ ] 1: One')
            self.assertEqual(self.command('--data', data, 'done', '1').stdout.strip(), 'Completed 1: One')
            self.assertEqual(self.command('--data', data, 'list').stdout.strip(), '[x] 1: One')

    def test_real_persistence_and_configuration(self):
        with tempfile.TemporaryDirectory() as temp:
            a, b = Path(temp) / 'a.json', Path(temp) / 'b.json'
            self.assertEqual(self.command('--data', a, 'add', 'Persistent').returncode, 0)
            self.assertEqual(self.command('--data', b, 'list').stdout, '')
            self.assertIn('Persistent', self.command('--data', a, 'list').stdout)
            self.assertEqual(json.loads(a.read_text())[0]['title'], 'Persistent')
            self.assertFalse(a.with_suffix('.json.tmp').exists())

    def test_errors_edge_cases_and_operator_alert(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'tasks.json'
            add_task(path, 'Keep')
            before = path.read_bytes()
            missing = self.command('--data', path, 'done', '999')
            self.assertNotEqual(missing.returncode, 0)
            self.assertIn('Unknown task id', missing.stderr)
            self.assertEqual(path.read_bytes(), before)
            path.write_text('invalid JSON')
            corrupt = self.command('--data', path, 'list')
            self.assertNotEqual(corrupt.returncode, 0)
            self.assertIn('JSONDecodeError', corrupt.stderr)
            self.assertEqual(path.read_text(), 'invalid JSON')

    def test_backup_restore_rollback_and_data_lifecycle(self):
        with tempfile.TemporaryDirectory() as temp:
            path, backup = Path(temp) / 'tasks.json', Path(temp) / 'backup.json'
            add_task(path, 'Recover')
            shutil.copyfile(path, backup)
            complete_task(path, 1)
            self.assertTrue(list_tasks(path)[0]['done'])
            shutil.copyfile(backup, path)
            self.assertFalse(list_tasks(path)[0]['done'])
            self.assertEqual(path.read_bytes(), backup.read_bytes())
            path.unlink()
            self.assertEqual(list_tasks(path), [])

    def test_schema_v1_compatibility(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'tasks.json'
            original = [{'id': 7, 'title': 'v1 baseline', 'done': False}]
            path.write_text(json.dumps(original))
            self.assertEqual(list_tasks(path), original)
            self.assertEqual(add_task(path, 'Current')['id'], 8)
            self.assertEqual(set(list_tasks(path)[0]), {'id', 'title', 'done'})

    def test_reproducible_local_install(self):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(__file__).resolve().parents[1] / 'task_cli.py'
            destination = Path(temp) / source.name
            shutil.copyfile(source, destination)
            self.assertEqual(source.read_bytes(), destination.read_bytes())
            run = subprocess.run([sys.executable, 'task_cli.py', '--data', 'tasks.json', 'add', 'Installed'],
                                 cwd=temp, capture_output=True, text=True, timeout=10)
            self.assertEqual(run.returncode, 0, run.stderr)
            self.assertEqual(json.loads((Path(temp) / 'tasks.json').read_text())[0]['title'], 'Installed')

    def test_local_security_boundary(self):
        import ast
        source = Path(__file__).resolve().parents[1] / 'task_cli.py'
        tree = ast.parse(source.read_text())
        modules = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                modules.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                modules.add(node.module)
        self.assertLessEqual(modules, {'__future__', 'argparse', 'json', 'pathlib', 'typing'})
        self.assertNotIn('socket', modules)
        self.assertNotIn('subprocess', modules)
        self.assertNotIn('API_KEY=', source.read_text())
        self.assertNotIn('PASSWORD=', source.read_text())

    def test_bounded_performance_baseline(self):
        with tempfile.TemporaryDirectory() as temp:
            data = Path(temp) / 'tasks.json'
            started = time.perf_counter()
            for index in range(100):
                add_task(data, f'Item {index}')
            self.assertEqual(len(list_tasks(data)), 100)
            elapsed = time.perf_counter() - started
            print(f'100 sequential local inserts: {elapsed:.6f}s; fixture budget 10s')
            self.assertLess(elapsed, 10.0)

    def test_declared_release_regression(self):
        # Explicit core product regression only; never recursively discovers
        # Harness's own test suite or this enclosing test.
        import test_task_cli
        result = unittest.TextTestRunner(stream=io.StringIO()).run(unittest.TestLoader().loadTestsFromModule(test_task_cli))
        self.assertEqual(result.testsRun, 2)
        self.assertTrue(result.wasSuccessful())
'''


def install_checks(root):
    (root / 'tests/test_phf06_product.py').write_text(PRODUCT_CHECKS, encoding='utf8')
