"""Regression tests: migration errors must never erase existing data."""
import tempfile
import unittest
from pathlib import Path

from migration_store_guard import DANGEROUS_FALLBACK, SAFE_FALLBACK, patch, transform


class MigrationStoreGuardTests(unittest.TestCase):
    def test_removes_destructive_reset(self):
        source = "header\n" + DANGEROUS_FALLBACK + "\nfooter"
        modified = transform(source)
        self.assertIn(SAFE_FALLBACK, modified)
        self.assertNotIn("removeItem(at:", modified)
        self.assertNotIn("copyItem(at:", modified)
        self.assertTrue(modified.startswith("header\n"))
        self.assertTrue(modified.endswith("\nfooter"))

    def test_idempotent(self):
        modified = transform(DANGEROUS_FALLBACK)
        self.assertEqual(transform(modified), modified)

    def test_rejects_unknown_source(self):
        with self.assertRaises(RuntimeError):
            transform("} catch { // unknown backup migration logic }")

    def test_rejects_duplicate_destructive_blocks(self):
        with self.assertRaises(RuntimeError):
            transform(DANGEROUS_FALLBACK + DANGEROUS_FALLBACK)

    def test_patch_requires_source_file(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(RuntimeError):
                patch(Path(folder), lambda path, transform: None)


if __name__ == "__main__":
    unittest.main()
