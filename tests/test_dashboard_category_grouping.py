"""Contract checks for category identities in the actual Swift dashboard."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]

class CategoryGroupingContractTests(unittest.TestCase):
    def test_category_identity_is_stable_and_distinct(self):
        swift = (ROOT / "FinTrackDashboard.swift").read_text()
        assert "let id: UUID?" in swift
        assert "tx.category?.id" in swift
        assert "id: categoryID" in swift
        assert 'tx.category?.name ?? "Без категории"' not in swift
        assert "if a.amount != b.amount" in swift
        assert 'a.id?.uuidString ?? ""' in swift

    def test_template_agrees_with_checked_in_source(self):
        source = (ROOT / "FinTrackDashboard.swift").read_text()
        derived = (ROOT / "MintLeaf/Views/DashboardView.swift").read_text()
        self.assertTrue(derived.endswith(source))
