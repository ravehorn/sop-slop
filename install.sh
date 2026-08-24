#!/usr/bin/env bash
set -euo pipefail

all_matt=0
dry_run=0
for arg in "$@"; do
  case "$arg" in
    --all-matt) all_matt=1 ;;
    --dry-run) dry_run=1 ;;
    *) echo "Unknown option: $arg" >&2; exit 2 ;;
  esac
done

run() {
  if [ "$dry_run" -eq 1 ]; then
    printf '  '
    printf '%q ' "$@"
    printf '\n'
  else
    "$@"
  fi
}

if [ "$dry_run" -eq 0 ]; then
  for command_name in git npx bun; do
    command -v "$command_name" >/dev/null 2>&1 || {
      echo "Missing requirement: $command_name" >&2
      exit 1
    }
  done
fi

sop_slop_source="${SOP_SLOP_SOURCE:-ravehorn/sop-slop}"
gstack_dir="${GSTACK_DIR:-$HOME/.gstack/repos/gstack}"
gstack_source="https://github.com/garrytan/gstack.git"

is_official_gstack_remote() {
  case "$1" in
    https://github.com/garrytan/gstack|https://github.com/garrytan/gstack.git|git@github.com:garrytan/gstack.git|ssh://git@github.com/garrytan/gstack.git) return 0 ;;
    *) return 1 ;;
  esac
}

echo "Installing Matt Pocock skills for Codex..."
if [ "$all_matt" -eq 1 ]; then
  run npx skills@latest add mattpocock/skills --skill '*' -g -a codex -y
else
  matt_skills=(
    setup-matt-pocock-skills
    wayfinder
    grill-me
    grill-with-docs
    to-spec
    to-tickets
    implement
    tdd
    code-review
  )
  matt_args=()
  for skill in "${matt_skills[@]}"; do
    matt_args+=(--skill "$skill")
  done
  run npx skills@latest add mattpocock/skills "${matt_args[@]}" -g -a codex -y
fi

echo "Installing gstack for Codex..."
if [ -e "$gstack_dir" ]; then
  gstack_remote="$(git -C "$gstack_dir" remote get-url origin 2>/dev/null || true)"
  if ! is_official_gstack_remote "$gstack_remote"; then
    echo "Refusing to pull or execute unverified gstack checkout: $gstack_dir" >&2
    echo "Expected origin: $gstack_source" >&2
    exit 1
  fi
  run git -C "$gstack_dir" pull --ff-only
else
  run mkdir -p "$(dirname "$gstack_dir")"
  run git clone --single-branch --depth 1 "$gstack_source" "$gstack_dir"
fi
run "$gstack_dir/setup" --host codex --quiet --no-prefix

echo "Installing SOP SLOP for Codex..."
run npx skills@latest add "$sop_slop_source" --skill sop-slop -g -a codex -y

if [ "$dry_run" -eq 0 ]; then
  codex_skills="$HOME/.codex/skills"
  required_skills=(
    sop-slop:sop-slop
    setup-matt-pocock-skills:setup-matt-pocock-skills
    wayfinder:wayfinder
    grill-me:grill-me
    grill-with-docs:grill-with-docs
    to-spec:to-spec
    to-tickets:to-tickets
    implement:implement
    tdd:tdd
    code-review:code-review
    gstack-office-hours:office-hours
    gstack-plan-ceo-review:plan-ceo-review
    gstack-plan-design-review:plan-design-review
    gstack-plan-eng-review:plan-eng-review
    gstack-review:review
    gstack-qa:qa
    gstack-ship:ship
    gstack-land-and-deploy:land-and-deploy
  )
  for requirement in "${required_skills[@]}"; do
    directory="${requirement%%:*}"
    skill_name="${requirement#*:}"
    skill_file="$codex_skills/$directory/SKILL.md"
    if [ ! -f "$skill_file" ] || ! grep -q "^name: $skill_name$" "$skill_file"; then
      echo "Missing or conflicting required Codex skill: $skill_name ($skill_file)" >&2
      exit 1
    fi
  done
fi

echo "SOP SLOP installation complete. Invoke it with: \$sop-slop"
