#!/usr/bin/env python3
"""Patch an *unmodified or previously v0.1-patched clone* of Mint Leaf 4.2.

Russian Xcode strings catalog (without rewriting serialization keys); three choices in UI;
RUB fallback; a multi-currency-aware SwiftUI dashboard. Idempotent.
"""
import argparse
import json
import re
import shutil
from pathlib import Path
from base_translations import RU as BASE_RU
from extra_translations import EXTRA_RU
from fix_calculations import patch as patch_financial_analytics
from migration_store_guard import patch as patch_migration_store

BASE = Path(__file__).resolve().parent

RU = dict(BASE_RU)
RU.update({
    # Screenshots / dashboard / onboarding
    "Net Worth": "Чистый капитал", "Financial Health": "Финансовое состояние",
    "Fair": "Удовлетворительно", "Excellent": "Отлично", "Good": "Хорошо",
    "Needs Work": "Требует внимания", "Score": "Оценка", "Assets": "Активы",
    "Liabilities": "Обязательства", "Debt Ratio": "Доля задолженности",
    "Savings Rate": "Доля сбережений", "Net Monthly": "Результат за месяц",
    "Income (30d)": "Доходы (30 дней)", "Expenses (30d)": "Расходы (30 дней)",
    "Last 30 days": "Последние 30 дней", "Recent Transactions": "Последние операции",
    "No prior data": "Нет данных для сравнения", "Upcoming": "Предстоящие",
    "No Transactions Yet": "Операций пока нет", "Add an account and start tracking your finances.": "Добавьте счёт и начните учитывать свои финансы.",
    "Customise": "Настроить", "Customise Dashboard": "Настроить главный экран",
    "Type": "Тип", "Payee": "Получатель / назначение", "Amount": "Сумма",
    "Date": "Дата", "Category": "Категория", "None": "Не выбрана",
    "Transfer to another account": "Перевести на другой счёт",
    "Destination": "Счёт назначения", "Select account": "Выберите счёт",
    "Notes": "Примечание", "Location (optional)": "Местоположение (необязательно)",
    "Cancel": "Отмена", "Add": "Добавить", "Save": "Сохранить",
    "Hide or show the sidebar": "Показать или скрыть боковую панель",
    "Savings & Investments": "Сбережения и инвестиции", "Income & Expenses": "Доходы и расходы",
    "Account Balances": "Остатки по счетам", "No Expenses": "Расходов нет",
    "Compare": "Сравнить", "Previous Period": "Предыдущий период",
    "Your money, at a glance.": "Все ваши финансы на одном экране.",
    "This Month": "Этот месяц", "This Week": "Эта неделя",
    "Year to Date": "С начала года", "All Time": "За всё время",
    "New Transaction": "Новая операция", "Edit Transaction": "Изменить операцию",
    "Today's Activity": "Операции за сегодня", "Transaction Details": "Детали операции",
    "View Details": "Подробнее", "No Transactions": "Нет операций",
    "Search Transactions": "Поиск операций", "Search transactions": "Поиск операций",
    "Account Summary": "Информация о счёте", "Account Balance": "Баланс счёта",
    "Balance Alerts": "Уведомления о балансе", "Credit Card Payments": "Платежи по кредитным картам",
    "New Account": "Новый счёт", "Checking Account": "Текущий счёт",
    "Savings Account": "Накопительный счёт", "Cash Wallet": "Наличные",
    "Account Name": "Название счёта", "Initial Balance": "Начальный баланс",
    "Starting Balance": "Начальный баланс", "Opening Balance": "Начальный баланс",
    "Credit Card": "Кредитная карта", "Savings": "Накопления",
    "Archived": "В архиве", "Archive": "В архив", "Unarchive": "Вернуть из архива",
    "Edit Account": "Изменить счёт", "Delete Account": "Удалить счёт",
    "This will permanently delete all accounts, transactions, budgets, rules, and categories. This cannot be undone.": "Все счета, операции, бюджеты, правила и категории будут удалены без возможности восстановления.",
    "This will add sample accounts, transactions, budgets and scheduled items. Your existing data will not be affected.": "Будут добавлены демонстрационные счета, операции, бюджеты и регулярные платежи. Ваши данные сохранятся.",
    "Hide": "Скрыть", "Show": "Показать", "Open": "Открыть",
    "Reorder Accounts": "Изменить порядок счетов", "Reset to Defaults": "Восстановить настройки",
    "Month": "Месяц", "Quarter": "Квартал", "Year": "Год",
    "Day": "День", "Week": "Неделя", "Months": "Месяцы",
    "View Report": "Открыть отчёт", "Net Change": "Изменение баланса",
    "Balance Trend": "Динамика баланса", "By Category": "По категориям",
    "Top Categories": "Главные категории", "Categories & Tags": "Категории и метки",
    "Food & Drink": "Еда и напитки", "Food & Dining": "Кафе и рестораны",
    "Groceries": "Продукты", "Transportation": "Транспорт",
    "Gas & Fuel": "Топливо", "Housing": "Жильё", "Utilities": "Коммунальные услуги",
    "Healthcare": "Здоровье", "Entertainment": "Развлечения", "Shopping": "Покупки",
    "Subscriptions": "Подписки", "Other": "Прочее", "Other Income": "Прочие доходы",
    "Salary": "Зарплата", "Freelance": "Подработка",
    "Rental Income": "Доход от аренды", "Refunds": "Возвраты",
    "Investment Income": "Доход от инвестиций", "Interests": "Проценты",
    "Transfers": "Переводы", "Transfer": "Перевод",
    "All Transactions": "Все операции", "Clear Filters": "Сбросить фильтры",
    "Select a Category": "Выберите категорию", "New Category": "Новая категория",
    "Recurring Payment": "Повторяющийся платёж", "Scheduled Payments": "Плановые платежи",
    "Add Scheduled Transaction": "Добавить регулярную операцию",
    "Upcoming Bills": "Ближайшие платежи", "Overdue": "Просрочено",
    "Import Excel": "Импорт Excel", "Export to CSV": "Экспорт в CSV",
    "Import PDF": "Импорт PDF", "Import Bank Statement": "Импорт банковской выписки",
    "Review Duplicates": "Проверить дубликаты", "Ignore": "Игнорировать",
    "Ignored": "Пропущено", "Match": "Совпадение", "No match": "Нет совпадений",
    "Choose Bank": "Выберите банк", "Processing": "Обработка",
    "Save Changes": "Сохранить изменения", "Changes saved": "Изменения сохранены",
    "Are you sure?": "Вы уверены?", "Delete Permanently": "Удалить безвозвратно",
    "Financial Overview": "Финансовый обзор", "Monthly Report": "Отчёт за месяц",
    "Yearly Report": "Отчёт за год", "Settings & Preferences": "Настройки",
    "Automatic Backups": "Автоматическое резервное копирование",
    "Data Security": "Безопасность данных", "Privacy Dashboard": "Конфиденциальность",
    "What’s New": "Что нового", "About Mint Leaf": "О Mint Leaf",
    "Help & Support": "Помощь и поддержка", "Keyboard Shortcuts": "Горячие клавиши",
    "General Settings": "Основные настройки", "Default Currency": "Основная валюта",
    "US Dollar": "Доллар США", "Euro": "Евро", "Russian Ruble": "Российский рубль",
    "All Categories": "Все категории", "All Accounts": "Все счета",
    "Edit": "Изменить", "Remove": "Убрать", "Delete": "Удалить",
    "Dismiss": "Закрыть", "OK": "ОК", "Done": "Готово",
})

RU.update(EXTRA_RU)
RU["Mint Leaf"] = "FinTrack Mac"

CURRENCY_PATHS = (
    "MintLeaf/Services/CurrencyFormatter.swift",
    "MintLeaf/Services/ExchangeRateService.swift",
    "MintLeaf/Models/Account.swift",
    "MintLeaf/Models/ScheduledTransaction.swift",
    "MintLeaf/Views/Settings/SettingsView.swift",
    "MintLeaf/Views/Accounts/NewAccountSheet.swift",
    "MintLeaf/Views/Transactions/ScheduledListView.swift",
    "MintLeaf/Views/Transactions/SubscriptionCalendarView.swift",
)


def rewrite(file: Path, transform):
    old = file.read_text(encoding="utf-8")
    new = transform(old)
    if new != old:
        file.write_text(new, encoding="utf-8")
        return 1
    return 0


def add_catalog_to_pbx(pbx: str) -> str:
    """Register string catalog on both macOS and iOS targets without XcodeGen."""
    if "Localizable.xcstrings in Resources" in pbx:
        return pbx
    file_ref = "FC02C4400000000000000001"
    mac_build = "FC02C4400000000000000002"
    ios_build = "FC02C4400000000000000003"
    needles = ["/* Begin PBXBuildFile section */", "/* Begin PBXFileReference section */",
               "/* MintLeaf */ = {", "/* Assets.xcassets in Resources */,"]
    for needle in needles:
        if needle not in pbx:
            raise ValueError(f"Unexpected Xcode project layout; missing {needle!r}")
    pbx = pbx.replace("/* Begin PBXBuildFile section */", "/* Begin PBXBuildFile section */\n"
        f"\t\t{mac_build} /* Localizable.xcstrings in Resources */ = {{isa = PBXBuildFile; fileRef = {file_ref} /* Localizable.xcstrings */; }};\n"
        f"\t\t{ios_build} /* Localizable.xcstrings in Resources */ = {{isa = PBXBuildFile; fileRef = {file_ref} /* Localizable.xcstrings */; }};", 1)
    pbx = pbx.replace("/* Begin PBXFileReference section */", "/* Begin PBXFileReference section */\n"
        f"\t\t{file_ref} /* Localizable.xcstrings */ = {{isa = PBXFileReference; lastKnownFileType = text.json.xcstrings; path = Localizable.xcstrings; sourceTree = \"<group>\"; }};", 1)
    pbx, count = re.subn(r'(\/\* MintLeaf \*\/ = \{\s+isa = PBXGroup;\s+children = \(\s*)',
        rf'\1{file_ref} /* Localizable.xcstrings */,\n\t\t\t\t', pbx, count=1)
    if count != 1:
        raise ValueError("Can't locate MintLeaf PBXGroup")
    # Existing project contains one macOS and one iOS assets build reference.
    mac_assets = "6DD71D64531275505222415F /* Assets.xcassets in Resources */,"
    ios_assets = "089AB54AA1A7868E8DCE41FA /* Assets.xcassets in Resources */,"
    if pbx.count(mac_assets) != 1 or pbx.count(ios_assets) != 1:
        raise ValueError("Unable to locate both Xcode resource build phases")
    pbx = pbx.replace(mac_assets, mac_assets + f"\n\t\t\t\t{mac_build} /* Localizable.xcstrings in Resources */,", 1)
    pbx = pbx.replace(ios_assets, ios_assets + f"\n\t\t\t\t{ios_build} /* Localizable.xcstrings in Resources */,", 1)
    # Register Russian as a known project region.
    pbx = pbx.replace("knownRegions = (\n", "knownRegions = (\n\t\t\t\tru,\n", 1)
    return pbx


def apply(root: Path):
    expected = [root / "MintLeaf/Services/SupportedCurrencies.swift",
                root / "MintLeaf.xcodeproj/project.pbxproj",
                root / "MintLeaf/Views/DashboardView.swift"]
    if not all(f.is_file() for f in expected):
        raise RuntimeError("Expected Mint Leaf 4.2 clone with Xcode project and Swift sources")
    count = 0
    currency = expected[0]
    def currencies(src):
        replacement = '''static let all: [CurrencyInfo] = [
        CurrencyInfo(code: "RUB", name: "Российский рубль", flag: "🇷🇺"),
        CurrencyInfo(code: "USD", name: "Доллар США", flag: "🇺🇸"),
        CurrencyInfo(code: "EUR", name: "Евро", flag: "🇪🇺"),
    ]'''
        changed, n = re.subn(r"static let all: \[CurrencyInfo\] = \[.*?\n    \]", replacement, src, count=1, flags=re.S)
        if n != 1:
            raise RuntimeError("Can't identify the currency picker model")
        return changed
    count += rewrite(currency, currencies)

    # Official CBR source for RUB, USD and EUR. The original ECB feed may not
    # provide current RUB rates, so do not treat its 91.5 fallback as live.
    service = root / "MintLeaf/Services/ExchangeRateService.swift"
    def replace_exchange_service(src):
        if "class FinTrackCBRRateReader" in src:
            return src
        if "import FoundationXML" not in src:
            src = src.replace("import Foundation", "import Foundation\n#if canImport(FoundationXML)\nimport FoundationXML\n#endif", 1)
        before = src.index("    /// Fetches live ECB rates")
        after = src.index("    /// Get the user's preferred currency", before)
        refresh = (BASE / "CBRRefresh.swift.txt").read_text(encoding="utf-8")
        parser = (BASE / "CBRParser.swift.txt").read_text(encoding="utf-8")
        return src[:before] + refresh + src[after:] + parser
    count += rewrite(service, replace_exchange_service)

    # Add regression tests to the existing, already-registered macOS test file.
    tests = root / "MintLeafTests/MoneyMathTests.swift"
    if tests.is_file():
        def test_changes(src):
            if "class FinTrackCurrencyTests" in src: return src
            if "import FoundationXML" not in src:
                src = "#if canImport(FoundationXML)\nimport FoundationXML\n#endif\n" + src
            return src + "\n" + (BASE / "FinTrackCurrencyTests.swift.txt").read_text(encoding="utf-8")
        count += rewrite(tests, test_changes)

    for name in CURRENCY_PATHS:
        file = root / name
        def change(src):
            new = src.replace('?? "USD"', '?? "RUB"')
            if name.endswith("Account.swift"):
                new = new.replace('currency: String = "USD"', 'currency: String = "RUB"')
            if name.endswith("ScheduledTransaction.swift"):
                new = new.replace('var currency: String = "USD"', 'var currency: String = "RUB"')
            if name.endswith("SettingsView.swift"):
                new = new.replace('@AppStorage("defaultCurrency") private var defaultCurrency: String = "USD"',
                    '@AppStorage("defaultCurrency") private var defaultCurrency: String = "RUB"')
            if name.endswith("CurrencyFormatter.swift") and 'Locale(identifier: "ru_RU")' not in new:
                new = new.replace('f.numberStyle = .currency',
                    'f.numberStyle = .currency\n        f.locale = Locale(identifier: "ru_RU")')
            return new
        count += rewrite(file, change)

    # Loading sample data must never override the user's explicitly selected
    # reporting currency, even when the demo accounts themselves are in USD.
    count += rewrite(root / "MintLeaf/Services/SampleDataGenerator.swift",
        lambda src: re.sub(
            r'(?m)^[ \t]*UserDefaults\.standard\.set\("(?:USD|RUB)", forKey: "defaultCurrency"\)[ \t]*(?:\n|$)',
            '',
            src.replace('        // Reset currency to match sample data\n', '')
        ))

    def app_changes(src):
        src = src.replace('ContentView()\n                .preferredColorScheme',
                          'ContentView()\n                .environment(\\.locale, Locale(identifier: "ru_RU"))\n                .preferredColorScheme')
        src = src.replace('SettingsView()\n                .preferredColorScheme',
                          'SettingsView()\n                .environment(\\.locale, Locale(identifier: "ru_RU"))\n                .preferredColorScheme')
        marker = "// FINTRACK SAFE CURRENCY PREFERENCE"
        if marker not in src:
            src = src.replace('        let schema = Schema([', '''        // FINTRACK SAFE CURRENCY PREFERENCE. Never alter historical account amounts.
        if let preferred = UserDefaults.standard.string(forKey: "defaultCurrency"),
           !["RUB", "USD", "EUR"].contains(preferred) {
            UserDefaults.standard.set("RUB", forKey: "defaultCurrency")
        }
        let schema = Schema([''', 1)
        return src
    count += rewrite(root / "MintLeaf/MintLeafApp.swift", app_changes)
    count += patch_migration_store(root, rewrite)

    count += patch_financial_analytics(root, rewrite)

    # Existing original code uses UI labels as enum raw values. Do NOT rewrite literals
    # across Swift sources: that would alter data and persisted dashboard configuration.
    for file in (root / "MintLeaf/Views").rglob("*.swift"):
        def translate_dynamic(src):
            for var in ("cat", "category"):
                src = src.replace(f"Text({var}.name)", f"Text(LocalizedStringKey({var}.name))")
                src = src.replace(f"Label({var}.name, systemImage:",
                                  f"Label(LocalizedStringKey({var}.name), systemImage:")
            return src
        count += rewrite(file, translate_dynamic)

    dashboard = root / "MintLeaf/Views/DashboardView.swift"
    template = (BASE / "FinTrackDashboard.swift").read_text(encoding="utf-8")
    def dashboard_changes(src):
        if "import Charts" not in src:
            src = src.replace("import SwiftUI\n", "import SwiftUI\nimport Charts\n", 1)
        if "import Combine" not in src:
            src = src.replace("import SwiftUI\n", "import SwiftUI\nimport Combine\n", 1)
        if "struct FinTrackDashboardView: View" not in src:
            src += "\n\n" + template
        return src
    count += rewrite(dashboard, dashboard_changes)

    def content_changes(src):
        return src.replace('DashboardView(onReviewDataHealth: { selection = .dataHealth })',
            '''FinTrackDashboardView(
                onAddTransaction: { showingNewTransaction = true },
                onAddAccount: { showingNewAccount = true },
                onReviewDataHealth: { selection = .dataHealth }
            )''')
    count += rewrite(root / "MintLeaf/Views/ContentView.swift", content_changes)

    # The original Settings links to an updater for the original Mint Leaf app.
    # Never offer upstream DMG upgrades for our private fork.
    def settings_updater(src):
        src = src.replace("\n            updateCheckerView\n", "\n            Label(\"Сборки FinTrack Mac доступны через GitHub Actions\", systemImage: \"shippingbox\")\n                .font(.subheadline)\n                .foregroundStyle(.secondary)\n")
        src = src.replace('Label("View on GitHub", systemImage: "link")',
                          'Label("Исходный проект Mint Leaf (MIT)", systemImage: "link")')
        return src
    count += rewrite(root / "MintLeaf/Views/Settings/SettingsView.swift", settings_updater)


    # Unique ID keeps the upstream Mint Leaf sandbox, preferences and finance data intact.
    pbx = root / "MintLeaf.xcodeproj/project.pbxproj"
    def update_pbx(src):
        src = src.replace("com.joefarmer.mintleaf", "com.maxliv234.fintrackru")
        src = src.replace('INFOPLIST_KEY_CFBundleDisplayName = "Mint Leaf";',
                          'INFOPLIST_KEY_CFBundleDisplayName = "FinTrack Mac";')
        return add_catalog_to_pbx(src)
    count += rewrite(pbx, update_pbx)
    count += rewrite(root / "project.yml", lambda src: src.replace("com.joefarmer.mintleaf", "com.maxliv234.fintrackru")
                 .replace('INFOPLIST_KEY_CFBundleDisplayName: Mint Leaf',
                          'INFOPLIST_KEY_CFBundleDisplayName: FinTrack Mac'))

    catalog = {"sourceLanguage": "en", "strings": {}, "version": "1.0"}
    for english, russian in sorted(RU.items()):
        catalog["strings"][english] = {"localizations": {"ru": {"stringUnit": {
            "state": "translated", "value": russian
        }}}}
    cat_path = root / "MintLeaf/Localizable.xcstrings"
    body = json.dumps(catalog, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if not cat_path.exists() or cat_path.read_text(encoding="utf-8") != body:
        cat_path.write_text(body, encoding="utf-8")
        count += 1

    workflow_dest = root / ".github/workflows/build-fintrack-macos.yml"
    workflow_dest.parent.mkdir(parents=True, exist_ok=True)
    if not workflow_dest.exists():
        shutil.copy2(BASE / ".github/workflows/build-fintrack-macos.yml", workflow_dest)
        count += 1

    # Reproducible status: report untranslated keys in static localized SwiftUI calls.
    candidates = set()
    pat = re.compile(r'\b(?:Text|Button|Toggle|Picker|Label|Section|TextField|DatePicker|GroupBox|ProgressView|navigationTitle)\(\s*"([^"\\\n]+)"')
    for file in (root / "MintLeaf/Views").rglob("*.swift"):
        for key in pat.findall(file.read_text(encoding="utf-8")):
            if any("A" <= char <= "z" for char in key) and key not in RU:
                candidates.add(key)
    report = root / "LOCALIZATION_REPORT_RU.md"
    report.write_text("# FinTrack Mac — проверка локализации\n\n"
        f"- Строк в каталоге: **{len(RU)}**.\n"
        f"- Статических строк интерфейса, которым ещё нужен перевод: **{len(candidates)}**.\n"
        "- Числа на новом экране переводятся в выбранную валюту через ExchangeRateService.\n"
        "- Онлайн-курс не всегда доступен, поэтому данные с устаревшим курсом помечаются как оценочные.\n"
        "- Остатки, существующие категории и исторические операции не меняются.\n"
        "- Новый bundle ID изолирует данные оригинального Mint Leaf.\n\n"
        "## Требуют ручного перевода\n\n" +
        "\n".join(f"- `{x}`" for x in sorted(candidates)) + "\n", encoding="utf-8")
    print(f"Изменено файлов: {count}")
    print(f"Строк в русской локализации: {len(RU)}")
    print(f"Осталось неподтверждённых статических строк: {len(candidates)}")
    print("Сборка требуется на macOS с Xcode либо GitHub Actions. Данные исходной программы не меняются.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repo", help="path to cloned Mint Leaf 4.2")
    args = parser.parse_args()
    apply(Path(args.repo).expanduser().resolve())


if __name__ == "__main__":
    main()