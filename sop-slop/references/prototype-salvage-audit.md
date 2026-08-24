# Prototype Salvage Audit

Use this when an existing app or repo exists but the product process is weak.

## 1. Audit goal
Establish what is real today, what the product probably intends to be, and what must be promoted, rewritten, or discarded before production planning continues.

## 2. Audit checklist

### Product surface audit
Inspect:
1. routes, pages, or screens
2. major user-facing flows
3. navigation and shell structure
4. core objects shown to the user

### Data and runtime audit
Inspect:
1. persistence model and storage choices
2. APIs and runtime boundaries
3. background jobs, automations, or agents
4. auth, permissions, or policy logic
5. integrations

### UX and behavior audit
Inspect:
1. interaction model consistency
2. whether primary flows are clear or improvised
3. where feature bloat has accumulated
4. empty, degraded, and error-state behavior
5. evidence of drift between surfaces

### Verification audit
Inspect:
1. tests that exist
2. what is actually verifiable today
3. missing smoke tests or acceptance checks
4. release confidence gaps

## 3. Required outputs
Produce:
1. current-state audit
2. intended-product hypothesis
3. drift and feature-bloat list
4. promotable parts
5. rewrite-required parts
6. unknowns requiring clarification
7. missing artifact map
8. recommended tier and gate restart point

## 4. Promotion rules
Do not treat existing prototype behavior as canonical automatically.
Promote only what is:
1. aligned with the intended product
2. understandable and bounded
3. technically defensible
4. compatible with the desired UX and architecture

Everything else stays provisional until explicitly approved.
