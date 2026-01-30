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
        self._sales_by_symbol: dict[str, dict] = defaultdict(lambda: {'proceeds': 0.0, 'cost_basis': 0.0})
        self._prior_values: dict[str, float] = {}
        self._load_holdings(self._file_location.holdings_file)
        self._load_activity(self._file_location.activity_file)
        self._load_prior_holdings()

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
        """Load activity data to get purchases and sales during the period."""
        if not csv_path.exists():
            # No activity file means no activity to account for
            return

        with open(csv_path, 'r', encoding='utf-8') as f:
            reader: DictReader[str] = csv.DictReader(f)
            for row in reader:
                if not any(row.values()):
                    continue

                symbol = row['symbol']
                amount = float(row['amount'])

                if row['action'] == 'You Bought':
                    self._purchases_by_symbol[symbol] += amount
                elif row['action'] == 'You Sold':
                    cost_basis = float(row['cost_basis']) if row.get('cost_basis') else 0.0
                    self._sales_by_symbol[symbol]['proceeds'] += amount
                    self._sales_by_symbol[symbol]['cost_basis'] += cost_basis

    def _load_prior_holdings(self) -> None:
        """Load prior month's holdings to get ending values for liquidated securities."""
        prior_month = self.month - 1 if self.month > 1 else 12
        prior_year = self.year if self.month > 1 else self.year - 1
        prior_holdings_path = self._file_location.root / 'scrapes' / 'holdings' / str(prior_year) / f"MMW-{prior_year}-{prior_month:02d}-HLD.csv"

        if not prior_holdings_path.exists():
            return

        with open(prior_holdings_path, 'r', encoding='utf-8') as f:
            reader: DictReader[str] = csv.DictReader(f)
            for row in reader:
                if not any(row.values()):
                    continue
                symbol = row['symbol']
                ending_value = float(row['ending_value']) if row.get('ending_value') else None
                if ending_value is not None:
                    self._prior_values[symbol] = ending_value

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

    def _get_liquidations(self) -> dict[str, float]:
        """
        Get change in value for securities that were completely liquidated.

        A liquidation is a sale where the security no longer appears in month-end holdings.
        Change = proceeds - cost_basis
        """
        holdings_symbols = {e.symbol for e in self._entries}
        liquidations: dict[str, float] = {}

        for symbol, sale_data in self._sales_by_symbol.items():
            if symbol not in holdings_symbols and symbol not in MONEY_MARKET_SYMBOLS:
                # Security was completely liquidated
                change = sale_data['proceeds'] - sale_data['cost_basis']
                liquidations[symbol] = change

        return liquidations

    def _get_liquidation_period_change(self) -> dict[str, float]:
        """
        Get period change for securities that were completely liquidated.

        This measures the change from prior period ending value to sale proceeds,
        which represents the gain/loss during the current period only.
        Change = proceeds - prior_ending_value
        """
        holdings_symbols = {e.symbol for e in self._entries}
        period_changes: dict[str, float] = {}

        for symbol, sale_data in self._sales_by_symbol.items():
            if symbol not in holdings_symbols and symbol not in MONEY_MARKET_SYMBOLS:
                if symbol in self._prior_values:
                    prior_value = self._prior_values[symbol]
                    period_change = sale_data['proceeds'] - prior_value
                    period_changes[symbol] = period_change

        return period_changes

    def _get_liquidation_period_change_by_basket(self) -> dict[str, float]:
        """Group liquidation period changes by basket."""
        by_basket: dict[str, float] = defaultdict(float)

        period_changes = self._get_liquidation_period_change()
        for symbol, change in period_changes.items():
            basket = SYMBOL_TO_BASKET.get(symbol)
            if basket:
                by_basket[basket] += change

        return dict(by_basket)

    def _get_unrealized_by_basket(self) -> dict[str, float]:
        """Group unrealized changes by basket (holdings + liquidation period changes)."""
        by_basket: dict[str, float] = defaultdict(float)

        # Add changes from current holdings
        for holding in self.holdings:
            basket = SYMBOL_TO_BASKET.get(holding.symbol)
            if basket:
                change = self._calculate_change(holding)
                by_basket[basket] += change

        # Add period changes for liquidated securities (proceeds - prior_ending_value)
        liquidation_period_changes = self._get_liquidation_period_change_by_basket()
        for basket, change in liquidation_period_changes.items():
            by_basket[basket] += change

        return dict(by_basket)

    def _get_liquidations_by_basket(self) -> dict[str, float]:
        """Group liquidation changes by basket."""
        by_basket: dict[str, float] = defaultdict(float)

        liquidations = self._get_liquidations()
        for symbol, change in liquidations.items():
            basket = SYMBOL_TO_BASKET.get(symbol)
            if basket:
                by_basket[basket] += change

        return dict(by_basket)

    def _get_total_by_basket(self) -> dict[str, float]:
        """Get combined unrealized + liquidation changes by basket."""
        by_basket: dict[str, float] = defaultdict(float)

        unrealized = self._get_unrealized_by_basket()
        for basket, change in unrealized.items():
            by_basket[basket] += change

        liquidations = self._get_liquidations_by_basket()
        for basket, change in liquidations.items():
            by_basket[basket] += change

        return dict(by_basket)

    @property
    def total_unrealized(self) -> float:
        """Total unrealized gain/loss for all baskets (including liquidations)."""
        by_basket = self._get_total_by_basket()
        return sum(by_basket.values())

    @property
    def journal_entries(self) -> Union[list[JournalEntry], None]:
        """Generate mark-to-market and liquidation journal entries grouped by basket."""
        unrealized_by_basket = self._get_unrealized_by_basket()
        liquidations_by_basket = self._get_liquidations_by_basket()

        if not unrealized_by_basket and not liquidations_by_basket:
            return None

        _return_value: list[JournalEntry] = []
        journal_number = 40001

        # Determine the journal date (last day of the period)
        import calendar
        last_day = calendar.monthrange(self.year, self.month)[1]
        journal_date = date(self.year, self.month, last_day)

        # Generate Mark-to-Market entries (holdings only)
        for basket_id in sorted(unrealized_by_basket.keys()):
            change = unrealized_by_basket[basket_id]

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

        # Generate Liquidation entries (separate from mark-to-market)
        for basket_id in sorted(liquidations_by_basket.keys()):
            change = liquidations_by_basket[basket_id]

            if abs(change) < 0.01:
                # Skip immaterial changes
                continue

            basket_name, fmv_account, unrealized_account = BASKET_ACCOUNTS.get(
                basket_id,
                ('Unknown', 'Trading Securities - FMV Adjustment', 'Unrealized Gain - Equity Baskets')
            )

            ref_number = f"LIQ-{journal_date}-{basket_id}"
            notes = f"{journal_date} Liquidation - {basket_name}"

            if change >= 0:
                # Liquidation gain
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
                    description=f"Liquidation Gain - {basket_name}",
                    contact_name='',
                    debit=None,
                    credit=round(change, 2),
                    project_name='',
                    status='published',
                    exchange_rate='',
                    account_code=None
                )
            else:
                # Liquidation loss - debit FMV asset account, credit unrealized
                abs_change = abs(change)
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
                    account=unrealized_account,
                    description=f"Liquidation Loss - {basket_name}",
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
        output_lines.append("-" * 150)

        unrealized_by_basket = self._get_unrealized_by_basket()
        liquidations_by_basket = self._get_liquidations_by_basket()
        total_by_basket = self._get_total_by_basket()

        _header = (
            f"Total Holdings: {len(self.entries)}\n"
            f"Securities (excl. money market): {len(self.holdings)}\n"
            f"Total Ending Value: ${self.total_ending_value:,.2f}\n"
            f"Total Beginning Value: ${self.total_beginning_value:,.2f}\n"
            f"Total Unrealized: ${self.total_unrealized:,.2f}\n"
            f"Holdings File: {self._file_location.holdings_file}"
        )

        output_lines.append(_header)
        output_lines.append("-" * 150)

        # Print breakdown by basket
        output_lines.append("Change by Basket:")
        output_lines.append(f"  {'Basket':<35} {'Mark-to-Market':>15} {'Liquidation':>15} {'Total':>15}")
        grand_total_mtm = 0.0
        grand_total_liq = 0.0
        grand_total = 0.0
        all_basket_ids = sorted(set(unrealized_by_basket.keys()) | set(liquidations_by_basket.keys()))
        for basket_id in all_basket_ids:
            basket_name = BASKET_ACCOUNTS.get(basket_id, ('Unknown',))[0]
            mtm = unrealized_by_basket.get(basket_id, 0.0)
            liq = liquidations_by_basket.get(basket_id, 0.0)
            total = total_by_basket.get(basket_id, 0.0)
            grand_total_mtm += mtm
            grand_total_liq += liq
            grand_total += total
            liq_str = f"${liq:,.2f}" if liq else ""
            output_lines.append(f"  {basket_id} ({basket_name}){'':<10} ${mtm:>12,.2f} {liq_str:>15} ${total:>12,.2f}")
        output_lines.append(f"  {'Total':<35} ${grand_total_mtm:>12,.2f} ${grand_total_liq:>12,.2f} ${grand_total:>12,.2f}")

        output_lines.append("-" * 150)

        # Print detail by holding
        output_lines.append(f"{'Symbol':<8} {'Basket':<8} {'Beg Value':>12} {'End Value':>12} {'Purchases':>12} {'Change':>12}")
        output_lines.append("-" * 150)

        total_beg = 0.0
        total_end = 0.0
        total_pur = 0.0
        total_chg = 0.0

        for holding in sorted(self.holdings, key=lambda h: h.symbol):
            basket = SYMBOL_TO_BASKET.get(holding.symbol, '')
            beg_val = holding.beginning_value if holding.beginning_value is not None else holding.cost_basis
            purchases = self._purchases_by_symbol.get(holding.symbol, 0.0)
            change = self._calculate_change(holding)

            total_beg += beg_val if beg_val else 0.0
            total_end += holding.ending_value
            total_pur += purchases
            total_chg += change

            beg_str = f"{beg_val:,.2f}" if beg_val else ""
            pur_str = f"{purchases:,.2f}" if purchases else ""

            output_lines.append(
                f"{holding.symbol:<8} {basket:<8} {beg_str:>12} {holding.ending_value:>12,.2f} {pur_str:>12} {change:>12,.2f}"
            )

        # Print liquidations (securities sold entirely during the period)
        liquidations = self._get_liquidations()
        period_changes = self._get_liquidation_period_change()
        if liquidations:
            output_lines.append("")
            output_lines.append("Liquidations (sold entirely):")
            output_lines.append(f"{'Symbol':<8} {'Basket':<8} {'Prior End':>12} {'Proceeds':>12} {'Period Chg':>12} {'Cost Basis':>12} {'Realized':>12}")
            for symbol in sorted(liquidations.keys()):
                basket = SYMBOL_TO_BASKET.get(symbol, '')
                sale_data = self._sales_by_symbol[symbol]
                cost_basis = sale_data['cost_basis']
                proceeds = sale_data['proceeds']
                realized_change = liquidations[symbol]
                prior_end = self._prior_values.get(symbol, 0.0)
                period_change = period_changes.get(symbol, 0.0)
                total_beg += prior_end
                total_end += proceeds
                total_chg += period_change
                output_lines.append(
                    f"{symbol:<8} {basket:<8} {prior_end:>12,.2f} {proceeds:>12,.2f} {period_change:>12,.2f} {cost_basis:>12,.2f} {realized_change:>12,.2f}"
                )

        output_lines.append("-" * 150)
        pur_total_str = f"{total_pur:,.2f}" if total_pur else ""
        output_lines.append(f"{'Total':<8} {'':<8} {total_beg:>12,.2f} {total_end:>12,.2f} {pur_total_str:>12} {total_chg:>12,.2f}")

        entries = self.journal_entries

        output_lines.append(f"\n{'Date':<12} {'Journal #':<12} {'Description':<40} {'Account':<45} {'Debit':>12} {'Credit':>12}")
        output_lines.append("-" * 150)

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
            output_lines.append("-" * 150)
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
