#!/usr/bin/env python3
"""PH-F02 acceptance suite: existing tests + PH-F02, excluding PH-F03-only RED.

Does not suppress any failure in a required test. The three known-red
future-stage planner cases are enumerated by their exact test IDs.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

DEFERRED_PH_F03 = {
    "test_ph_f01_planner_regression.PHF01FixtureAndPlannerTests.test_ph_f03_accept_prototype_to_first_alpha_ready_jit",
    "test_ph_f01_planner_regression.PHF01FixtureAndPlannerTests.test_ph_f03_level_up_mvp_to_first_release_ready_jit",
    "test_ph_f01_planner_regression.PHF01FixtureAndPlannerTests.test_ph_f03_route_is_actionable_in_public_status_api",
}


def select_suite(suite: unittest.TestSuite) -> tuple[unittest.TestSuite, set[str]]:
    excluded: set[str] = set()
    result = unittest.TestSuite()
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            selected, ignored = select_suite(item)
            result.addTests(selected)
            excluded |= ignored
        elif item.id() in DEFERRED_PH_F03:
            excluded.add(item.id())
        else:
            result.addTest(item)
    return result, excluded


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--list", action="store_true", help="Print exact suite sizes and excluded PH-F03 cases without running tests")
    args = parser.parse_args()
    discovered = unittest.defaultTestLoader.discover(str(ROOT / "tests"), pattern="test_*.py")
    selected, excluded = select_suite(discovered)
    if excluded != DEFERRED_PH_F03:
        print("Unexpected PH-F03 exclusion set; refusing misleading PH-F02 PASS", file=sys.stderr)
        print(json.dumps({"expected": sorted(DEFERRED_PH_F03), "actual": sorted(excluded)}, indent=2), file=sys.stderr)
        return 2
    if args.list:
        print(json.dumps({"acceptance": "PH-F02", "included_tests": selected.countTestCases(), "excluded_future_ph_f03": sorted(excluded)}, indent=2))
        return 0
    print(f"PH-F02 acceptance: {selected.countTestCases()} cases; exactly {len(excluded)} deferred PH-F03 cases", file=sys.stderr)
    outcome = unittest.TextTestRunner(verbosity=2).run(selected)
    return 0 if outcome.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
