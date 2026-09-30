import unittest
from service import list_recipes


class ExistingTests(unittest.TestCase):
    def test_tenant_visibility_and_copy(self):
        rows = [{"id": "a", "tenant": "one", "name": "Soup"}, {"id": "b", "tenant": "two", "name": "Pie"}]
        found = list_recipes(rows, "one")
        self.assertEqual(len(found), 1)
        found[0]["name"] = "Changed"
        self.assertEqual(rows[0]["name"], "Soup")


if __name__ == "__main__":
    unittest.main()
