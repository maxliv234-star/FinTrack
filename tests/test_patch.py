"""Run with: python3 -m unittest discover -s tests -v"""
import json
import re
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from apply_ru import apply, add_catalog_to_pbx
from migration_store_guard import DANGEROUS_FALLBACK

PROJECT = r'''/* Begin PBXBuildFile section */
/* Begin PBXFileReference section */
771F588FFE5A0F1A1AE6963F /* MintLeaf */ = {
  isa = PBXGroup;
  children = (
    5581E42C2DC0B5EF4E095CD6 /* Assets.xcassets */,
  );
};
knownRegions = (
 en,
);
6DD71D64531275505222415F /* Assets.xcassets in Resources */,
089AB54AA1A7868E8DCE41FA /* Assets.xcassets in Resources */,
INFOPLIST_KEY_CFBundleDisplayName = "Mint Leaf";
PRODUCT_BUNDLE_IDENTIFIER = com.joefarmer.mintleaf;
'''


class PatchTests(unittest.TestCase):
    def make_fixture(self, base):
        base = Path(base)
        files = {
            'MintLeaf.xcodeproj/project.pbxproj': PROJECT,
            'project.yml': 'PRODUCT_BUNDLE_IDENTIFIER: com.joefarmer.mintleaf\nINFOPLIST_KEY_CFBundleDisplayName: Mint Leaf',
            'MintLeaf/Services/SupportedCurrencies.swift': '''struct CurrencyInfo {
 let code: String
 let name: String
 let flag: String
}
enum SupportedCurrencies {
 static let all: [CurrencyInfo] = [
  CurrencyInfo(code: "USD", name: "US Dollar", flag: "🇺🇸"),
  CurrencyInfo(code: "GBP", name: "British Pound", flag: "🇬🇧"),
  CurrencyInfo(code: "RUB", name: "Russian Ruble", flag: "🇷🇺"),
    ]
}''',
            'MintLeaf/MintLeafApp.swift': '''struct MintLeafApp {
 init() {
  let schema = Schema([
  ])
  do {
    container = try ModelContainer(for: schema, configurations: [config])
''' + DANGEROUS_FALLBACK + '''
 }
 var body: some View {
  ContentView()
                .preferredColorScheme(nil)
  SettingsView()
                .preferredColorScheme(nil)
 }
}''',
            'MintLeaf/Services/CurrencyFormatter.swift': 'f.numberStyle = .currency\nlet c = UserDefaults.standard.string(forKey: "defaultCurrency") ?? "USD"',
            'MintLeaf/Services/ExchangeRateService.swift': '''import Foundation
final class ExchangeRateService {
    /// Fetches live ECB rates (via frankfurter.dev, free/no key) and caches them.
    func refresh() async {}
    /// Get the user's preferred currency
    var preferredCurrency: String { UserDefaults.standard.string(forKey: "defaultCurrency") ?? "USD" }
}''',
            'MintLeaf/Models/Account.swift': 'init(currency: String = "USD") {}',
            'MintLeaf/Models/ScheduledTransaction.swift': 'var currency: String = "USD"\nlet c = value ?? "USD"',
            'MintLeaf/Views/Settings/SettingsView.swift': '@AppStorage("defaultCurrency") private var defaultCurrency: String = "USD"\nText(cat.name)',
            'MintLeaf/Views/Accounts/NewAccountSheet.swift': 'let currency = value ?? "USD"\nText(category.name)',
            'MintLeaf/Views/Transactions/ScheduledListView.swift': 'let currency = value ?? "USD"',
            'MintLeaf/Views/Transactions/SubscriptionCalendarView.swift': 'let currency = value ?? "USD"',
            'MintLeaf/Services/SampleDataGenerator.swift': 'UserDefaults.standard.set("USD", forKey: "defaultCurrency")',
            'MintLeaf/Views/Components/TransactionRow.swift': 'Text(cat.name)',
            'MintLeaf/Views/ContentView.swift': 'DashboardView(onReviewDataHealth: { selection = .dataHealth })',
            'MintLeaf/Views/DashboardView.swift': 'import SwiftUI\nimport SwiftData\n\nenum DashboardCard: String { case heroBalance = "Net Worth" }',
            'MintLeaf/Views/Trends/NetWorthView.swift': 'struct NetWorthView {\n @State private var timeRange: Int = 2\n let amount = accounts.reduce(Decimal.zero) { $0 + $1.currentBalance }\n}',
            'MintLeaf/Views/Trends/TrendsView.swift': 'struct TrendsView {\n @State private var timeRange: Int = 2\n let amount = allTransactions.reduce(Decimal.zero) { $0 + $1.amount }\n}',
            'MintLeaf/Views/Trends/ReportsView.swift': 'struct ReportsView {\n @Environment(\\.colorScheme) private var scheme\n let amount = allTransactions.reduce(Decimal.zero) { $0 + $1.amount }\n}',
            'MintLeaf/Services/CashflowForecaster.swift': 'final class CashflowForecaster {\n let amount = allTransactions.reduce(Decimal.zero) { $0 + $1.amount }\n}',
            'MintLeaf/Views/ForecastView.swift': 'struct ForecastView {\n @Environment(\\.colorScheme) private var scheme\n let amount = accounts.reduce(Decimal.zero) { $0 + $1.currentBalance }\n}',
            'MintLeaf/Views/Trends/InsightsView.swift': 'struct InsightsView {\n @Environment(\\.colorScheme) private var scheme\n let amount = accounts.reduce(Decimal.zero) { $0 + $1.currentBalance }\n}',

        }
        for name, content in files.items():
            path = base / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding='utf-8')
        return base

    def test_catalog_projects_both_targets(self):
        p = add_catalog_to_pbx(PROJECT)
        self.assertEqual(p.count('= {isa = PBXBuildFile; fileRef = FC02C4400000000000000001'), 2)
        self.assertIn('ru,', p)
        self.assertEqual(add_catalog_to_pbx(p), p)

    def test_changes_are_idempotent_and_preserve_ids(self):
        with tempfile.TemporaryDirectory() as temp:
            root = self.make_fixture(temp)
            apply(root)
            before = {str(p.relative_to(root)): p.read_bytes() for p in root.rglob('*') if p.is_file()}
            apply(root)
            after = {str(p.relative_to(root)): p.read_bytes() for p in root.rglob('*') if p.is_file()}
            self.assertEqual(before, after)
            currency_src = (root / 'MintLeaf/Services/SupportedCurrencies.swift').read_text()
            self.assertEqual(re.findall(r'CurrencyInfo\(code: "(\w+)"', currency_src), ['RUB', 'USD', 'EUR'])
            self.assertIn('case heroBalance = "Net Worth"', (root / 'MintLeaf/Views/DashboardView.swift').read_text())
            self.assertEqual((root / 'MintLeaf/Views/DashboardView.swift').read_text().count('struct FinTrackDashboardView: View'), 1)
            self.assertIn('com.maxliv234.fintrackru', (root / 'MintLeaf.xcodeproj/project.pbxproj').read_text())
            catalog = json.loads((root / 'MintLeaf/Localizable.xcstrings').read_text())
            self.assertEqual(catalog['strings']['Payee']['localizations']['ru']['stringUnit']['value'],
                             'Получатель / назначение')
            self.assertIn('LOCALIZATION_REPORT_RU.md', before)
            self.assertEqual(catalog['strings']['Accept']['localizations']['ru']['stringUnit']['value'], 'Принять')
            self.assertEqual(catalog['strings']['Subscription']['localizations']['ru']['stringUnit']['value'], 'Подписка')
            self.assertEqual(catalog['strings']['Locked']['localizations']['ru']['stringUnit']['value'], 'Заблокировано')
            app_swift = (root / 'MintLeaf/MintLeafApp.swift').read_text()
            self.assertIn('FINTRACK DATA SAFETY', app_swift)
            self.assertNotIn('removeItem(at:', app_swift)
            self.assertNotIn('try? FileManager.default.copyItem', app_swift)
            # The sample-data generator must never reset a user preference.
            demo = (root / 'MintLeaf/Services/SampleDataGenerator.swift').read_text()
            self.assertNotIn('UserDefaults.standard.set("RUB", forKey: "defaultCurrency")', demo)
            self.assertNotIn('UserDefaults.standard.set("USD", forKey: "defaultCurrency")', demo)


if __name__ == '__main__':
    unittest.main()