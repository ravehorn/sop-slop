# Modes, Lanes, and Tiers

## Entry mode

### `greenfield`

Use when little trustworthy code or product structure exists. Use `/wayfinder` first only when the effort is too large for one agent session.

### `prototype-salvage`

Use when working code exists but product truth, scope, architecture, or verification is weak. Read [prototype-salvage-audit.md](prototype-salvage-audit.md) before selecting the restart point.

### `evolution`

Use when a mature repository already has canonical product documents, architecture, tasks, and verification. Preserve those artifacts and begin at the first missing stage.

## Work lane

### `strategy-decision`

Company strategy, positioning, packaging, non-product pricing, hiring, fundraising, or partnerships. Default to `/grill-me`; add `/office-hours` only for customer-problem or opportunity questions. No build chain by default.

### `product-change`

New product behavior, domain terminology, workflows, economics, permissions, schema, integrations, or user experience. Use the product lifecycle.

### `review-only`

Evaluate an idea, plan, design, architecture, diff, or running product without implementation authority. Run the relevant review lens and stop.

### `approved-build`

An approved canonical plan or spec already exists. Skip alignment that would merely re-interview settled decisions and start at the first missing review or implementation stage.

## Scale tier

Apply scale tiers only to `product-change` and `approved-build`. A `strategy-decision` is not T-tiered unless it creates product work.

### `T1 Small Slice`

Bounded, already-clear behavior with no domain, architecture, security, pricing, schema, integration, or multi-surface change. This meta-skill should normally exit to the direct engineering workflow.

### `T2 Major Feature`

New workflows, multi-surface behavior, schema or integration changes, economics, policy, or meaningful rollout risk. Use the product-change lane with conditional alignment and full engineering review.

### `T3 Program or Overhaul`

New apps, platform shifts, foundational overhauls, or work that cannot fit in one agent session. Use `/wayfinder`, then run the T2 chain one approved vertical slice at a time.

## Escalate at least to T2 for

- durable schema changes
- authentication, authorization, permissions, privacy, or security changes
- product pricing, billing, costing, tax, or economics logic
- external integrations
- agent autonomy or safety-policy changes
- multi-surface UX changes
- meaningful migration or rollout risk
- unclear or conflicting domain intent

When scale is uncertain, inspect the actual blast radius before deciding. Do not escalate merely because a feature sounds important.
