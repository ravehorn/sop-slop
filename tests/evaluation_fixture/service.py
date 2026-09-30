"""Small tenant-scoped recipe catalog used only for workflow evaluation."""


def list_recipes(rows, tenant):
    return [dict(row) for row in rows if row["tenant"] == tenant]


def set_archived(rows, tenant, role, recipe_id, archived):
    raise NotImplementedError("Archive and restore are not implemented")
