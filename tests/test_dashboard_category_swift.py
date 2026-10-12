"""Compile the production Swift spending aggregator with synthetic transactions."""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

SOURCE = Path(__file__).resolve().parents[1] / "FinTrackDashboard.swift"

class CategorySwiftExecutionTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("swiftc"), "swiftc unavailable")
    def test_identity_fx_uncategorized_transfers_and_ties(self):
        code = SOURCE.read_text(encoding="utf-8")
        first = code.index("private struct FinTrackCategoryTotal: Identifiable")
        last = code.index("struct FinTrackDashboardView: View", first)
        model = code[first:last].replace("private struct", "struct", 1)
        first = code.index("    private var topCategories: [FinTrackCategoryTotal]")
        last = code.index("    private var recentTransactions:", first)
        block = code[first:last].replace("private var topCategories:", "var topCategories:", 1)
        program = r'''import Foundation
struct Color { init(hex: String) {} ; static let gray = Color(hex: "#888") }
struct Category { let id: UUID; let name: String; let icon = "tag"; let colorHex = "#ffffff" }
struct Transaction {
    let amount: Decimal
    let category: Category?
    var isTransfer = false
    var isExpense: Bool { amount < 0 && !isTransfer }
}
''' + model + '''
struct Harness {
    let includedTransactions: [Transaction]
    func converted(_ tx: Transaction) -> Decimal { tx.amount * 2 }
''' + block + r'''
}
let a = Category(id: UUID(uuidString: "00000000-0000-0000-0000-000000000001")!, name: "Продукты")
let b = Category(id: UUID(uuidString: "00000000-0000-0000-0000-000000000002")!, name: "Продукты")
let c = Category(id: UUID(uuidString: "00000000-0000-0000-0000-000000000003")!, name: "Без категории")
let tx = [Transaction(amount: -10, category: a), Transaction(amount: -20, category: b),
          Transaction(amount: -5, category: nil), Transaction(amount: -5, category: nil),
          Transaction(amount: -10, category: c), Transaction(amount: 100, category: a),
          Transaction(amount: -50, category: a, isTransfer: true)]
let result = Harness(includedTransactions: tx).topCategories
precondition(result.count == 4)
precondition(result.first(where: { $0.id == a.id })?.amount == 20)
precondition(result.first(where: { $0.id == b.id })?.amount == 40)
precondition(result.first(where: { $0.id == c.id })?.amount == 20)
precondition(result.first(where: { $0.id == nil })?.amount == 20)
precondition(result.first?.id == b.id)
let again = Harness(includedTransactions: tx.reversed()).topCategories
precondition(result.map(\.id) == again.map(\.id))
print("PASS")
'''
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "main.swift"
            exe = Path(tmp) / "category-harness"
            source.write_text(program, encoding="utf-8")
            build = subprocess.run(["swiftc", str(source), "-o", str(exe)],
                                   capture_output=True, text=True, timeout=90)
            self.assertEqual(build.returncode, 0, build.stderr)
            run = subprocess.run([str(exe)], capture_output=True, text=True, timeout=30)
            self.assertEqual(run.returncode, 0, run.stderr)
            self.assertEqual(run.stdout.strip(), "PASS")
