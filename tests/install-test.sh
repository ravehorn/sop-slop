#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "$0")/.." && pwd)"
test_root="$(mktemp -d "${TMPDIR:-/tmp}/sop-slop-install-test.XXXXXX")"
trap 'rm -rf "$test_root"' EXIT

default_output="$(GSTACK_DIR="$test_root/new-gstack" SOP_SLOP_SOURCE=ravehorn/sop-slop "$repo_root/install.sh" --dry-run)"
for expected in setup-matt-pocock-skills wayfinder grill-me grill-with-docs to-spec to-tickets implement tdd code-review garrytan/gstack.git ravehorn/sop-slop '--host codex' --no-prefix; do
  grep -q -- "$expected" <<<"$default_output"
done

all_output="$(GSTACK_DIR="$test_root/all-gstack" "$repo_root/install.sh" --dry-run --all-matt)"
grep -Fq -- '--skill \*' <<<"$all_output"

mkdir -p "$test_root/not-git"
if GSTACK_DIR="$test_root/not-git" "$repo_root/install.sh" --dry-run >/dev/null 2>&1; then
  echo "Expected non-git gstack path to be rejected" >&2
  exit 1
fi

git init -q "$test_root/wrong-remote"
git -C "$test_root/wrong-remote" remote add origin https://example.com/not-gstack.git
if GSTACK_DIR="$test_root/wrong-remote" "$repo_root/install.sh" --dry-run >/dev/null 2>&1; then
  echo "Expected wrong gstack origin to be rejected" >&2
  exit 1
fi

git init -q "$test_root/official-remote"
git -C "$test_root/official-remote" remote add origin https://github.com/garrytan/gstack.git
rerun_output="$(GSTACK_DIR="$test_root/official-remote" "$repo_root/install.sh" --dry-run)"
grep -Fq 'pull --ff-only' <<<"$rerun_output"
grep -Fq -- '--host codex' <<<"$rerun_output"

fake_bin="$test_root/fake-bin"
mkdir -p "$fake_bin"
cat >"$fake_bin/bun" <<'EOF'
#!/usr/bin/env bash
exit 0
EOF
cat >"$fake_bin/npx" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
skills="$HOME/.codex/skills"
mkdir -p "$skills"
if [[ " $* " == *" mattpocock/skills "* ]]; then
  for name in setup-matt-pocock-skills wayfinder grill-me grill-with-docs to-spec to-tickets implement tdd code-review; do
    mkdir -p "$skills/$name"
    printf '%s\n' '---' "name: $name" 'description: test' '---' >"$skills/$name/SKILL.md"
  done
else
  mkdir -p "$skills/sop-slop"
  printf '%s\n' '---' 'name: sop-slop' 'description: test' '---' >"$skills/sop-slop/SKILL.md"
fi
EOF
cat >"$fake_bin/git" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
if [ "${1:-}" = "clone" ]; then
  destination="${!#}"
  mkdir -p "$destination/.git"
  cat >"$destination/setup" <<'SETUP'
#!/usr/bin/env bash
set -euo pipefail
skills="$HOME/.codex/skills"
mkdir -p "$skills"
for requirement in \
  gstack-office-hours:office-hours \
  gstack-plan-ceo-review:plan-ceo-review \
  gstack-plan-design-review:plan-design-review \
  gstack-plan-eng-review:plan-eng-review \
  gstack-review:review \
  gstack-qa:qa \
  gstack-ship:ship \
  gstack-land-and-deploy:land-and-deploy; do
  directory="${requirement%%:*}"
  name="${requirement#*:}"
  [ "${FAKE_GSTACK_COLLISION:-0}" = 1 ] && [ "$name" = qa ] && name=conflicting-qa
  mkdir -p "$skills/$directory"
  printf '%s\n' '---' "name: $name" 'description: test' '---' >"$skills/$directory/SKILL.md"
done
SETUP
  chmod +x "$destination/setup"
elif [ "${1:-}" = "-C" ] && [ "${3:-}" = "remote" ]; then
  echo 'https://github.com/garrytan/gstack.git'
else
  exit 0
fi
EOF
chmod +x "$fake_bin/bun" "$fake_bin/npx" "$fake_bin/git"

fake_home="$test_root/fake-home"
HOME="$fake_home" PATH="$fake_bin:$PATH" GSTACK_DIR="$fake_home/.gstack/repos/gstack" "$repo_root/install.sh" >/dev/null
HOME="$fake_home" PATH="$fake_bin:$PATH" GSTACK_DIR="$fake_home/.gstack/repos/gstack" "$repo_root/install.sh" >/dev/null

collision_home="$test_root/collision-home"
if HOME="$collision_home" PATH="$fake_bin:$PATH" GSTACK_DIR="$collision_home/.gstack/repos/gstack" FAKE_GSTACK_COLLISION=1 "$repo_root/install.sh" >/dev/null 2>&1; then
  echo "Expected conflicting gstack skill name to be rejected" >&2
  exit 1
fi

echo "INSTALL TEST VALID"
