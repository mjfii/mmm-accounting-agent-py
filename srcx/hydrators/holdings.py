import csv
from csv import DictReader
from datetime import date
from pathlib import Path
from typing import Iterator, Optional, Union
from srcx.common.file_location import FileLocation
from srcx.datasets.holding_position import HoldingPosition
from srcx.datasets.journal_entry import JournalEntry
from srcx.common.journal_writer import write_journal_entries
from srcx.common.log_writer import write_log
from collections import defaultdict


MONEY_MARKET_SYMBOLS = {'FDRXX', 'SPAXX', 'FCASH'}

# Symbol to basket mapping
SYMBOL_TO_BASKET = {
    # 10001 - Water Stocks Basket (12 symbols)
    'ALCO': '10001', 'AWK': '10001', 'CWCO': '10001', 'CWT': '10001',
    'ECL': '10001', 'FERG': '10001', 'FPI': '10001', 'GWRS': '10001',
    'LAND': '10001', 'VEGI': '10001', 'WAT': '10001', 'XYL': '10001',
    # 10003 - Buy Write ETFs (7 symbols)
    'JEPI': '10003', 'MUST': '10003', 'QYLD': '10003', 'RYLD': '10003',
    'SPYI': '10003', 'TLTW': '10003', 'XYLD': '10003',
    # 10005 - Holding Companies (6 symbols)
    'APO': '10005', 'BRKB': '10005', 'BX': '10005',
    'KKR': '10005', 'L': '10005', 'TPG': '10005',
    # 10007 - Balanced ETFs (6 symbols)
    'FDEM': '10007', 'FDEV': '10007', 'FELC': '10007',
    'FESM': '10007', 'FMDE': '10007', 'ONEQ': '10007',
}

# Basket configuration: (name, fmv_adjustment_account, unrealized_gain_account)
BASKET_ACCOUNTS = {
    '10001': (
        'Water Investments',
        'Trading Securities - Water Basket - FMV Adjustment',
        'Unrealized Gain - Equity Baskets - Water Investments'
    ),
    '10003': (
        'Buy Write ETFs',
        'Trading Securities - Buy-Write ETFs - FMV Adjustment',
        'Unrealized Gain - Equity Baskets - Buy Write ETFs'
    ),
    '10005': (
        'Holding Companies',
        'Trading Securities - Holding Companies - FMV Adjustment',
        'Unrealized Gain - Equity Baskets - Holding Companies'
    ),
    '10007': (
        'Balanced ETFs',
        'Trading Securities - Balanced ETFs - FMV Adjustment',
        'Unrealized Gain - Equity Baskets - Balanced ETFs'
    ),
}


class Holdings(object):
    """
    Represents holdings data for a statement period.

    Hydrates from an HLD CSV file which contains multiple records
    representing investment positions at period end.

    Generates mark-to-market (unrealized gain/loss) journal entries
    grouped by basket.
    """
    def __init__(self, file_location: FileLocation) -> None:
        """
        Initialize Holdings for a specific month and year.
        """
        self._file_location = file_location
        self._entries: list[HoldingPosition] = []
        self._purchases_by_symbol: dict[str, float] = defaultdict(float)
        self._load_holdings(self._file_location.holdings_file)
        self._load_activity(self._file_location.activity_file)

    def _load_holdings(self, csv_path: Path) -> None:
        """Load holdings data from CSV file."""
        if not csv_path.exists():
            raise FileNotFoundError(f"CSV file not found: {csv_path}")

        with open(csv_path, 'r', encoding='utf-8') as f:
            reader: DictReader[str] = csv.DictReader(f)
            for row in reader:
                if not any(row.values()):
                    continue

                entry = HoldingPosition(
                    symbol=row['symbol'],
                    description=row['description'],
                    quantity=float(row['quantity']),
                    price=float(row['price']),
                    beginning_value=float(row['beginning_value']) if row.get('beginning_value') else None,
                    ending_value=float(row['ending_value']),
                    cost_basis=float(row['cost_basis']) if row.get('cost_basis') else None,
                    unrealized_gain=float(row['unrealized_gain']) if row.get('unrealized_gain') else None,
                )
                self._entries.append(entry)

    def _load_activity(self, csv_path: Path) -> None:
        """Load activity data to get purchases during the period."""
        if not csv_path.exists():
            # No activity file means no purchases to account for
            return

        with open(csv_path, 'r', encoding='utf-8') as f:
            reader: DictReader[str] = csv.DictReader(f)
            for row in reader:
                if not any(row.values()):
                    continue

                if row['action'] == 'You Bought':
                    symbol = row['symbol']
                    amount = float(row['amount'])
                    self._purchases_by_symbol[symbol] += amount

    @property
    def year(self) -> int:
        return self._file_location.year

    @property
    def month(self) -> int:
        return self._file_location.month

    @property
    def entries(self) -> list[HoldingPosition]:
        return self._entries

    @property
    def holdings(self) -> list[HoldingPosition]:
        """Return holdings excluding money market funds."""
        return [e for e in self._entries if e.symbol not in MONEY_MARKET_SYMBOLS]

    @property
    def total_ending_value(self) -> float:
        """Total ending value of all holdings."""
        return sum(e.ending_value for e in self.holdings)

    @property
    def total_beginning_value(self) -> float:
        """Total beginning value (or cost basis if unavailable) of all holdings."""
        total = 0.0
        for e in self.holdings:
            if e.beginning_value is not None:
                total += e.beginning_value
            elif e.cost_basis is not None:
                total += e.cost_basis
        return total

    def _calculate_change(self, holding: HoldingPosition) -> float:
        """
        Calculate the change in value for a holding.

        Logic:
        - If beginning_value exists: base = beginning_value
        - Else: base = cost_basis (new purchase during period)
        - Raw change = ending_value - base
        - If beginning_value exists AND there were purchases: subtract purchases
        - If no beginning_value: don't subtract (cost_basis already reflects purchase)
        """
        # Determine base value
        if holding.beginning_value is not None:
            base_value = holding.beginning_value
        elif holding.cost_basis is not None:
            base_value = holding.cost_basis
        else:
            # No base value available, cannot calculate change
            return 0.0

        # Calculate raw change
        raw_change = holding.ending_value - base_value

        # If there was a beginning balance and purchases occurred, subtract purchases
        if holding.beginning_value is not None:
            purchases = self._purchases_by_symbol.get(holding.symbol, 0.0)
            raw_change -= purchases

        return raw_change

    def _get_unrealized_by_basket(self) -> dict[str, float]:
        """Group unrealized changes by basket."""
        by_basket: dict[str, float] = defaultdict(float)

        for holding in self.holdings:
            basket = SYMBOL_TO_BASKET.get(holding.symbol)
            if basket:
                change = self._calculate_change(holding)
                by_basket[basket] += change

        return dict(by_basket)

    @property
    def total_unrealized(self) -> float:
        """Total unrealized gain/loss for all baskets."""
        by_basket = self._get_unrealized_by_basket()
        return sum(by_basket.values())

    @property
    def journal_entries(self) -> Union[list[JournalEntry], None]:
        """Generate mark-to-market journal entries grouped by basket."""
        by_basket = self._get_unrealized_by_basket()

        if not by_basket:
            return None

        _return_value: list[JournalEntry] = []
        journal_number = 40001

        # Determine the journal date (last day of the period)
        import calendar
        last_day = calendar.monthrange(self.year, self.month)[1]
        journal_date = date(self.year, self.month, last_day)

        for basket_id in sorted(by_basket.keys()):
            change = by_basket[basket_id]

            if abs(change) < 0.01:
                # Skip immaterial changes
                continue

            basket_name, fmv_account, unrealized_account = BASKET_ACCOUNTS.get(
                basket_id,
                ('Unknown', 'Trading Securities - FMV Adjustment', 'Unrealized Gain - Equity Baskets')
            )

            ref_number = f"UNR-{journal_date}-{basket_id}"
            notes = f"{journal_date} Mark-to-Market - {basket_name}"

            if change >= 0:
                # Unrealized gain
                # Debit: FMV Adjustment (increase asset)
                # Credit: Unrealized Gain (income)
                _row_debit = JournalEntry(
                    journal_date=journal_date,
                    reference_number=ref_number,
                    journal_number_prefix='MMW-',
                    journal_number_suffix=str(journal_number),
                    notes=notes,
                    journal_type='both',
                    currency='USD',
                    account=fmv_account,
                    description=f"FMV Adjustment - {basket_name}",
                    contact_name='',
                    debit=round(change, 2),
                    credit=None,
                    project_name='',
                    status='published',
                    exchange_rate='',
                    account_code=None
                )
                _row_credit = JournalEntry(
                    journal_date=journal_date,
                    reference_number=ref_number,
                    journal_number_prefix='MMW-',
                    journal_number_suffix=str(journal_number),
                    notes=notes,
                    journal_type='both',
                    currency='USD',
                    account=unrealized_account,
                    description=f"Unrealized Gain - {basket_name}",
                    contact_name='',
                    debit=None,
                    credit=round(change, 2),
                    project_name='',
                    status='published',
                    exchange_rate='',
                    account_code=None
                )
            else:
                # Unrealized loss
                # Debit: Unrealized Gain (expense - reduces income)
                # Credit: FMV Adjustment (decrease asset)
                abs_change = abs(change)
                _row_debit = JournalEntry(
                    journal_date=journal_date,
                    reference_number=ref_number,
                    journal_number_prefix='MMW-',
                    journal_number_suffix=str(journal_number),
                    notes=notes,
                    journal_type='both',
                    currency='USD',
                    account=unrealized_account,
                    description=f"Unrealized Loss - {basket_name}",
                    contact_name='',
                    debit=round(abs_change, 2),
                    credit=None,
                    project_name='',
                    status='published',
                    exchange_rate='',
                    account_code=None
                )
                _row_credit = JournalEntry(
                    journal_date=journal_date,
                    reference_number=ref_number,
                    journal_number_prefix='MMW-',
                    journal_number_suffix=str(journal_number),
                    notes=notes,
                    journal_type='both',
                    currency='USD',
                    account=fmv_account,
                    description=f"FMV Adjustment - {basket_name}",
                    contact_name='',
                    debit=None,
                    credit=round(abs_change, 2),
                    project_name='',
                    status='published',
                    exchange_rate='',
                    account_code=None
                )

            _return_value.append(_row_debit)
            _return_value.append(_row_credit)
            journal_number += 1

        return _return_value if _return_value else None

    def write(self) -> dict[str, Optional[Path]]:
        """Write unrealized journal entries to CSV file."""
        return {
            'unrealized': write_journal_entries(self.journal_entries, self._file_location.unrealized_file)
        }

    def pprint(self, log: bool = False) -> None:
        output_lines: list[str] = []

        output_lines.append(f"{self.__repr__()}")
        output_lines.append("-" * 130)

        by_basket = self._get_unrealized_by_basket()

        _header = (
            f"Total Holdings: {len(self.entries)}\n"
            f"Securities (excl. money market): {len(self.holdings)}\n"
            f"Total Ending Value: ${self.total_ending_value:,.2f}\n"
            f"Total Beginning Value: ${self.total_beginning_value:,.2f}\n"
            f"Total Unrealized: ${self.total_unrealized:,.2f}\n"
            f"Holdings File: {self._file_location.holdings_file}"
        )

        output_lines.append(_header)
        output_lines.append("-" * 130)

        # Print breakdown by basket
        output_lines.append("Unrealized by Basket:")
        for basket_id in sorted(by_basket.keys()):
            basket_name = BASKET_ACCOUNTS.get(basket_id, ('Unknown',))[0]
            change = by_basket[basket_id]
            output_lines.append(f"  {basket_id} ({basket_name}): ${change:,.2f}")

        output_lines.append("-" * 130)

        # Print detail by holding
        output_lines.append(f"{'Symbol':<8} {'Basket':<8} {'Beg Value':>12} {'End Value':>12} {'Purchases':>12} {'Change':>12}")
        output_lines.append("-" * 130)

        for holding in sorted(self.holdings, key=lambda h: h.symbol):
            basket = SYMBOL_TO_BASKET.get(holding.symbol, '')
            beg_val = holding.beginning_value if holding.beginning_value is not None else holding.cost_basis
            purchases = self._purchases_by_symbol.get(holding.symbol, 0.0)
            change = self._calculate_change(holding)

            beg_str = f"{beg_val:,.2f}" if beg_val else ""
            pur_str = f"{purchases:,.2f}" if purchases else ""

            output_lines.append(
                f"{holding.symbol:<8} {basket:<8} {beg_str:>12} {holding.ending_value:>12,.2f} {pur_str:>12} {change:>12,.2f}"
            )

        output_lines.append("-" * 130)

        entries = self.journal_entries

        output_lines.append(f"\n{'Date':<12} {'Journal #':<12} {'Description':<40} {'Account':<45} {'Debit':>12} {'Credit':>12}")
        output_lines.append("-" * 130)

        if not entries:
            output_lines.append("There are no journal entries.")
        else:
            prev_journal_number = None
            for e in entries:
                if prev_journal_number is not None and e.journal_number != prev_journal_number:
                    output_lines.append("")
                prev_journal_number = e.journal_number
                debit_str = f"{e.debit:,.2f}" if e.debit else ""
                credit_str = f"{e.credit:,.2f}" if e.credit else ""
                desc_display = e.description[:38] + ".." if e.description and len(e.description) > 40 else (e.description or "")
                account_display = e.account[:43] + ".." if len(e.account) > 45 else e.account
                output_lines.append(
                    f"{str(e.journal_date):<12} {e.journal_number:<12} {desc_display:<40} {account_display:<45} {debit_str:>12} {credit_str:>12}"
                )
            output_lines.append("-" * 130)
            total_debit = sum(e.debit for e in entries if e.debit)
            total_credit = sum(e.credit for e in entries if e.credit)
            output_lines.append(f"{'Total':<112} {total_debit:>12,.2f} {total_credit:>12,.2f}")

        output = "\n".join(output_lines)
        print(output)

        if log:
            write_log(output, self._file_location.log_file)

        return None

    def __len__(self) -> int:
        return len(self._entries)

    def __iter__(self) -> Iterator[HoldingPosition]:
        return iter(self._entries)

    def __str__(self) -> str:
        return f"{self._file_location.holdings_file}"

    def __float__(self) -> float:
        return self.total_unrealized

    def __repr__(self) -> str:
        """String representation of Holdings."""
        return f"Holdings(FileLocation(year={self.year}, month={self.month}, root='{self._file_location.root}'))"


if __name__ == '__main__':
    _holdings = Holdings(FileLocation(2025, 2, root='/Users/mick/GitHub/mjfii/mmm-accounting-agent-py'))
    _holdings.pprint()
