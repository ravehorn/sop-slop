#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "$0")/.." && pwd)"

python3 "$repo_root/sop-slop/scripts/validate_workflow_graph.py" --self-test
python3 "$repo_root/sop-slop/scripts/validate_run_replay.py" --scenario forward_test --require-closure
python3 "$repo_root/sop-slop/scripts/validate_run_replay.py" \
  "$repo_root/sop-slop/references/deliberation-forward-test-fixture-0.5.0.json" \
  --scenario forward_test --require-closure --self-test

grep -q '^name: sop-slop$' "$repo_root/sop-slop/SKILL.md"
grep -q 'display_name: "SOP SLOP"' "$repo_root/sop-slop/agents/openai.yaml"

"$repo_root/tests/install-test.sh"

echo "PACKAGE VALID"
