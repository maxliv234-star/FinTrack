// FinTrack Mac — Russian-first, multi-currency dashboard for Mint Leaf 4.2.
// Appended to the existing DashboardView.swift so both the checked-in Xcode project
// and XcodeGen include it without fragile manual Swift-file registration.

private struct FinTrackFlowPoint: Identifiable {
    let date: Date
    let income: Double
    let expense: Double
    var id: Date { date }
}

private struct FinTrackCategoryTotal: Identifiable {
    let name: String
    let id: UUID?
    let icon: String
    let color: Color
    let amount: Decimal
}

struct FinTrackDashboardView: View {
    @Environment(\.colorScheme) private var colorScheme
    @Query(sort: \Account.sortOrder) private var accounts: [Account]
    @Query(sort: \Transaction.date, order: .reverse) private var transactions: [Transaction]
    @Query(sort: \ScheduledTransaction.nextDate) private var scheduled: [ScheduledTransaction]
    @AppStorage("defaultCurrency") private var preferredCurrency = "RUB"
    @State private var period: Period = .month
    @State private var fxRevision = 0

    var onAddTransaction: (() -> Void)? = nil
    var onAddAccount: (() -> Void)? = nil
    var onReviewDataHealth: (() -> Void)? = nil

    private enum Period: String, CaseIterable {
        case month = "Месяц"
        case quarter = "Квартал"
        case year = "Год"

        var component: Calendar.Component {
            switch self {
            case .month: return .month
            case .quarter: return .quarter
            case .year: return .year
            }
        }

        var bucket: Calendar.Component {
            switch self {
            case .month: return .day
            case .quarter: return .weekOfYear
            case .year: return .month
            }
        }
    }

    private var calendar: Calendar { Calendar.current }
    private var now: Date { Date() }
    private var periodStart: Date {
        calendar.dateInterval(of: period.component, for: now)?.start
            ?? calendar.startOfDay(for: now)
    }
    private var activeAccounts: [Account] { accounts.filter { !$0.isArchived } }
    private var supportedCurrency: String {
        ["RUB", "USD", "EUR"].contains(preferredCurrency) ? preferredCurrency : "RUB"
    }

    private func format(_ amount: Decimal) -> String {
        CurrencyFormatter.shared.format(amount, currency: supportedCurrency)
    }
    private func converted(_ amount: Decimal, currency: String) -> Decimal {
        _ = fxRevision // Refresh the figures after the currency rates update.
        return ExchangeRateService.shared.convert(amount, from: currency, to: supportedCurrency)
    }
    private func converted(_ transaction: Transaction) -> Decimal {
        converted(transaction.amount, currency: transaction.account?.currency ?? supportedCurrency)
    }
    private var includedTransactions: [Transaction] {
        transactions.filter { transaction in
            guard let account = transaction.account, !account.isArchived else { return false }
            return transaction.date >= periodStart && transaction.date <= now
        }
    }
    private var netWorth: Decimal {
        activeAccounts.reduce(Decimal.zero) { $0 + converted($1.currentBalance, currency: $1.currency) }
    }
    private var totalAssets: Decimal {
        activeAccounts.reduce(Decimal.zero) { sum, account in
            sum + max(converted(account.currentBalance, currency: account.currency), Decimal.zero)
        }
    }
    private var totalLiabilities: Decimal {
        activeAccounts.reduce(Decimal.zero) { sum, account in
            sum + max(-converted(account.currentBalance, currency: account.currency), Decimal.zero)
        }
    }
    private var income: Decimal {
        includedTransactions.filter(\.isIncome).reduce(Decimal.zero) { $0 + converted($1) }
    }
    private var expenses: Decimal {
        includedTransactions.filter(\.isExpense).reduce(Decimal.zero) { $0 + abs(converted($1)) }
    }
    private var savings: Decimal { income - expenses }
    private var savingsPercent: Double {
        guard income > 0 else { return 0 }
        return NSDecimalNumber(decimal: savings / income * 100).doubleValue
    }
    private var multipleCurrencies: Bool {
        Set(activeAccounts.map(\.currency)).count > 1 ||
        activeAccounts.contains { $0.currency != supportedCurrency }
    }
    private var hasFreshRates: Bool {
        guard let last = UserDefaults.standard.object(forKey: "exchangeRatesFetchedAt") as? Date else {
            return false
        }
        guard now.timeIntervalSince(last) < 86400 * 2 else { return false }
        let live = UserDefaults.standard.dictionary(forKey: "cachedExchangeRates") as? [String: Double] ?? [:]
        let needed = Set(activeAccounts.map(\.currency)).union([supportedCurrency]).subtracting(["USD"])
        return needed.allSatisfy { live[$0] != nil }
    }
    private var hasBalanceMismatch: Bool {
        activeAccounts.contains { account in
            let expected = account.initialBalance + account.transactions.reduce(Decimal.zero) { $0 + $1.amount }
            return abs(account.currentBalance - expected) >= Decimal(string: "0.01")!
        }
    }

    private var flowPoints: [FinTrackFlowPoint] {
        var result: [FinTrackFlowPoint] = []
        var cursor = periodStart
        let bucket = period.bucket
        while cursor <= now {
            guard let next = calendar.date(byAdding: bucket, value: 1, to: cursor), next > cursor else { break }
            let values = includedTransactions.filter { $0.date >= cursor && $0.date < next }
            let periodIncome = values.filter(\.isIncome).reduce(Decimal.zero) { $0 + converted($1) }
            let periodExpenses = values.filter(\.isExpense).reduce(Decimal.zero) { $0 + abs(converted($1)) }
            result.append(FinTrackFlowPoint(
                date: cursor,
                income: NSDecimalNumber(decimal: periodIncome).doubleValue,
                expense: NSDecimalNumber(decimal: periodExpenses).doubleValue
            ))
            cursor = next
        }
        return result
    }

    private var topCategories: [FinTrackCategoryTotal] {
        let grouped = Dictionary(grouping: includedTransactions.filter(\.isExpense)) { tx in
            tx.category?.id
        }
        return grouped.map { categoryID, values in
            let cat = values.first?.category
            return FinTrackCategoryTotal(
                name: cat?.name ?? "Без категории",
                id: categoryID,
                icon: cat?.icon ?? "square.grid.2x2",
                color: cat.map { Color(hex: $0.colorHex) } ?? .gray,
                amount: values.reduce(Decimal.zero) { $0 + abs(converted($1)) }
            )
        }.sorted { a, b in
            if a.amount != b.amount { return a.amount > b.amount }
            if a.name != b.name { return a.name < b.name }
            return (a.id?.uuidString ?? "") < (b.id?.uuidString ?? "")
        }.prefix(6).map { $0 }
    }
    private var recentTransactions: [Transaction] {
        transactions.filter { $0.account != nil }.prefix(7).map { $0 }
    }
    private var upcomingPayments: [ScheduledTransaction] {
        let limit = calendar.date(byAdding: .day, value: 14, to: now) ?? now
        return scheduled.filter {
            $0.isActive && $0.nextDate <= limit && $0.amount < 0
        }.sorted { $0.nextDate < $1.nextDate }.prefix(4).map { $0 }
    }

    private var tileColor: Color { colorScheme == .dark ? Color.white.opacity(0.055) : .white }
    private var canvasColor: Color {
        colorScheme == .dark ? Color(red: 0.055, green: 0.065, blue: 0.085)
                             : Color(red: 0.945, green: 0.955, blue: 0.974)
    }
    private var accent: Color { Color(red: 0.28, green: 0.65, blue: 0.89) }

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 18) {
                header
                hero
                metrics
                if hasBalanceMismatch { dataIntegrityBanner }
                ViewThatFits(in: .horizontal) {
                    HStack(alignment: .top, spacing: 16) {
                        cashflowCard.frame(maxWidth: .infinity, alignment: .top)
                        categoryCard.frame(maxWidth: .infinity, alignment: .top)
                    }.frame(minWidth: 740)
                    VStack(spacing: 16) { cashflowCard; categoryCard }
                }
                ViewThatFits(in: .horizontal) {
                    HStack(alignment: .top, spacing: 16) {
                        accountCard.frame(maxWidth: .infinity, alignment: .top)
                        recentCard.frame(maxWidth: .infinity, alignment: .top)
                    }.frame(minWidth: 740)
                    VStack(spacing: 16) { accountCard; recentCard }
                }
                if !upcomingPayments.isEmpty { upcomingCard }
            }
            .frame(maxWidth: 1400)
            .padding(24)
            .frame(maxWidth: .infinity)
        }
        .background(canvasColor)
        .navigationTitle("Финансы")
        .animation(.easeInOut(duration: 0.18), value: period)
        .onReceive(NotificationCenter.default.publisher(for: Notification.Name("FinTrackExchangeRatesUpdated"))) { _ in
            fxRevision += 1
        }
    }

    private var header: some View {
        HStack(alignment: .center) {
            VStack(alignment: .leading, spacing: 4) {
                Text("Финансовый обзор")
                    .font(.system(size: 28, weight: .bold, design: .rounded))
                Text(Date.now.formatted(.dateTime.day().month(.wide).year().locale(Locale(identifier: "ru_RU"))))
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
            }
            Spacer(minLength: 12)
            Picker("Валюта", selection: $preferredCurrency) {
                Text("₽ RUB").tag("RUB")
                Text("$ USD").tag("USD")
                Text("€ EUR").tag("EUR")
            }
            .pickerStyle(.menu)
            .frame(width: 125)
            Button(action: { onAddTransaction?() }) {
                Label("Добавить операцию", systemImage: "plus")
                    .fontWeight(.semibold)
            }
            .buttonStyle(.borderedProminent)
            .tint(accent)
            .disabled(activeAccounts.isEmpty)
        }
    }

    private var hero: some View {
        VStack(alignment: .leading, spacing: 18) {
            HStack(alignment: .top) {
                VStack(alignment: .leading, spacing: 9) {
                    Text("МОЙ КАПИТАЛ")
                        .font(.caption.weight(.semibold))
                        .tracking(2)
                        .foregroundStyle(.white.opacity(0.7))
                    Text(format(netWorth))
                        .font(.system(size: 43, weight: .bold, design: .rounded))
                        .monospacedDigit()
                        .minimumScaleFactor(0.6)
                        .lineLimit(1)
                        .foregroundStyle(.white)
                    Label("Баланс всех счетов с учётом долгов", systemImage: "chart.xyaxis.line")
                        .font(.caption)
                        .foregroundStyle(.white.opacity(0.72))
                }
                Spacer(minLength: 10)
                Image(systemName: "chart.pie.fill")
                    .font(.system(size: 35, weight: .light))
                    .foregroundStyle(.white.opacity(0.8))
                    .padding(12)
                    .background(.white.opacity(0.10), in: RoundedRectangle(cornerRadius: 14))
            }
            Divider().overlay(.white.opacity(0.2))
            HStack {
                balanceMini("Активы", amount: totalAssets, symbol: "arrow.up.right")
                Spacer()
                balanceMini("Обязательства", amount: totalLiabilities, symbol: "arrow.down.right")
                Spacer()
                balanceMini("Доходы − расходы", amount: savings, symbol: "equal.circle")
            }
            if multipleCurrencies {
                Label(hasFreshRates
                    ? "Суммы переведены по последнему полученному курсу"
                    : "Курс может быть устаревшим: оценка, не точная стоимость",
                    systemImage: "info.circle")
                    .font(.caption2)
                    .foregroundStyle(.white.opacity(0.76))
            }
        }
        .padding(24)
        .background(
            LinearGradient(colors: [Color(red: 0.12, green: 0.22, blue: 0.37),
                                    Color(red: 0.13, green: 0.40, blue: 0.56),
                                    Color(red: 0.22, green: 0.56, blue: 0.65)],
                           startPoint: .topLeading, endPoint: .bottomTrailing),
            in: RoundedRectangle(cornerRadius: 22)
        )
    }

    private func balanceMini(_ label: String, amount: Decimal, symbol: String) -> some View {
        VStack(alignment: .leading, spacing: 7) {
            Label(label, systemImage: symbol)
                .font(.caption)
                .foregroundStyle(.white.opacity(0.75))
            Text(format(amount))
                .font(.system(size: 18, weight: .semibold, design: .rounded))
                .monospacedDigit()
                .lineLimit(1)
                .minimumScaleFactor(0.65)
                .foregroundStyle(.white)
        }
    }

    private var metrics: some View {
        LazyVGrid(columns: [GridItem(.adaptive(minimum: 200), spacing: 14)], spacing: 14) {
            metric("Доходы", amount: income, note: "За выбранный период", icon: "arrow.down.left", color: .green)
            metric("Расходы", amount: expenses, note: "За выбранный период", icon: "arrow.up.right", color: .red)
            metric("Разница", amount: savings, note: "Доходы минус расходы", icon: "equal", color: accent)
            tile {
                VStack(alignment: .leading, spacing: 12) {
                    Label("Доля сбережений", systemImage: "chart.bar.xaxis")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                    Text(income == 0 ? "—" : String(format: "%.1f%%", savingsPercent))
                        .font(.system(size: 27, weight: .bold, design: .rounded))
                    ProgressView(value: income > 0 ? min(1, max(0, savingsPercent / 100)) : 0)
                        .tint(accent)
                }
            }
        }
    }
    private func metric(_ title: String, amount: Decimal, note: String, icon: String, color: Color) -> some View {
        tile {
            VStack(alignment: .leading, spacing: 12) {
                HStack {
                    Text(title).font(.subheadline).foregroundStyle(.secondary)
                    Spacer()
                    Image(systemName: icon).foregroundStyle(color)
                }
                Text(format(amount))
                    .font(.system(size: 26, weight: .bold, design: .rounded))
                    .monospacedDigit().lineLimit(1).minimumScaleFactor(0.6)
                Text(note).font(.caption2).foregroundStyle(.tertiary)
            }
        }
    }

    private var cashflowCard: some View {
        tile {
            VStack(alignment: .leading, spacing: 14) {
                HStack {
                    VStack(alignment: .leading, spacing: 3) {
                        Text("Денежный поток").font(.headline)
                        Text("Доходы и расходы").font(.caption).foregroundStyle(.secondary)
                    }
                    Spacer()
                    Picker("Период", selection: $period) {
                        ForEach(Period.allCases, id: \.self) { Text($0.rawValue).tag($0) }
                    }
                    .pickerStyle(.menu)
                    .frame(width: 115)
                }
                if includedTransactions.isEmpty {
                    ContentUnavailableView("Нет операций за период", systemImage: "chart.bar",
                        description: Text("Добавьте доход или расход — здесь появится график."))
                        .frame(height: 230)
                } else {
                    Chart(flowPoints) { point in
                        BarMark(x: .value("Дата", point.date, unit: period.bucket),
                                y: .value("Сумма", point.income))
                            .foregroundStyle(by: .value("Тип", "Доходы"))
                            .position(by: .value("Тип", "Доходы"))
                        BarMark(x: .value("Дата", point.date, unit: period.bucket),
                                y: .value("Сумма", point.expense))
                            .foregroundStyle(by: .value("Тип", "Расходы"))
                            .position(by: .value("Тип", "Расходы"))
                    }
                    .chartForegroundStyleScale(["Доходы": Color.green, "Расходы": Color.orange])
                    .chartLegend(position: .bottom, alignment: .leading)
                    .frame(height: 235)
                }
            }
        }
    }

    private var categoryCard: some View {
        tile {
            VStack(alignment: .leading, spacing: 16) {
                HStack {
                    Text("На что уходят деньги").font(.headline)
                    Spacer()
                    Text("Топ категорий").font(.caption).foregroundStyle(.secondary)
                }
                if topCategories.isEmpty {
                    ContentUnavailableView("Нет расходов", systemImage: "tray",
                        description: Text("Категории расходов появятся здесь."))
                        .frame(height: 230)
                } else {
                    ForEach(topCategories) { cat in
                        VStack(spacing: 7) {
                            HStack(spacing: 9) {
                                Image(systemName: cat.icon).foregroundStyle(cat.color)
                                    .frame(width: 20)
                                Text(LocalizedStringKey(cat.name)).font(.subheadline).lineLimit(1)
                                Spacer()
                                Text(format(cat.amount)).font(.subheadline.weight(.semibold)).monospacedDigit()
                            }
                            GeometryReader { geo in
                                Capsule().fill(.secondary.opacity(0.12))
                                    .overlay(alignment: .leading) {
                                        Capsule().fill(cat.color)
                                            .frame(width: max(0, geo.size.width * CGFloat(
                                                NSDecimalNumber(decimal: expenses > 0 ? cat.amount / expenses : 0).doubleValue
                                            )))
                                    }
                            }.frame(height: 6)
                        }
                    }
                    Spacer(minLength: 0)
                }
            }.frame(minHeight: 265, alignment: .top)
        }
    }

    private var accountCard: some View {
        tile {
            VStack(alignment: .leading, spacing: 14) {
                HStack {
                    Text("Мои счета").font(.headline)
                    Spacer()
                    Button { onAddAccount?() } label: {
                        Label("Добавить", systemImage: "plus")
                    }.buttonStyle(.borderless)
                }
                if activeAccounts.isEmpty {
                    ContentUnavailableView("Пока нет счетов", systemImage: "building.columns",
                        description: Text("Создайте первый счёт для учёта финансов."))
                        .frame(height: 150)
                } else {
                    ForEach(activeAccounts.prefix(6)) { account in
                        HStack(spacing: 10) {
                            Image(systemName: account.type.icon)
                                .foregroundStyle(Color(hex: account.colorHex))
                                .frame(width: 34, height: 34)
                                .background(Color(hex: account.colorHex).opacity(0.12),
                                            in: RoundedRectangle(cornerRadius: 10))
                            VStack(alignment: .leading, spacing: 3) {
                                Text(account.name).font(.subheadline.weight(.medium))
                                Text(account.currency).font(.caption2).foregroundStyle(.secondary)
                            }
                            Spacer()
                            Text(CurrencyFormatter.shared.format(account.currentBalance,
                                                                currency: account.currency))
                                .font(.subheadline.weight(.semibold)).monospacedDigit()
                        }
                        if account.id != activeAccounts.prefix(6).last?.id { Divider() }
                    }
                }
            }
        }
    }

    private var recentCard: some View {
        tile {
            VStack(alignment: .leading, spacing: 12) {
                HStack {
                    Text("Последние операции").font(.headline)
                    Spacer()
                    Text("Недавняя активность").font(.caption).foregroundStyle(.secondary)
                }
                if recentTransactions.isEmpty {
                    ContentUnavailableView("Операций пока нет", systemImage: "clock",
                        description: Text("Добавьте операцию, чтобы увидеть историю."))
                        .frame(height: 150)
                } else {
                    ForEach(recentTransactions) { transaction in
                        TransactionRow(transaction: transaction, showAccount: true)
                        if transaction.id != recentTransactions.last?.id { Divider() }
                    }
                }
            }
        }
    }

    private var upcomingCard: some View {
        tile {
            VStack(alignment: .leading, spacing: 12) {
                Text("Ближайшие платежи").font(.headline)
                ForEach(upcomingPayments) { payment in
                    HStack {
                        Image(systemName: "calendar.badge.clock").foregroundStyle(accent)
                        Text(payment.title).font(.subheadline)
                        Spacer()
                        Text(payment.nextDate, format: .dateTime.day().month(.abbreviated))
                            .font(.caption).foregroundStyle(.secondary)
                    }
                }
            }
        }
    }

    private var dataIntegrityBanner: some View {
        HStack(spacing: 12) {
            Image(systemName: "exclamationmark.triangle.fill").foregroundStyle(.orange)
            Text("Обнаружено расхождение остатков по счетам. Проверьте данные перед анализом.")
                .font(.subheadline)
            Spacer()
            Button("Проверить") { onReviewDataHealth?() }
        }
        .padding(15)
        .background(.orange.opacity(0.10), in: RoundedRectangle(cornerRadius: 13))
    }

    private func tile<Content: View>(@ViewBuilder _ content: () -> Content) -> some View {
        content()
            .frame(maxWidth: .infinity, alignment: .topLeading)
            .padding(18)
            .background(tileColor, in: RoundedRectangle(cornerRadius: 18))
            .overlay(RoundedRectangle(cornerRadius: 18)
                .strokeBorder(.primary.opacity(0.045), lineWidth: 1))
    }
}