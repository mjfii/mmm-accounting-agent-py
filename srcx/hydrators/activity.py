import csv
from csv import DictReader
from datetime import date
from pathlib import Path
from typing import Iterator, Optional, Union
from srcx.common.file_location import FileLocation
from srcx.datasets.activity_transaction import ActivityTransaction
from srcx.datasets.journal_entry import JournalEntry
from collections import defaultdict


MONEY_MARKET_SYMBOLS = {'FDRXX', 'SPAXX', 'FCASH'}

BASKET_INCOME_ACCOUNTS = {
    '10001': ('Water Investments', 'Income - Equity Securities Baskets - Water Investments'),
    '10003': ('Buy Write ETFs', 'Income - Equity Securities Baskets - Buy Write ETFs'),
    '10005': ('Holding Companies', 'Income - Equity Securities Baskets - Holding Companies'),
    '10007': ('Balanced ETFs', 'Income - Equity Securities Baskets - Balanced ETFs'),
}


class Activity(object):
    """
    Represents securities activity data for a statement period.

    Hydrates from an ACT CSV file which contains multiple records
    representing buy and sell transactions.
    """
    def __init__(self, file_location: FileLocation) -> None:
        """
        Initialize Activity for a specific month and year.
        """
        self._file_location = file_location
        self._entries: list[ActivityTransaction] = []
        self._symbol_map: dict[str, str] = {}
        self._load(self._file_location.activity_file)
        self._load_chart_of_accounts()

    def _load(self, csv_path: Path) -> None:
        """Load activity data from CSV file."""
        if not csv_path.exists():
            raise FileNotFoundError(f"CSV file not found: {csv_path}")

        with open(csv_path, 'r', encoding='utf-8') as f:
            reader: DictReader[str] = csv.DictReader(f)
            for row in reader:
                if not any(row.values()):
                    continue

                entry = ActivityTransaction(
                    settlement_date=date.fromisoformat(row['settlement_date']),
                    action=row['action'],
                    symbol=row['symbol'],
                    security_name=row['security_name'],
                    quantity=float(row['quantity']),
                    price=float(row['price']),
                    amount=float(row['amount']),
                    transaction_cost=float(row['transaction_cost']) if row.get('transaction_cost') else None,
                    basket=row.get('basket') if row.get('basket') else None,
                    cost_basis=float(row['cost_basis']) if row.get('cost_basis') else None,
                )
                self._entries.append(entry)

        # group transactions by (date, basket) and action
        self._bought_by_date_basket: dict[tuple, list] = defaultdict(list)
        self._sold_by_date_basket: dict[tuple, list] = defaultdict(list)
        for txn in self._entries:
            if txn.symbol in MONEY_MARKET_SYMBOLS:
                continue
            key = (txn.settlement_date, txn.basket or '')
            if txn.action == 'You Bought':
                self._bought_by_date_basket[key].append(txn)
            elif txn.action == 'You Sold':
                self._sold_by_date_basket[key].append(txn)

    def _load_chart_of_accounts(self) -> None:
        """Load chart of accounts to map symbols to full account names."""
        chart_path = self._file_location.root / 'books' / 'chart_of_accounts.csv'

        if not chart_path.exists():
            return

        with open(chart_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                account_name = row['Account Name']
                if '(' in account_name and ')' in account_name:
                    start = account_name.rfind('(')
                    end = account_name.rfind(')')
                    symbol = account_name[start+1:end]
                    self._symbol_map[symbol] = account_name

    @property
    def year(self) -> int:
        return self._file_location.year

    @property
    def month(self) -> int:
        return self._file_location.month

    @property
    def entries(self) -> list[ActivityTransaction]:
        return self._entries

    @property
    def bought(self) -> list[ActivityTransaction]:
        """Return only buy transactions (excluding money market)."""
        return [e for e in self._entries if e.action == 'You Bought' and e.symbol not in MONEY_MARKET_SYMBOLS]

    @property
    def sold(self) -> list[ActivityTransaction]:
        """Return only sell transactions (excluding money market)."""
        return [e for e in self._entries if e.action == 'You Sold' and e.symbol not in MONEY_MARKET_SYMBOLS]

    @property
    def total_bought(self) -> float:
        """Total of all purchase amounts."""
        return sum(e.amount for e in self.bought)

    @property
    def total_sold(self) -> float:
        """Total of all sale amounts."""
        return sum(e.amount for e in self.sold)

    @property
    def total_cost_basis_sold(self) -> float:
        """Total cost basis of all sold securities."""
        return sum(e.cost_basis for e in self.sold if e.cost_basis)

    @property
    def realized_gain(self) -> float:
        """Realized gain/loss from sales (proceeds - cost basis)."""
        return self.total_sold - self.total_cost_basis_sold

    @property
    def purchase_journal_entries(self) -> Union[list[JournalEntry], None]:
        """Generate journal entries for purchases."""
        if not self._bought_by_date_basket:
            return None

        _return_value: list[JournalEntry] = []
        journal_number = 20001

        for (settlement_date, basket), txns in sorted(self._bought_by_date_basket.items()):
            basket_suffix = f"-{basket}" if basket else ""
            ref_number = f"PUR-{settlement_date}{basket_suffix}"
            symbols = ', '.join(sorted(set(t.symbol for t in txns)))
            notes = f"{settlement_date} Purchase - {symbols}"
            total_amount = round(sum(t.amount for t in txns), 3)

            # Debit: Investment accounts (one per transaction)
            for txn in txns:
                account_name = self._symbol_map.get(txn.symbol, txn.symbol)
                if txn.quantity and txn.price:
                    description = f"Purchase - {txn.symbol} - {txn.quantity:.3f} @ ~ ${txn.price:.2f}"
                else:
                    description = f"Purchase - {txn.symbol}"

                _row = JournalEntry(
                    journal_date=settlement_date,
                    reference_number=ref_number,
                    journal_number_prefix='MMW-',
                    journal_number_suffix=str(journal_number),
                    notes=notes,
                    journal_type='both',
                    currency='USD',
                    account=account_name,
                    description=description,
                    contact_name='',
                    debit=txn.amount,
                    credit=None,
                    project_name='',
                    status='published',
                    exchange_rate='',
                    account_code=None
                )
                _return_value.append(_row)

            # Credit: Cash (total amount)
            _row = JournalEntry(
                journal_date=settlement_date,
                reference_number=ref_number,
                journal_number_prefix='MMW-',
                journal_number_suffix=str(journal_number),
                notes=notes,
                journal_type='both',
                currency='USD',
                account='Cash - Fidelity Cash Management Account',
                description=f"Cash for {symbols}",
                contact_name='',
                debit=None,
                credit=total_amount,
                project_name='',
                status='published',
                exchange_rate='',
                account_code=None
            )
            _return_value.append(_row)

            journal_number += 1

        return _return_value

    @property
    def sale_journal_entries(self) -> Union[list[JournalEntry], None]:
        """Generate journal entries for sales."""
        if not self._sold_by_date_basket:
            return None

        _return_value: list[JournalEntry] = []
        journal_number = 30001

        for (settlement_date, basket), txns in sorted(self._sold_by_date_basket.items()):
            basket_suffix = f"-{basket}" if basket else ""
            basket_name, income_account = BASKET_INCOME_ACCOUNTS.get(basket, ('', 'Income - Equity Securities'))

            ref_number = f"SAL-{settlement_date}{basket_suffix}"
            symbols = ', '.join(sorted(set(t.symbol for t in txns)))

            if basket_name:
                notes = f"{settlement_date} Sale - {basket_name} - {symbols}"
            else:
                notes = f"{settlement_date} Sale - {symbols}"

            total_proceeds = sum(t.amount for t in txns)

            # Group transactions by symbol for consolidated entries
            symbol_totals: dict[str, dict] = defaultdict(lambda: {'proceeds': 0.0, 'cost_basis': 0.0, 'quantity': 0.0})
            for txn in txns:
                symbol_totals[txn.symbol]['proceeds'] += txn.amount
                symbol_totals[txn.symbol]['cost_basis'] += txn.cost_basis if txn.cost_basis else txn.amount
                symbol_totals[txn.symbol]['quantity'] += txn.quantity if txn.quantity else 0

            # 1. Debit cash account for total proceeds
            _row = JournalEntry(
                journal_date=settlement_date,
                reference_number=ref_number,
                journal_number_prefix='MMW-',
                journal_number_suffix=str(journal_number),
                notes=notes,
                journal_type='both',
                currency='USD',
                account='Cash - Fidelity Cash Management Account',
                description=f"Proceeds from {basket_name + ' - ' if basket_name else ''}{symbols}",
                contact_name='',
                debit=total_proceeds,
                credit=None,
                project_name='',
                status='published',
                exchange_rate='',
                account_code=None
            )
            _return_value.append(_row)

            # 2. Record realized gains/losses per symbol
            for symbol in sorted(symbol_totals.keys()):
                totals = symbol_totals[symbol]
                proceeds = totals['proceeds']
                cost_basis = totals['cost_basis']
                gain_loss = proceeds - cost_basis

                if abs(gain_loss) >= 0.01:  # Only record if material
                    if gain_loss < 0:
                        # Realized loss - debit income account
                        _row = JournalEntry(
                            journal_date=settlement_date,
                            reference_number=ref_number,
                            journal_number_prefix='MMW-',
                            journal_number_suffix=str(journal_number),
                            notes=notes,
                            journal_type='both',
                            currency='USD',
                            account=income_account,
                            description=f"Realized Loss - {symbol}",
                            contact_name='',
                            debit=abs(gain_loss),
                            credit=None,
                            project_name='',
                            status='published',
                            exchange_rate='',
                            account_code=None
                        )
                    else:
                        # Realized gain - credit income account
                        _row = JournalEntry(
                            journal_date=settlement_date,
                            reference_number=ref_number,
                            journal_number_prefix='MMW-',
                            journal_number_suffix=str(journal_number),
                            notes=notes,
                            journal_type='both',
                            currency='USD',
                            account=income_account,
                            description=f"Realized Gain - {symbol}",
                            contact_name='',
                            debit=None,
                            credit=gain_loss,
                            project_name='',
                            status='published',
                            exchange_rate='',
                            account_code=None
                        )
                    _return_value.append(_row)

            # 3. Credit security accounts with cost basis (reducing asset)
            for symbol in sorted(symbol_totals.keys()):
                totals = symbol_totals[symbol]
                cost_basis = totals['cost_basis']
                quantity = totals['quantity']
                account_name = self._symbol_map.get(symbol, symbol)

                # Calculate average price for description
                avg_price = totals['proceeds'] / quantity if quantity else 0
                description = f"Sale - {symbol} - {quantity:.3f} @ ~ ${avg_price:.2f}"

                _row = JournalEntry(
                    journal_date=settlement_date,
                    reference_number=ref_number,
                    journal_number_prefix='MMW-',
                    journal_number_suffix=str(journal_number),
                    notes=notes,
                    journal_type='both',
                    currency='USD',
                    account=account_name,
                    description=description,
                    contact_name='',
                    debit=None,
                    credit=cost_basis,
                    project_name='',
                    status='published',
                    exchange_rate='',
                    account_code=None
                )
                _return_value.append(_row)

            journal_number += 1

        return _return_value

    @property
    def journal_entries(self) -> Union[list[JournalEntry], None]:
        """All journal entries (purchases + sales)."""
        entries: list[JournalEntry] = []
        if self.purchase_journal_entries:
            entries.extend(self.purchase_journal_entries)
        if self.sale_journal_entries:
            entries.extend(self.sale_journal_entries)
        return entries if entries else None

    def pprint(self) -> None:

        print(f"{self.__repr__()}")
        print("-" * 150)

        _header = (
            f"Total Transactions: {len(self.entries)}\n"
            f"Buy Transactions: {len(self.bought)}\n"
            f"Sell Transactions: {len(self.sold)}\n"
            f"Total Bought: ${self.total_bought:,.2f}\n"
            f"Total Sold: ${self.total_sold:,.2f}\n"
            f"Cost Basis Sold: ${self.total_cost_basis_sold:,.2f}\n"
            f"Realized Gain/Loss: ${self.realized_gain:,.2f}\n"
            f"Activity File: {self._file_location.activity_file}"
        )

        print(_header)
        print("-" * 150)

        entries = self.journal_entries

        lines: list = [
            f"{'Date':<12} {'Journal #':<12} {'Description':<45} {'Account':<50} {'Debit':>12} {'Credit':>12}",
            "-" * 150
        ]
        if not entries:
            lines.append("There are no journal entries.")
        else:
            prev_journal_number = None
            for e in entries:
                if prev_journal_number is not None and e.journal_number != prev_journal_number:
                    lines.append("")
                prev_journal_number = e.journal_number
                debit_str = f"{e.debit:,.2f}" if e.debit else ""
                credit_str = f"{e.credit:,.2f}" if e.credit else ""
                desc_display = e.description[:43] + ".." if e.description and len(e.description) > 45 else (e.description or "")
                account_display = e.account[:48] + ".." if len(e.account) > 50 else e.account
                lines.append(
                    f"{str(e.journal_date):<12} {e.journal_number:<12} {desc_display:<45} {account_display:<50} {debit_str:>12} {credit_str:>12}"
                )
            lines.append("-" * 150)
            total_debit = sum(e.debit for e in entries if e.debit)
            total_credit = sum(e.credit for e in entries if e.credit)
            lines.append(f"{'Total':<122} {total_debit:>12,.2f} {total_credit:>12,.2f}")

        print("\n".join(lines))
        return None

    def __len__(self) -> int:
        return len(self._entries)

    def __iter__(self) -> Iterator[ActivityTransaction]:
        return iter(self._entries)

    def __str__(self) -> str:
        return f"{self._file_location.activity_file}"

    def __float__(self) -> float:
        return self.total_bought - self.total_sold

    def __repr__(self) -> str:
        """String representation of Activity."""
        return f"Activity(FileLocation(year={self.year}, month={self.month}, root='{self._file_location.root}'))"


if __name__ == '__main__':
    _activity = Activity(FileLocation(2025, 9, root='/Users/mick/GitHub/mjfii/mmm-accounting-agent-py'))
    _activity.pprint()
