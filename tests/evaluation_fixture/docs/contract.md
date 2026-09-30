# Recipe archive

Archive is a reversible visibility change, never deletion. `set_archived` changes
the requested row in the supplied list in place, returning a copy of that row.
Only role `manager` may archive/restore. Other roles raise PermissionError.
Only the matching tenant is visible; missing/cross-tenant IDs raise LookupError.
The boolean `archived` argument must actually be bool, else ValueError.
Repeated archive or restore succeeds without any other change.

`list_recipes(rows, tenant, include_archived=False)` returns copies for that tenant.
By default it excludes archived rows; include_archived=True includes both states.
Legacy rows without an archived key count as active. Preserve row order, IDs,
names, and all unrelated fields. Empty catalogs are valid.

No hard delete, UI, database, analytics, notifications, background jobs, or release.
