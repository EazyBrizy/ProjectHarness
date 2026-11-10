from __future__ import annotations

from copy import deepcopy
import json
import os
from pathlib import Path
import tempfile
import unittest
import zipfile

from project_harness.compiler import prepare_handoff
from project_harness.errors import HarnessError, SafetyViolation, ValidationFailure, WaitingDecision, WaitingInput
from project_harness.hashing import sha256_file, tree_hash, tree_entries
from project_harness.intake import check_intake, start_intake
from project_harness.resources import distribution_root
from project_harness.runtime import (
    block_current,
    complete_current,
    next_task,
    project_status,
    resume_blocked,
    verify_current,
)
from project_harness.serialization import load_data, write_data
from project_harness.validation import doctor, validate_handoff, validate_project_directory


ROOT = distribution_root()
FIXTURE = ROOT / "fixtures/demo_project_input.json"


def load_fixture() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def add_brownfield_approval(data: dict, *, actor: str = "ACT-BROWNFIELD-APPROVER-001") -> None:
    data.setdefault("implementation", {})["claimed_current_level"] = "UNKNOWN"
    approvals = data.setdefault("approvals", {})
    approvals["brownfield_baseline"] = {
        "approved": True,
        "actor": actor,
        "approved_at": "2026-08-17T08:05:00Z",
        "notes": "Explicit Brownfield Baseline approval",
    }


def file_tree_digest(root: Path) -> str:
    return tree_hash(root, tree_entries(root))


def prepare_demo(base: Path, *, data: dict | None = None, repository: Path | None = None) -> tuple[Path, Path, Path]:
    data = deepcopy(data or load_fixture())
    input_path = base / "input.json"
    input_path.parent.mkdir(parents=True, exist_ok=True)
    input_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    workspace = base / "intake"
    mode = data["project"]["mode"]
    start_intake(
        workspace,
        project_name=data["project"]["name"],
        mode=mode,
        repository=repository,
        initial_input=input_path,
        force=True,
    )
    output = base / "handoff.zip"
    extracted = base / "handoff"
    result = prepare_handoff(workspace, output, keep_directory=extracted)
    if result["status"] != "READY_FOR_CODEX":
        raise AssertionError(result)
    return workspace, output, extracted


def implement_first_task(root: Path) -> None:
    (root / "task_cli.py").write_text(
        """from __future__ import annotations
import argparse
import json
from pathlib import Path
from typing import Any


def load_tasks(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding=\"utf-8\"))


def save_tasks(path: Path, tasks: list[dict[str, Any]]) -> None:
    temp = path.with_suffix(path.suffix + \".tmp\")
    temp.write_text(json.dumps(tasks, ensure_ascii=False, indent=2) + \"\\n\", encoding=\"utf-8\")
    temp.replace(path)


def add_task(path: Path, title: str) -> dict[str, Any]:
    tasks = load_tasks(path)
    task = {\"id\": max((item[\"id\"] for item in tasks), default=0) + 1, \"title\": title, \"done\": False}
    tasks.append(task)
    save_tasks(path, tasks)
    return task


def list_tasks(path: Path) -> list[dict[str, Any]]:
    return load_tasks(path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(\"--data\", type=Path, default=Path(\"tasks.json\"))
    sub = parser.add_subparsers(dest=\"command\", required=True)
    add = sub.add_parser(\"add\")
    add.add_argument(\"title\")
    sub.add_parser(\"list\")
    args = parser.parse_args()
    if args.command == \"add\":
        task = add_task(args.data, args.title)
        print(f\"Added {task['id']}: {task['title']}\")
    else:
        for task in list_tasks(args.data):
            print(f\"[ ] {task['id']}: {task['title']}\")
    return 0


if __name__ == \"__main__\":
    raise SystemExit(main())
""",
        encoding="utf-8",
    )
    tests = root / "tests"
    tests.mkdir(exist_ok=True)
    (tests / "test_task_cli.py").write_text(
        """from pathlib import Path
import tempfile
import unittest
from task_cli import add_task, list_tasks


class TaskCliTests(unittest.TestCase):
    def test_add_and_list(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / \"tasks.json\"
            first = add_task(path, \"One\")
            second = add_task(path, \"Two\")
            self.assertEqual((first[\"id\"], second[\"id\"]), (1, 2))
            self.assertEqual([item[\"title\"] for item in list_tasks(path)], [\"One\", \"Two\"])
            self.assertFalse(first[\"done\"])
""",
        encoding="utf-8",
    )
    with (root / "README.md").open("a", encoding="utf-8") as fh:
        fh.write("\n## Usage\n\n`python task_cli.py add \\\"Example\\\"` and `python task_cli.py list`.\n")


def implement_second_task(root: Path) -> None:
    path = root / "task_cli.py"
    text = path.read_text(encoding="utf-8")
    text = text.replace(
        "def main() -> int:\n",
        """def complete_task(path: Path, task_id: int) -> dict[str, Any]:
    tasks = load_tasks(path)
    for task in tasks:
        if task[\"id\"] == task_id:
            task[\"done\"] = True
            save_tasks(path, tasks)
            return task
    raise ValueError(f\"Unknown task id: {task_id}\")


def main() -> int:
""",
    )
    text = text.replace(
        '    sub.add_parser("list")\n    args = parser.parse_args()\n',
        '    sub.add_parser("list")\n    done = sub.add_parser("done")\n    done.add_argument("task_id", type=int)\n    args = parser.parse_args()\n',
    )
    text = text.replace(
        """    else:
        for task in list_tasks(args.data):
            print(f\"[ ] {task['id']}: {task['title']}\")
""",
        """    elif args.command == \"done\":
        task = complete_task(args.data, args.task_id)
        print(f\"Completed {task['id']}: {task['title']}\")
    else:
        for task in list_tasks(args.data):
            marker = \"x\" if task.get(\"done\") else \" \"
            print(f\"[{marker}] {task['id']}: {task['title']}\")
""",
    )
    path.write_text(text, encoding="utf-8")
    test_path = root / "tests/test_task_cli.py"
    tests = test_path.read_text(encoding="utf-8").replace(
        "from task_cli import add_task, list_tasks",
        "from task_cli import add_task, complete_task, list_tasks",
    )
    tests += """
    def test_complete_and_unknown_id(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / \"tasks.json\"
            task = add_task(path, \"Finish\")
            self.assertTrue(complete_task(path, task[\"id\"])[\"done\"])
            self.assertTrue(list_tasks(path)[0][\"done\"])
            with self.assertRaisesRegex(ValueError, \"Unknown task id\"):
                complete_task(path, 999)
"""
    test_path.write_text(tests, encoding="utf-8")
    with (root / "README.md").open("a", encoding="utf-8") as fh:
        fh.write("\n`python task_cli.py done 1` marks a task complete.\n")


def write_agent_result(root: Path, verification: dict, summary: str = "Implemented current task") -> Path:
    state = load_data(root / ".harness/state/CURRENT_STATE.yaml")["state"]
    active = state["active_run"]
    result = {
        "schema_version": 1,
        "task_ref": active["task_ref"],
        "run_ref": active["run_ref"],
        "status": "COMPLETED",
        "summary": summary,
        "changes": verification["diff"],
        "commands": verification["commands"],
        "tests": [{"name": "declared verification", "status": "PASS"}],
        "evidence": [verification["report_ref"]],
        "blockers": [],
        "notes": [],
    }
    path = root / ".harness/runtime/AGENT_RESULTS" / f"{active['run_ref']}.json"
    write_data(path, result)
    return path


class ProjectHarnessTests(unittest.TestCase):
    def test_01_doctor_passes(self) -> None:
        result = doctor(ROOT, check_manifest=False)
        self.assertEqual(result["status"], "PASS")
        versions = result["checks"][0]["details"]
        self.assertEqual(versions, {
            "id_prefixes": 3,
            "project_profiles": 1,
            "statuses": 6,
            "request_routing": 2,
            "capabilities": 1,
            "contracts": 6,
            "implementation_levels": 1,
        })

    def test_02_start_intake_is_external_and_waits_for_input(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            repo = base / "repo"
            repo.mkdir()
            (repo / "README.md").write_text("existing\n", encoding="utf-8")
            before = file_tree_digest(repo)
            workspace = base / "control" / "intake"
            result = start_intake(workspace, project_name="Existing", mode="BROWNFIELD", repository=repo)
            self.assertEqual(result["status"], "WAITING_INPUT")
            self.assertEqual(file_tree_digest(repo), before)
            self.assertFalse((repo / ".harness").exists())
            questions = (workspace / "QUESTIONS.md").read_text(encoding="utf-8")
            self.assertLess(questions.index("QST-DOCUMENTATION-001"), questions.index("QST-OUTCOME-001"))

    def test_03_complete_answers_still_require_explicit_approvals(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            data = load_fixture()
            for item in data["approvals"].values():
                item.update({"approved": False, "actor": None, "approved_at": None})
            input_path = base / "input.json"
            write_data(input_path, data)
            workspace = base / "intake"
            result = start_intake(workspace, project_name=data["project"]["name"], mode="GREENFIELD", initial_input=input_path)
            self.assertEqual(result["status"], "WAITING_DECISION")
            with self.assertRaises(WaitingDecision):
                prepare_handoff(workspace, base / "handoff.zip")

    def test_04_greenfield_handoff_is_valid_and_jit(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            _, archive, root = prepare_demo(Path(temp))
            directory_result = validate_handoff(root)
            archive_result = validate_handoff(archive)
            self.assertEqual(directory_result["status"], "PASS")
            self.assertEqual(archive_result["status"], "PASS")
            bundles = list((root / ".harness/prompts/BUNDLES_BY_RUN").glob("CPB-*.yaml"))
            tasks = load_data(root / ".harness/tasks/INDEX.yaml")["task_index"]["order"]
            self.assertEqual(len(tasks), 2)
            self.assertEqual(len(bundles), 1)
            lock = load_data(root / ".harness/config/PROJECT_LOCK.yaml")["project_lock"]
            self.assertEqual(set(lock["registry_versions"]), {
                "id_prefixes", "project_profiles", "statuses", "request_routing", "capabilities", "contracts",
                "implementation_levels"
            })

    def test_05_manifest_detects_tampering(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            _, _, root = prepare_demo(Path(temp))
            (root / "PROJECT.md").write_text("tampered\n", encoding="utf-8")
            result = validate_handoff(root)
            self.assertEqual(result["status"], "FAIL")
            manifest_check = next(item for item in result["checks"] if item["name"] == "Handoff manifest")
            self.assertIn("PROJECT.md", manifest_check["details"]["mismatched"])

    def test_06_brownfield_intake_and_prepare_do_not_modify_source(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            repo = base / "repo"
            repo.mkdir()
            (repo / "README.md").write_text("# Existing\n", encoding="utf-8")
            (repo / "app.py").write_text("def hello():\n    return 'hello'\n", encoding="utf-8")
            (repo / "test_app.py").write_text("from app import hello\n\ndef test_value(): assert hello() == 'hello'\n", encoding="utf-8")
            before = file_tree_digest(repo)
            data = load_fixture()
            data["project"]["name"] = "Existing Demo"
            data["project"]["slug"] = "existing-demo"
            data["project"]["mode"] = "BROWNFIELD"
            data["brownfield"]["baseline_summary"] = "Small existing Python module with a README and one test."
            add_brownfield_approval(data)
            _, archive, root = prepare_demo(base / "run", data=data, repository=repo)
            self.assertEqual(file_tree_digest(repo), before)
            self.assertFalse((repo / ".harness").exists())
            self.assertEqual(validate_handoff(archive)["status"], "PASS")
            portfolio = load_data(root / ".harness/work-packages/ROUTE_PORTFOLIO/INDEX.yaml")["brownfield_route_portfolio"]
            routes = []
            for ref in portfolio["route_refs"]:
                rid = ref.split("@")[0]
                routes.append(load_data(root / f".harness/work-packages/ROUTE_PORTFOLIO/{rid}@1.yaml")["brownfield_route_item"]["route"])
            self.assertEqual(set(routes), {"CONTINUE_DEVELOPMENT", "FIX_KNOWN_BUGS", "IMPROVE_PROJECT", "STABILIZE_BASELINE"})

    def test_07_next_is_idempotent_until_state_changes(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            _, _, root = prepare_demo(Path(temp))
            first = next_task(root)
            second = next_task(root)
            self.assertTrue(first["idempotent"])
            self.assertTrue(second["idempotent"])
            self.assertEqual(first["run_ref"], second["run_ref"])
            self.assertEqual(first["prompt_bundle_path"], second["prompt_bundle_path"])

    def test_08_scope_violation_fails_independent_verification(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            _, _, root = prepare_demo(Path(temp))
            (root / "ARCHITECTURE.md").write_text("unauthorized\n", encoding="utf-8")
            result = verify_current(root, allow_command_execution=False)
            self.assertEqual(result["status"], "BLOCKED")
            self.assertEqual(result["reason"], "SAFETY_VIOLATION")
            self.assertEqual(result["commands"], [])
            self.assertIn("ARCHITECTURE.md", result["control_plane"]["changed"])
            state = load_data(root / ".harness/state/CURRENT_STATE.yaml")["state"]
            self.assertEqual(state["project_status"], "BLOCKED")
            self.assertEqual(
                state["next_route"],
                "RESTORE_CONTROL_PLANE_FROM_TRUSTED_HANDOFF_OR_RESTART_RUN",
            )

    def test_09_agent_declared_diff_must_match_observed_diff(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            _, _, root = prepare_demo(Path(temp))
            implement_first_task(root)
            verification = verify_current(root, allow_command_execution=True)
            self.assertEqual(verification["status"], "PASS")
            result_path = write_agent_result(root, verification)
            result = load_data(result_path)
            result["changes"]["added"] = []
            write_data(result_path, result)
            with self.assertRaises(ValidationFailure):
                complete_current(root, result_path)

    def test_10_full_two_task_execution_reaches_stage_gate_and_jit_compiles_second(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            _, _, root = prepare_demo(Path(temp))
            implement_first_task(root)
            verify1 = verify_current(root, allow_command_execution=True)
            complete1 = complete_current(root, write_agent_result(root, verify1, "Implemented add/list"))
            self.assertEqual(complete1["project_status"], "ACTIVE")
            task_index = load_data(root / ".harness/tasks/INDEX.yaml")["task_index"]
            task1 = load_data(root / task_index["current"]["TSK-HARNESS-DEMO-TASK-CLI-001"])["task"]
            run1 = load_data(root / ".harness/runtime/RUNS/RUN-HARNESS-DEMO-TASK-CLI-001-A1.yaml")["run"]
            report1 = load_data(root / ".harness/reports/TRP-HARNESS-DEMO-TASK-CLI-001-A1.yaml")["task_report"]
            self.assertEqual(task1["status"], "DONE")
            self.assertEqual(run1["status"], "SUCCEEDED")
            self.assertEqual(report1["status"], "COMPLETED")
            bundles = list((root / ".harness/prompts/BUNDLES_BY_RUN").glob("CPB-*.yaml"))
            self.assertEqual(len(bundles), 2)
            self.assertIn("next", complete1)
            implement_second_task(root)
            verify2 = verify_current(root, allow_command_execution=True)
            self.assertEqual(verify2["status"], "PASS")
            complete2 = complete_current(root, write_agent_result(root, verify2, "Implemented done"))
            self.assertEqual(complete2["project_status"], "ACTIVE")
            self.assertEqual(complete2["stage_gate"]["status"], "STAGE_ACCEPTANCE_PREPARATION")
            self.assertEqual(complete2["next"]["status"], "READY_FOR_CODEX")
            verify3 = verify_current(root, allow_command_execution=True)
            self.assertEqual(verify3["status"], "PASS")
            complete3 = complete_current(root, write_agent_result(root, verify3, "Prepared final Stage Gate evidence"))
            self.assertEqual(complete3["stage_gate"]["status"], "BLOCKED")
            # PH-F02: only separately checked and pinned subject proofs can
            # close Gate preparation; no automatic PASS from the common run.
            from project_harness.stage_gate_lifecycle import resume_stage_gate
            from tests.gate_proof_fixtures import all_gate_subjects
            all_gate_subjects(root)
            self.assertEqual(resume_stage_gate(root)["status"], "VERIFYING")
            status = project_status(root)
            self.assertEqual(status["status"], "ACTIVE")
            self.assertEqual(status["implementation"]["active_stage"], "PROTOTYPE")
            self.assertEqual(next_task(root)["status"], "STAGE_GATE_PENDING")
            stage_state = load_data(root / ".harness/stages/STAGE_STATE.yaml")["implementation"]
            self.assertEqual(stage_state["highest_accepted_level"], "NONE")
            self.assertEqual(stage_state["active_stage"], "PROTOTYPE")
            self.assertEqual(validate_project_directory(root)["status"], "PASS")

    def test_11_block_resume_preserves_history_and_uses_new_attempt(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            _, _, root = prepare_demo(Path(temp))
            blocked1 = block_current(root, "Need a decision", options=["Provide decision"])
            self.assertEqual(blocked1["blocker_ref"].split("-")[-1], "001")
            self.assertEqual(validate_project_directory(root)["status"], "PASS")
            resumed1 = resume_blocked(root, resolution="Decision supplied")
            self.assertEqual(resumed1["next"]["run_ref"].split("-")[-1], "A2")
            blocked2 = block_current(root, "Second material blocker")
            self.assertTrue(blocked2["blocker_ref"].endswith("-002"))
            resolved = list((root / ".harness/blockers").glob("*@2.yaml"))
            self.assertEqual(len(resolved), 1)

    def test_12_zip_traversal_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            archive = Path(temp) / "unsafe.zip"
            with zipfile.ZipFile(archive, "w") as zf:
                zf.writestr("../escape.txt", "bad")
            with self.assertRaises(SafetyViolation):
                validate_handoff(archive)

    def test_13_normal_brownfield_zip_is_accepted_and_remains_immutable(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            source = base / "source"
            source.mkdir()
            (source / "README.md").write_text("# Existing ZIP\n", encoding="utf-8")
            (source / "app.py").write_text("def value(): return 1\n", encoding="utf-8")
            archive = base / "repository.zip"
            with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zf:
                for path in sorted(source.rglob("*")):
                    if path.is_file():
                        zf.write(path, f"repository/{path.relative_to(source).as_posix()}")
            before = sha256_file(archive)
            data = load_fixture()
            data["project"].update({"name": "ZIP Existing", "slug": "zip-existing", "mode": "BROWNFIELD"})
            data["brownfield"]["baseline_summary"] = "Small Python repository supplied as a ZIP archive."
            add_brownfield_approval(data)
            _, handoff_zip, handoff = prepare_demo(base / "run", data=data, repository=archive)
            self.assertEqual(sha256_file(archive), before)
            self.assertEqual(validate_handoff(handoff_zip)["status"], "PASS")
            self.assertTrue((handoff / "app.py").exists())
            self.assertFalse((source / ".harness").exists())

    def test_14_provider_accounting_fields_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            data = load_fixture()
            data["provider_billing"] = {"account": "forbidden"}
            path = Path(temp) / "input.json"
            write_data(path, data)
            workspace = Path(temp) / "intake"
            result = start_intake(workspace, project_name=data["project"]["name"], mode="GREENFIELD", initial_input=path)
            self.assertEqual(result["status"], "INVALID")
            self.assertTrue(any("Forbidden provider accounting field" in item for item in result["readiness"]["errors"]))


if __name__ == "__main__":
    unittest.main()
