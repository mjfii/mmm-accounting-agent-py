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

    def write_entries(self, output_path: Optional[Path] = None) -> Path:
        """
        Generate bookkeeping journal entries CSV file.

        Creates entries for dividends and purchases during the period.
        - Dividends: Debit Cash, Credit Income (grouped by date)
        - Purchases: Debit Security accounts, Credit Cash (grouped by date/basket)

        Args:
            output_path: Optional custom path for output file.
                        If None, uses base_path/entries/MMW-YYYY-MM-ENT.csv

        Returns:
            Path to the created CSV file

        Raises:
            ValueError: If income data is not loaded
        """
        if self.income is None:
            raise ValueError("Income data must be loaded before writing entries")

        # Determine output path
        if output_path is None:
            entries_dir = self.base_path / 'entries'
            entries_dir.mkdir(parents=True, exist_ok=True)
            output_path = entries_dir / f"{self.file_prefix}-ENT.csv"
        else:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)

        # Load chart of accounts for symbol mapping
        symbol_map = self._load_chart_of_accounts()

        # Group non-reinvestment income transactions by date
        from collections import defaultdict
        income_by_date = defaultdict(list)

        for txn in self.income:
            if not txn.is_reinvestment:
                income_by_date[txn.settlement_date].append(txn)

        # Group purchase transactions by date and basket (exclude money market funds)
        money_market_symbols = {'FDRXX', 'SPAXX', 'FCASH'}
        purchases_by_date_basket = defaultdict(list)
        if self.activity is not None:
            for txn in self.activity:
                if 'Bought' in txn.action and txn.symbol not in money_market_symbols:
                    key = (txn.settlement_date, txn.basket or '')
                    purchases_by_date_basket[key].append(txn)

        # Generate entries
        import csv
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            fieldnames = [
                'Journal Date', 'Reference Number', 'Journal Number Prefix',
                'Journal Number Suffix', 'Notes', 'Journal Type', 'Currency',
                'Account', 'Description', 'Contact Name', 'Debit', 'Credit',
                'Project Name', 'Status', 'Exchange Rate'
            ]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            journal_number = 10001

            # Write dividend entries
            for settlement_date in sorted(income_by_date.keys()):
                txns = income_by_date[settlement_date]

                # Create reference number and notes
                ref_number = f"DIV-{settlement_date}"
                symbols = ', '.join(sorted(set(t.symbol for t in txns)))
                notes = f"{settlement_date} Dividends - {symbols}"

                # Calculate total for this date
                total_amount = sum(t.amount for t in txns)

                # Write debit entries (one per transaction - Cash account)
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

                # Write single credit entry (Income account)
                writer.writerow({
                    'Journal Date': str(settlement_date),
                    'Reference Number': ref_number,
                    'Journal Number Prefix': 'MMW-',
                    'Journal Number Suffix': str(journal_number),
                    'Notes': notes,
                    'Journal Type': 'both',
                    'Currency': 'USD',
                    'Account': 'Income - Ordinary Dividend',
                    'Description': f"Income - {symbols}",
                    'Contact Name': '',
                    'Debit': '',
                    'Credit': f"{total_amount:.2f}",
                    'Project Name': '',
                    'Status': 'published',
                    'Exchange Rate': ''
                })

                journal_number += 1

            # Write purchase entries
            journal_number = 20001

            for (settlement_date, basket), txns in sorted(purchases_by_date_basket.items()):
                # Create reference number
                basket_suffix = f"-{basket}" if basket else ""
                ref_number = f"PUR-{settlement_date}{basket_suffix}"

                # Create notes with symbols
                symbols = ', '.join(sorted(set(t.symbol for t in txns)))
                notes = f"{settlement_date} Purchase - {symbols}"

                # Calculate total amount
                total_amount = sum(t.amount for t in txns)

                # Write debit entries (one per security - Asset accounts)
                for txn in txns:
                    # Get full account name from chart of accounts
                    account_name = symbol_map.get(txn.symbol, txn.symbol)

                    # Create description with quantity and price
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

                # Write single credit entry (Cash account)
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
