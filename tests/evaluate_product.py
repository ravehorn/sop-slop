"""Independent acceptance oracle; run against either disposable product path."""
import importlib.util
from pathlib import Path
import sys
import unittest

spec = importlib.util.spec_from_file_location("subject_service", Path(sys.argv.pop(1)) / "service.py")
service = importlib.util.module_from_spec(spec)
spec.loader.exec_module(service)


class ProductAcceptance(unittest.TestCase):
    def setUp(self):
        self.rows = [{"id": "same", "tenant": "other", "name": "Other", "archived": False},
                     {"id": "same", "tenant": "ours", "name": "Soup", "note": "keep"},
                     {"id": "old", "tenant": "ours", "name": "Pie", "archived": True}]

    def test_default_active_including_legacy(self):
        self.assertEqual([x["name"] for x in service.list_recipes(self.rows, "ours")], ["Soup"])

    def test_include_archived_preserves_order(self):
        self.assertEqual([x["name"] for x in service.list_recipes(self.rows, "ours", include_archived=True)], ["Soup", "Pie"])

    def test_manager_archive_restore_idempotent_and_tenant_scoped(self):
        for flag in (True, True, False, False):
            row = service.set_archived(self.rows, "ours", "manager", "same", flag)
            self.assertIs(row["archived"], flag)
            self.assertIs(self.rows[1]["archived"], flag)
            self.assertFalse(self.rows[0]["archived"])
            self.assertEqual((len(self.rows), row["note"], row["name"]), (3, "keep", "Soup"))

    def test_cook_and_unknown_roles_cannot_mutate(self):
        for role in ("cook", "admin", "", None):
            with self.assertRaises(PermissionError):
                service.set_archived(self.rows, "ours", role, "same", True)
        self.assertNotIn("archived", self.rows[1])

    def test_missing_and_other_tenant_ids_do_not_leak(self):
        for tenant, ident in (("absent", "same"), ("other", "old"), ("ours", "missing")):
            with self.assertRaises(LookupError):
                service.set_archived(self.rows, tenant, "manager", ident, True)

    def test_boolean_trust_boundary(self):
        for flag in (0, 1, "false", [], None):
            with self.assertRaises(ValueError):
                service.set_archived(self.rows, "ours", "manager", "same", flag)

    def test_returns_copy(self):
        row = service.set_archived(self.rows, "ours", "manager", "same", True)
        row["name"] = "wrong"
        self.assertEqual(self.rows[1]["name"], "Soup")

    def test_empty(self):
        self.assertEqual(service.list_recipes([], "ours"), [])


unittest.main(verbosity=2)
