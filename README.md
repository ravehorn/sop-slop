# SOP SLOP

SOP SLOP is a focused product-delivery graph for Codex. It combines Matt Pocock's alignment and specification skills with gstack's product, engineering, design, QA, ship, and deployment workflow.

It is designed for substantial features, product-domain changes, and end-to-end product reviews—not small, already-clear fixes.

## What it changes

- binds one primary mission and observable completion target
- turns annotation batches into fully covered, deduplicated problem ledgers with one durable canonical task per accepted problem
- executes clear annotation problems one at a time and asks only the material questions needed for ambiguous ones
- moves unrelated side quests into linked tasks when authorized, without pivoting the parent run
- records an alignment lock before transferring reversible technical and version decisions to the controller
- treats nested skill finals as stage evidence rather than permission to stop
- lets eligible product, design, engineering, review, QA, and learning stages call one bounded peer-deliberation protocol and return to the exact caller
- continues an explicitly authorized full-delivery run through production verification
- records a run receipt and automatic review before closure

The active graph is supervised and inspectable: 39 nodes, 97 edges, typed evidence, named guards, bounded back-edges, and release authority gates.

## Requirements

- OpenAI Codex
- Git
- Node.js/npm (`npx`)
- [Bun](https://bun.sh/) for gstack
- Python 3 for graph validation

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

Release and linked-task authority still come from the request and repository rules. Review or planning requests do not silently become deployment authority. Destructive data actions, security or tenant-boundary expansion, missing credentials, conflicts, failed checks, and unhealthy deployments remain real stops.

## Validate

```bash
./scripts/verify-package.sh
```

The check validates the skill, graph policy, 60 negative graph cases, 23 adversarial deliberation receipts, annotation-batch and two-profile deliberation forward runs, synthetic closure, default and all-Matt install plans, gstack origin enforcement, rerun routing, and non-git/wrong-remote refusal without downloading dependencies.

## Upstream projects

SOP SLOP does not vendor or modify its upstream dependencies. The installer fetches them from their official repositories so they remain independently updateable:

- [Matt Pocock's skills](https://github.com/mattpocock/skills) — MIT
- [gstack](https://github.com/garrytan/gstack) — MIT
- [`skills` installer](https://github.com/vercel-labs/skills)

This project is independent and is not affiliated with or endorsed by Matt Pocock, Garry Tan, or OpenAI.

## License

MIT. See [LICENSE](LICENSE).
