#!/usr/bin/env bash
set -u
cd "$(dirname "$0")/.."
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH="src:.:tests"
run() {
  local name="$1"; shift
  timeout 240s python -m unittest -v "$@" > "PH_051_03_LOGS/REGRESSION_${name}.log" 2>&1
  local rc=$?
  echo "$name $rc" | tee -a PH_051_03_LOGS/REGRESSION_GROUP_SUMMARY.txt
}
run 02 tests.test_engine tests.test_gate_evidence_contract
run 03 tests.test_ph_f06_maturity_lifecycle tests.test_canonical_target tests.test_ph_051_01_contract_baseline
run 04 tests.test_ph_f05_intake_acceptance tests.test_assessment_freshness tests.test_exact_assessment_ref tests.test_contract_hardening
run 05 tests.test_ph_f03_active_stage_planning tests.test_implementation_levels tests.test_ph_f01_planner_regression
run 06 tests.test_ph_f04_runtime_reachability tests.test_stage_transaction_recovery tests.test_stage_approval_preparation
run 07 tests.test_ph_f02_semantic_proof_contract tests.test_stage_gate_preparation_block_recovery tests.test_ph_f01_gate_semantics_regression
