"""Statement class for managing all scrape data for a single statement period."""

from pathlib import Path
from typing import Optional

from .holdings import Holdings
from .income import Income
from .activity import Activity
from .summary import Summary


class Statement:
    """
    Manages all scrape data for a single statement period.

    This class loads and holds Holdings, Income, Activity, and Summary data
    for a specific month/year period.
    """

    def __init__(
        self,
        year: int,
        month: int,
        base_path: Optional[Path] = None,
        auto_load: bool = True
    ):
        """
        Initialize Statement for a specific month and year.

        Args:
            year: Statement year (e.g., 2025)
            month: Statement month (1-12)
            base_path: Base directory path for the project (defaults to current working directory)
            auto_load: If True, automatically load all CSV files on initialization

        Raises:
            ValueError: If month is not between 1 and 12
        """
        if not 1 <= month <= 12:
            raise ValueError(f"Month must be between 1 and 12, got {month}")

        self.year = year
        self.month = month
        self.base_path = Path(base_path) if base_path else Path.cwd()

        # Initialize data containers
        self.holdings: Optional[Holdings] = None
        self.income: Optional[Income] = None
        self.activity: Optional[Activity] = None
        self.summary: Optional[Summary] = None

        if auto_load:
            self.load_all()

    @property
    def period_string(self) -> str:
        """Get the period string in YYYY-MM format."""
        return f"{self.year}-{self.month:02d}"

    @property
    def file_prefix(self) -> str:
        """Get the file prefix for this period (MMW-YYYY-MM)."""
        return f"MMW-{self.year}-{self.month:02d}"

    def _get_scrape_path(self, scrape_type: str) -> Path:
        """
        Get the path to a scrape CSV file.

        Args:
            scrape_type: Type of scrape (HLD, INC, ACT, SUM)

        Returns:
            Path to the CSV file
        """
        scrape_dirs = {
            'HLD': 'holdings',
            'INC': 'income',
            'ACT': 'activity',
            'SUM': 'summary'
        }

        if scrape_type not in scrape_dirs:
            raise ValueError(f"Invalid scrape type: {scrape_type}")

        scrape_dir = scrape_dirs[scrape_type]
        return self.base_path / 'scrapes' / scrape_dir / str(self.year) / f"{self.file_prefix}-{scrape_type}.csv"

    def load_holdings(self) -> None:
        """Load holdings data from HLD CSV file."""
        csv_path = self._get_scrape_path('HLD')
        self.holdings = Holdings(csv_path)

    def load_income(self) -> None:
        """Load income data from INC CSV file."""
        csv_path = self._get_scrape_path('INC')
        self.income = Income(csv_path)

    def load_activity(self) -> None:
        """Load activity data from ACT CSV file."""
        csv_path = self._get_scrape_path('ACT')
        self.activity = Activity(csv_path)

    def load_summary(self) -> None:
        """Load summary data from SUM CSV file."""
        csv_path = self._get_scrape_path('SUM')
        self.summary = Summary.from_csv_file(csv_path)

    def load_all(self) -> None:
        """
        Load all scrape data files.

        Attempts to load all four scrape types. If any file is missing,
        that data type will remain None.
        """
        try:
            self.load_holdings()
        except FileNotFoundError:
            pass

        try:
            self.load_income()
        except FileNotFoundError:
            pass

        try:
            self.load_activity()
        except FileNotFoundError:
            pass

        try:
            self.load_summary()
        except FileNotFoundError:
            pass

    @property
    def is_validated(self) -> bool:
        """
        Validate that the accounting equation balances.

        Checks: change_investment_value_period == Income.amount + Holdings.change_in_value

        Returns:
            True if validation passes, False otherwise (or if required data is missing)
        """
        if self.summary is None or self.income is None or self.holdings is None:
            return False

        expected = self.summary.change_investment_value_period
        actual = self.income.amount + self.holdings.change_in_value

        # Use a small tolerance for floating point comparison
        return abs(expected - actual) < 0.01

    def _load_chart_of_accounts(self) -> dict:
        """
        Load chart of accounts to map symbols to full account names.

        Returns:
            Dictionary mapping symbol to account name
        """
        import csv
        chart_path = self.base_path / 'books' / 'chart_of_accounts.csv'
        symbol_map = {}

        if not chart_path.exists():
            return symbol_map

        with open(chart_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                account_name = row['Account Name']
                # Extract symbol from account name (e.g., "Symbol (TICKER)")
                if '(' in account_name and ')' in account_name:
                    start = account_name.rfind('(')
                    end = account_name.rfind(')')
                    symbol = account_name[start+1:end]
                    symbol_map[symbol] = account_name

        return symbol_map

    def _get_entry_path(self, entry_type: str) -> Path:
        """Get the path for an entry file."""
        entry_dirs = {
            'DIV': 'dividends',
            'PUR': 'purchases',
            'SAL': 'sales',
            'UNR': 'unrealized',
        }
        entry_dir = entry_dirs.get(entry_type, entry_type.lower())
        return self.base_path / 'entries' / entry_dir / str(self.year) / f"{self.file_prefix}-{entry_type}.csv"

    def _get_fieldnames(self) -> list:
        """Get the standard fieldnames for journal entries."""
        return [
            'Journal Date', 'Reference Number', 'Journal Number Prefix',
            'Journal Number Suffix', 'Notes', 'Journal Type', 'Currency',
            'Account', 'Description', 'Contact Name', 'Debit', 'Credit',
            'Project Name', 'Status', 'Exchange Rate'
        ]

    def write_dividend_entries(self) -> Optional[Path]:
        """Write dividend entries to DIV file. Journal suffix starts at 10001."""
        if self.income is None:
            return None

        from collections import defaultdict
        import csv

        # Group non-reinvestment income transactions by date
        income_by_date = defaultdict(list)
        for txn in self.income:
            if not txn.is_reinvestment:
                income_by_date[txn.settlement_date].append(txn)

        if not income_by_date:
            return None

        output_path = self._get_entry_path('DIV')
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=self._get_fieldnames())
            writer.writeheader()

            journal_number = 10001

            for settlement_date in sorted(income_by_date.keys()):
                txns = income_by_date[settlement_date]
                ref_number = f"DIV-{settlement_date}"
                symbols = ', '.join(sorted(set(t.symbol for t in txns)))
                notes = f"{settlement_date} Dividends - {symbols}"
                total_amount = sum(t.amount for t in txns)

                for txn in txns:
                    writer.writerow({
                        'Journal Date': str(settlement_date),
                        'Reference Number': ref_number,
                        'Journal Number Prefix': 'MMW-',
                        'Journal Number Suffix': str(journal_number),
                        'Notes': notes,
                        'Journal Type': 'both',
                        'Currency': 'USD',
                        'Account': 'Cash - Fidelity Cash Management Account',
                        'Description': f"Dividend - {txn.symbol}",
                        'Contact Name': '',
                        'Debit': f"{txn.amount:.2f}",
                        'Credit': '',
                        'Project Name': '',
                        'Status': 'published',
                        'Exchange Rate': ''
                    })

                writer.writerow({
                    'Journal Date': str(settlement_date),
                    'Reference Number': ref_number,
                    'Journal Number Prefix': 'MMW-',
                    'Journal Number Suffix': str(journal_number),
                    'Notes': notes,
                    'Journal Type': 'both',
                    'Currency': 'USD',
                    'Account': 'Income - Ordinary Dividends',
                    'Description': f"Income - {symbols}",
                    'Contact Name': '',
                    'Debit': '',
                    'Credit': f"{total_amount:.2f}",
                    'Project Name': '',
                    'Status': 'published',
                    'Exchange Rate': ''
                })

                journal_number += 1

        return output_path

    def write_purchase_entries(self) -> Optional[Path]:
        """Write purchase entries to PUR file. Journal suffix starts at 20001."""
        if self.activity is None:
            return None

        from collections import defaultdict
        import csv

        money_market_symbols = {'FDRXX', 'SPAXX', 'FCASH'}
        purchases_by_date_basket = defaultdict(list)

        for txn in self.activity:
            if 'Bought' in txn.action and txn.symbol not in money_market_symbols:
                key = (txn.settlement_date, txn.basket or '')
                purchases_by_date_basket[key].append(txn)

        if not purchases_by_date_basket:
            return None

        output_path = self._get_entry_path('PUR')
        output_path.parent.mkdir(parents=True, exist_ok=True)
        symbol_map = self._load_chart_of_accounts()

        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=self._get_fieldnames())
            writer.writeheader()

            journal_number = 20001

            for (settlement_date, basket), txns in sorted(purchases_by_date_basket.items()):
                basket_suffix = f"-{basket}" if basket else ""
                ref_number = f"PUR-{settlement_date}{basket_suffix}"
                symbols = ', '.join(sorted(set(t.symbol for t in txns)))
                notes = f"{settlement_date} Purchase - {symbols}"
                total_amount = sum(t.amount for t in txns)

                for txn in txns:
                    account_name = symbol_map.get(txn.symbol, txn.symbol)
                    if txn.quantity and txn.price:
                        description = f"Purchase - {txn.symbol} - {txn.quantity:.3f} @ ~ ${txn.price:.2f}"
                    else:
                        description = f"Purchase - {txn.symbol}"

                    writer.writerow({
                        'Journal Date': str(settlement_date),
                        'Reference Number': ref_number,
                        'Journal Number Prefix': 'MMW-',
                        'Journal Number Suffix': str(journal_number),
                        'Notes': notes,
                        'Journal Type': 'both',
                        'Currency': 'USD',
                        'Account': account_name,
                        'Description': description,
                        'Contact Name': '',
                        'Debit': f"{txn.amount:.2f}",
                        'Credit': '',
                        'Project Name': '',
                        'Status': 'published',
                        'Exchange Rate': ''
                    })

                writer.writerow({
                    'Journal Date': str(settlement_date),
                    'Reference Number': ref_number,
                    'Journal Number Prefix': 'MMW-',
                    'Journal Number Suffix': str(journal_number),
                    'Notes': notes,
                    'Journal Type': 'both',
                    'Currency': 'USD',
                    'Account': 'Cash - Fidelity Cash Management Account',
                    'Description': f"Cash for {symbols}",
                    'Contact Name': '',
                    'Debit': '',
                    'Credit': f"{total_amount:.2f}",
                    'Project Name': '',
                    'Status': 'published',
                    'Exchange Rate': ''
                })

                journal_number += 1

        return output_path

    def write_sale_entries(self) -> Optional[Path]:
        """Write sale entries to SAL file. Journal suffix starts at 30001."""
        if self.activity is None:
            return None

        from collections import defaultdict
        import csv

        money_market_symbols = {'FDRXX', 'SPAXX', 'FCASH'}
        sales_by_date_basket = defaultdict(list)

        # Basket config for realized gains/losses income account
        basket_income_accounts = {
            '10001': ('Water Investments', 'Income - Equity Securities Baskets - Water Investments'),
            '10003': ('Buy Write ETFs', 'Income - Equity Securities Baskets - Buy Write ETFs'),
            '10005': ('Holding Companies', 'Income - Equity Securities Baskets - Holding Companies'),
            '10007': ('Balanced ETFs', 'Income - Equity Securities Baskets - Balanced ETFs'),
        }

        for txn in self.activity:
            if 'Sold' in txn.action and txn.symbol not in money_market_symbols:
                key = (txn.settlement_date, txn.basket or '')
                sales_by_date_basket[key].append(txn)

        if not sales_by_date_basket:
            return None

        output_path = self._get_entry_path('SAL')
        output_path.parent.mkdir(parents=True, exist_ok=True)
        symbol_map = self._load_chart_of_accounts()

        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=self._get_fieldnames())
            writer.writeheader()

            journal_number = 30001

            for (settlement_date, basket), txns in sorted(sales_by_date_basket.items()):
                basket_suffix = f"-{basket}" if basket else ""
                basket_name, income_account = basket_income_accounts.get(basket, ('', 'Income - Equity Securities'))

                ref_number = f"SAL-{settlement_date}{basket_suffix}"
                symbols = ', '.join(sorted(set(t.symbol for t in txns)))

                if basket_name:
                    notes = f"{settlement_date} Sale - {basket_name} - {symbols}"
                else:
                    notes = f"{settlement_date} Sale - {symbols}"

                total_proceeds = sum(t.amount for t in txns)
                total_cost_basis = sum(t.cost_basis for t in txns if t.cost_basis)

                # Group transactions by symbol for consolidated entries
                symbol_totals = defaultdict(lambda: {'proceeds': 0.0, 'cost_basis': 0.0, 'quantity': 0.0})
                for txn in txns:
                    symbol_totals[txn.symbol]['proceeds'] += txn.amount
                    symbol_totals[txn.symbol]['cost_basis'] += txn.cost_basis if txn.cost_basis else txn.amount
                    symbol_totals[txn.symbol]['quantity'] += txn.quantity if txn.quantity else 0

                # 1. Debit cash account for total proceeds
                writer.writerow({
                    'Journal Date': str(settlement_date),
                    'Reference Number': ref_number,
                    'Journal Number Prefix': 'MMW-',
                    'Journal Number Suffix': str(journal_number),
                    'Notes': notes,
                    'Journal Type': 'both',
                    'Currency': 'USD',
                    'Account': 'Cash - Fidelity Cash Management Account',
                    'Description': f"Proceeds from {basket_name + ' - ' if basket_name else ''}{symbols}",
                    'Contact Name': '',
                    'Debit': f"{total_proceeds:.2f}",
                    'Credit': '',
                    'Project Name': '',
                    'Status': 'published',
                    'Exchange Rate': ''
                })

                # 2. Record realized gains/losses per symbol
                for symbol in sorted(symbol_totals.keys()):
                    totals = symbol_totals[symbol]
                    proceeds = totals['proceeds']
                    cost_basis = totals['cost_basis']
                    gain_loss = proceeds - cost_basis

                    if abs(gain_loss) >= 0.01:  # Only record if material
                        if gain_loss < 0:
                            # Realized loss - debit income account
                            writer.writerow({
                                'Journal Date': str(settlement_date),
                                'Reference Number': ref_number,
                                'Journal Number Prefix': 'MMW-',
                                'Journal Number Suffix': str(journal_number),
                                'Notes': notes,
                                'Journal Type': 'both',
                                'Currency': 'USD',
                                'Account': income_account,
                                'Description': f"Realized Loss - {symbol}",
                                'Contact Name': '',
                                'Debit': f"{abs(gain_loss):.2f}",
                                'Credit': '',
                                'Project Name': '',
                                'Status': 'published',
                                'Exchange Rate': ''
                            })
                        else:
                            # Realized gain - credit income account
                            writer.writerow({
                                'Journal Date': str(settlement_date),
                                'Reference Number': ref_number,
                                'Journal Number Prefix': 'MMW-',
                                'Journal Number Suffix': str(journal_number),
                                'Notes': notes,
                                'Journal Type': 'both',
                                'Currency': 'USD',
                                'Account': income_account,
                                'Description': f"Realized Gain - {symbol}",
                                'Contact Name': '',
                                'Debit': '',
                                'Credit': f"{gain_loss:.2f}",
                                'Project Name': '',
                                'Status': 'published',
                                'Exchange Rate': ''
                            })

                # 3. Credit security accounts with cost basis (reducing asset)
                for symbol in sorted(symbol_totals.keys()):
                    totals = symbol_totals[symbol]
                    cost_basis = totals['cost_basis']
                    quantity = totals['quantity']
                    account_name = symbol_map.get(symbol, symbol)

                    # Calculate average price for description
                    avg_price = totals['proceeds'] / quantity if quantity else 0
                    description = f"Sale - {symbol} - {quantity:.3f} @ ~ ${avg_price:.2f}"

                    writer.writerow({
                        'Journal Date': str(settlement_date),
                        'Reference Number': ref_number,
                        'Journal Number Prefix': 'MMW-',
                        'Journal Number Suffix': str(journal_number),
                        'Notes': notes,
                        'Journal Type': 'both',
                        'Currency': 'USD',
                        'Account': account_name,
                        'Description': description,
                        'Contact Name': '',
                        'Debit': '',
                        'Credit': f"{cost_basis:.2f}",
                        'Project Name': '',
                        'Status': 'published',
                        'Exchange Rate': ''
                    })

                journal_number += 1

        return output_path

    def _load_prior_holdings(self) -> dict:
        """
        Load prior month's holdings to get beginning values for sold securities.

        Returns:
            Dictionary mapping symbol to prior month's ending_value
        """
        prior_month = self.month - 1 if self.month > 1 else 12
        prior_year = self.year if self.month > 1 else self.year - 1
        prior_holdings_path = self.base_path / 'scrapes' / 'holdings' / str(prior_year) / f"MMW-{prior_year}-{prior_month:02d}-HLD.csv"

        prior_values = {}
        if prior_holdings_path.exists():
            prior_holdings = Holdings(prior_holdings_path)
            for h in prior_holdings:
                if h.ending_value is not None:
                    prior_values[h.symbol] = h.ending_value

        return prior_values

    def write_unrealized_entries(self) -> Optional[Path]:
        """Write unrealized (mark-to-market) entries to UNR file. Journal suffix starts at 40001."""
        if self.holdings is None or self.summary is None:
            return None

        from collections import defaultdict
        import csv

        # Basket configuration: symbol -> (basket_id, basket_name, fmv_account, unrealized_account)
        basket_config = {
            'CWCO': ('10001', 'Water Investments', 'Trading Securities - Water Basket - FMV Adjustment', 'Unrealized Gain - Equity Baskets - Water Investments'),
            'ALCO': ('10001', 'Water Investments', 'Trading Securities - Water Basket - FMV Adjustment', 'Unrealized Gain - Equity Baskets - Water Investments'),
            'AWK': ('10001', 'Water Investments', 'Trading Securities - Water Basket - FMV Adjustment', 'Unrealized Gain - Equity Baskets - Water Investments'),
            'CWT': ('10001', 'Water Investments', 'Trading Securities - Water Basket - FMV Adjustment', 'Unrealized Gain - Equity Baskets - Water Investments'),
            'ECL': ('10001', 'Water Investments', 'Trading Securities - Water Basket - FMV Adjustment', 'Unrealized Gain - Equity Baskets - Water Investments'),
            'FPI': ('10001', 'Water Investments', 'Trading Securities - Water Basket - FMV Adjustment', 'Unrealized Gain - Equity Baskets - Water Investments'),
            'FERG': ('10001', 'Water Investments', 'Trading Securities - Water Basket - FMV Adjustment', 'Unrealized Gain - Equity Baskets - Water Investments'),
            'LAND': ('10001', 'Water Investments', 'Trading Securities - Water Basket - FMV Adjustment', 'Unrealized Gain - Equity Baskets - Water Investments'),
            'GWRS': ('10001', 'Water Investments', 'Trading Securities - Water Basket - FMV Adjustment', 'Unrealized Gain - Equity Baskets - Water Investments'),
            'VEGI': ('10001', 'Water Investments', 'Trading Securities - Water Basket - FMV Adjustment', 'Unrealized Gain - Equity Baskets - Water Investments'),
            'WAT': ('10001', 'Water Investments', 'Trading Securities - Water Basket - FMV Adjustment', 'Unrealized Gain - Equity Baskets - Water Investments'),
            'XYL': ('10001', 'Water Investments', 'Trading Securities - Water Basket - FMV Adjustment', 'Unrealized Gain - Equity Baskets - Water Investments'),
            'JEPI': ('10003', 'Buy Write ETFs', 'Trading Securities - Buy-Write ETFs - FMV Adjustment', 'Unrealized Gain - Equity Baskets - Buy Write ETFs'),
            'QYLD': ('10003', 'Buy Write ETFs', 'Trading Securities - Buy-Write ETFs - FMV Adjustment', 'Unrealized Gain - Equity Baskets - Buy Write ETFs'),
            'SPYI': ('10003', 'Buy Write ETFs', 'Trading Securities - Buy-Write ETFs - FMV Adjustment', 'Unrealized Gain - Equity Baskets - Buy Write ETFs'),
            'TLTW': ('10003', 'Buy Write ETFs', 'Trading Securities - Buy-Write ETFs - FMV Adjustment', 'Unrealized Gain - Equity Baskets - Buy Write ETFs'),
            'XYLD': ('10003', 'Buy Write ETFs', 'Trading Securities - Buy-Write ETFs - FMV Adjustment', 'Unrealized Gain - Equity Baskets - Buy Write ETFs'),
            'RYLD': ('10003', 'Buy Write ETFs', 'Trading Securities - Buy-Write ETFs - FMV Adjustment', 'Unrealized Gain - Equity Baskets - Buy Write ETFs'),
            'MUST': ('10003', 'Buy Write ETFs', 'Trading Securities - Buy-Write ETFs - FMV Adjustment', 'Unrealized Gain - Equity Baskets - Buy Write ETFs'),
            'APO': ('10005', 'Holding Companies', 'Trading Securities - Holding Companies - FMV Adjustment', 'Unrealized Gain - Equity Baskets - Holding Companies'),
            'BRKB': ('10005', 'Holding Companies', 'Trading Securities - Holding Companies - FMV Adjustment', 'Unrealized Gain - Equity Baskets - Holding Companies'),
            'BX': ('10005', 'Holding Companies', 'Trading Securities - Holding Companies - FMV Adjustment', 'Unrealized Gain - Equity Baskets - Holding Companies'),
            'KKR': ('10005', 'Holding Companies', 'Trading Securities - Holding Companies - FMV Adjustment', 'Unrealized Gain - Equity Baskets - Holding Companies'),
            'L': ('10005', 'Holding Companies', 'Trading Securities - Holding Companies - FMV Adjustment', 'Unrealized Gain - Equity Baskets - Holding Companies'),
            'TPG': ('10005', 'Holding Companies', 'Trading Securities - Holding Companies - FMV Adjustment', 'Unrealized Gain - Equity Baskets - Holding Companies'),
            'FDEM': ('10007', 'Balanced ETFs', 'Trading Securities - Balanced ETFs - FMV Adjustment', 'Unrealized Gain - Equity Baskets - Balanced ETFs'),
            'FDEV': ('10007', 'Balanced ETFs', 'Trading Securities - Balanced ETFs - FMV Adjustment', 'Unrealized Gain - Equity Baskets - Balanced ETFs'),
            'FELC': ('10007', 'Balanced ETFs', 'Trading Securities - Balanced ETFs - FMV Adjustment', 'Unrealized Gain - Equity Baskets - Balanced ETFs'),
            'FESM': ('10007', 'Balanced ETFs', 'Trading Securities - Balanced ETFs - FMV Adjustment', 'Unrealized Gain - Equity Baskets - Balanced ETFs'),
            'FMDE': ('10007', 'Balanced ETFs', 'Trading Securities - Balanced ETFs - FMV Adjustment', 'Unrealized Gain - Equity Baskets - Balanced ETFs'),
            'ONEQ': ('10007', 'Balanced ETFs', 'Trading Securities - Balanced ETFs - FMV Adjustment', 'Unrealized Gain - Equity Baskets - Balanced ETFs'),
        }

        # Calculate change_in_value by basket
        basket_totals = defaultdict(float)
        basket_info = {}
        for holding in self.holdings:
            if holding.is_money_market:
                continue
            if holding.symbol in basket_config:
                basket_id, name, fmv_acct, unr_acct = basket_config[holding.symbol]
                basket_totals[basket_id] += holding.change_in_value
                basket_info[basket_id] = (name, fmv_acct, unr_acct)

        # Adjust for purchases and sales during the period
        # Only adjust for holdings that have a beginning_value (existing positions).
        # New positions (no beginning_value) use ending - cost_basis which already
        # excludes purchase amounts, so no adjustment needed for those.
        holdings_with_beginning = {h.symbol for h in self.holdings if h.beginning_value is not None and h.beginning_value > 0}

        if self.activity is not None:
            for txn in self.activity:
                if txn.symbol in basket_config and txn.symbol in holdings_with_beginning:
                    basket_id = basket_config[txn.symbol][0]
                    if 'Bought' in txn.action:
                        basket_totals[basket_id] -= txn.amount
                    elif 'Sold' in txn.action:
                        basket_totals[basket_id] += txn.amount

        # Include period gains/losses for completely sold securities
        # These securities are not in current holdings but had value at beginning of period
        current_symbols = {h.symbol for h in self.holdings}
        prior_values = self._load_prior_holdings()

        if self.activity is not None:
            # Aggregate sale proceeds by symbol for completely sold securities
            sold_proceeds = defaultdict(float)
            for txn in self.activity:
                if 'Sold' in txn.action and txn.symbol in basket_config and txn.symbol not in current_symbols:
                    sold_proceeds[txn.symbol] += txn.amount

            # Calculate period change for each sold security
            for symbol, proceeds in sold_proceeds.items():
                if symbol in prior_values:
                    beginning_value = prior_values[symbol]
                    period_change = proceeds - beginning_value
                    basket_id, name, fmv_acct, unr_acct = basket_config[symbol]
                    basket_totals[basket_id] += period_change
                    if basket_id not in basket_info:
                        basket_info[basket_id] = (name, fmv_acct, unr_acct)

        if not basket_totals:
            return None

        output_path = self._get_entry_path('UNR')
        output_path.parent.mkdir(parents=True, exist_ok=True)
        period_end = self.summary.period_end

        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=self._get_fieldnames())
            writer.writeheader()

            journal_number = 40001

            for basket_id in sorted(basket_totals.keys()):
                change = basket_totals[basket_id]
                if abs(change) < 0.01:
                    continue

                name, fmv_acct, unr_acct = basket_info[basket_id]
                ref_number = f"UNR-{period_end}-{basket_id}"
                notes = f"{period_end} Mark-to-Market - {name}"
                amount = abs(round(change, 2))

                if change > 0:
                    # Gain: Debit FMV Adjustment, Credit Unrealized Gain
                    writer.writerow({
                        'Journal Date': str(period_end),
                        'Reference Number': ref_number,
                        'Journal Number Prefix': 'MMW-',
                        'Journal Number Suffix': str(journal_number),
                        'Notes': notes,
                        'Journal Type': 'both',
                        'Currency': 'USD',
                        'Account': fmv_acct,
                        'Description': f"FMV Adjustment - {name}",
                        'Contact Name': '',
                        'Debit': f"{amount:.2f}",
                        'Credit': '',
                        'Project Name': '',
                        'Status': 'published',
                        'Exchange Rate': ''
                    })
                    writer.writerow({
                        'Journal Date': str(period_end),
                        'Reference Number': ref_number,
                        'Journal Number Prefix': 'MMW-',
                        'Journal Number Suffix': str(journal_number),
                        'Notes': notes,
                        'Journal Type': 'both',
                        'Currency': 'USD',
                        'Account': unr_acct,
                        'Description': f"Unrealized Gain - {name}",
                        'Contact Name': '',
                        'Debit': '',
                        'Credit': f"{amount:.2f}",
                        'Project Name': '',
                        'Status': 'published',
                        'Exchange Rate': ''
                    })
                else:
                    # Loss: Debit Unrealized Gain, Credit FMV Adjustment
                    writer.writerow({
                        'Journal Date': str(period_end),
                        'Reference Number': ref_number,
                        'Journal Number Prefix': 'MMW-',
                        'Journal Number Suffix': str(journal_number),
                        'Notes': notes,
                        'Journal Type': 'both',
                        'Currency': 'USD',
                        'Account': unr_acct,
                        'Description': f"Unrealized Loss - {name}",
                        'Contact Name': '',
                        'Debit': f"{amount:.2f}",
                        'Credit': '',
                        'Project Name': '',
                        'Status': 'published',
                        'Exchange Rate': ''
                    })
                    writer.writerow({
                        'Journal Date': str(period_end),
                        'Reference Number': ref_number,
                        'Journal Number Prefix': 'MMW-',
                        'Journal Number Suffix': str(journal_number),
                        'Notes': notes,
                        'Journal Type': 'both',
                        'Currency': 'USD',
                        'Account': fmv_acct,
                        'Description': f"FMV Adjustment - {name}",
                        'Contact Name': '',
                        'Debit': '',
                        'Credit': f"{amount:.2f}",
                        'Project Name': '',
                        'Status': 'published',
                        'Exchange Rate': ''
                    })

                journal_number += 1

        return output_path

    def write_entries(self) -> Path:
        """
        Generate all entry files and combine into ENT file.

        Writes:
        - DIV file (dividends, journal suffix 10001+)
        - PUR file (purchases, journal suffix 20001+)
        - SAL file (sales, journal suffix 30001+)
        - UNR file (unrealized, journal suffix 40001+)
        - ENT file (union of all above)

        Returns:
            Path to the ENT file
        """
        import csv

        # Write individual entry files
        self.write_dividend_entries()
        self.write_purchase_entries()
        self.write_sale_entries()
        self.write_unrealized_entries()

        # Combine all entry files into ENT
        output_path = self.base_path / 'entries' / f"{self.file_prefix}-ENT.csv"
        output_path.parent.mkdir(parents=True, exist_ok=True)

        entry_types = ['DIV', 'PUR', 'SAL', 'UNR']

        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=self._get_fieldnames())
            writer.writeheader()

            for entry_type in entry_types:
                entry_path = self._get_entry_path(entry_type)
                if entry_path.exists():
                    with open(entry_path, 'r', encoding='utf-8') as entry_file:
                        reader = csv.DictReader(entry_file)
                        for row in reader:
                            writer.writerow(row)

        return output_path

    def __repr__(self) -> str:
        """String representation of Statement."""
        loaded = []
        if self.holdings is not None:
            loaded.append('holdings')
        if self.income is not None:
            loaded.append('income')
        if self.activity is not None:
            loaded.append('activity')
        if self.summary is not None:
            loaded.append('summary')

        loaded_str = ', '.join(loaded) if loaded else 'none'
        return f"Statement(period={self.period_string}, loaded={loaded_str})"
