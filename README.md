# SOP SLOP

SOP SLOP turns product ideas and observations into aligned, executable work and verified results. Version 0.8 adds opt-in parallel worktree development and serialized delivery to the small local supervisor, alongside Matt Pocock's and gstack's upstream-maintained techniques.

It is designed for substantial features, product-domain changes, and end-to-end product reviews—not small, already-clear fixes.

## What it changes

- starts from concrete behavior examples; settled decisions do not trigger another interview
- checks in after three answered material questions without capping necessary clarification; routine choices stay delegated
- preserves the mission, annotation mapping and pending work in local SQLite state
- captures real check exits and binds proof to the candidate and assertion files
- rejects stale evidence, rejected reviews, competing writers and uncertain spawn retries
- seals delivery before resource reconciliation and run review
- keeps upstream skills updateable and runs only needed specialist lenses
- gives independent peers their own worktree leases, scoped test locks, a FIFO
  delivery lane and a compact mailbox without a central orchestrator

See [coordination and safe adoption](sop-slop/references/coordination.md).
Activation requires a drained checkpoint and explicitly fences older controllers;
do not overwrite an active run's pinned package.

Version 0.8.2 adds [execution readiness and bounded evidence reuse](sop-slop/references/evidence-reuse.md):
keep focused repairs narrow and qualify once at a coherent release boundary.
Missing assertion files fail at plan time; declared prerequisites gate expensive
checks and readiness gates freeze. Failed-run continuations retain repair budgets.
Eligible proof can be reused during build/check with a fresh environment observation;
optional reviewed dependency closures require exact outside-change review.
Release and production observations stay exact-revision checks. Adoption is explicit;
existing pins remain. See [scope and verification](docs/ru01-execution-improvements.md).

The verification guide incorporates field lessons on fixture causality/lifetime,
actual producer-consumer contracts, asynchronous effects, semantic UI assertions
and private failure diagnostics. These refine existing review—not extra gates or
permission to weaken acceptance. Guidance-only revisions retain controller v0.8.2;
pin the complete package by commit, not version label alone.

Six active phases: understand, plan, build, check, release, finish. This is an
in-task supervisor, not a background service, sandbox, host hook or guarantee of
honest agent behavior. Host permissions remain authoritative. The old 41-node
graph and replay fixtures remain available as legacy diagnostics.

See the [architecture decision](docs/v0.7-design.md),
[CLI guide](sop-slop/references/supervisor-guide.md), and
[comparison and test evidence](docs/v0.7-evaluation.md).

## Requirements

- OpenAI Codex
- Git
- Node.js/npm (`npx`)
- [Bun](https://bun.sh/) for gstack
- Python 3.9+ for the standard-library supervisor and validation

## One-command install

This installs SOP SLOP, the Matt Pocock skills it directly relies on, and the complete gstack Codex pack with the short skill names SOP SLOP expects:

```bash
curl -fsSL https://raw.githubusercontent.com/ravehorn/sop-slop/main/install.sh | bash
```

To install every Matt Pocock skill instead of only the required subset:

```bash
curl -fsSL https://raw.githubusercontent.com/ravehorn/sop-slop/main/install.sh | bash -s -- --all-matt
```

For the inspect-first route:

```bash
git clone https://github.com/ravehorn/sop-slop.git
cd sop-slop
./install.sh
```

Review remote scripts before piping them to a shell. The installer refuses to pull or execute an existing gstack directory unless its `origin` is the official `garrytan/gstack` repository, and verified checkouts update only with `git pull --ff-only`.

## Use

Invoke the skill with:

```text
$sop-slop
```

Example:

```text
Use $sop-slop to design, implement, ship, and verify this feature in production. Keep the primary mission focused and create linked tasks for unrelated side quests.
```

Release and linked-task authority still come from the request and repository rules. Review or planning requests do not silently become deployment authority. Cleanup is limited to exact current-run resources: dirty, untracked, unpushed, unmerged, shared, canonical, active, or ownership-unknown resources are preserved, and destructive cleanup requires one exact recoverability card plus explicit `yes` or `do it` confirmation. Security or tenant-boundary expansion, missing credentials, conflicts, failed checks, and unhealthy deployments remain real stops.

## Validate

```bash
./scripts/verify-package.sh
```

The check runs disposable supervisor integration/failure tests, legacy graph and
replay diagnostics, and installer tests without downloading dependencies. The
evaluation report separates deterministic enforcement tests from live-agent
behavior and simulated release observations from real production evidence.

## Upstream projects

SOP SLOP does not vendor or modify its upstream dependencies. The installer fetches them from their official repositories so they remain independently updateable:

- [Matt Pocock's skills](https://github.com/mattpocock/skills) — MIT
- [gstack](https://github.com/garrytan/gstack) — MIT
- [`skills` installer](https://github.com/vercel-labs/skills)

This project is independent and is not affiliated with or endorsed by Matt Pocock, Garry Tan, or OpenAI.

## License

MIT. See [LICENSE](LICENSE).
