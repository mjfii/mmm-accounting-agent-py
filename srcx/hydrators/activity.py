import csv
from csv import DictReader
from datetime import date
from pathlib import Path
from typing import Iterator, Optional, Union
from srcx.common.file_location import FileLocation
from srcx.datasets.activity_transaction import ActivityTransaction
from srcx.datasets.journal_entry import JournalEntry
from collections import defaultdict


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
        self._load(self._file_location.activity_file)

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

        # group transactions by date and action
        self._bought_by_date = defaultdict(list)
        self._sold_by_date = defaultdict(list)
        for txn in self._entries:
            if txn.action == 'You Bought':
                self._bought_by_date[txn.settlement_date].append(txn)
            elif txn.action == 'You Sold':
                self._sold_by_date[txn.settlement_date].append(txn)

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
        """Return only buy transactions."""
        return [e for e in self._entries if e.action == 'You Bought']

    @property
    def sold(self) -> list[ActivityTransaction]:
        """Return only sell transactions."""
        return [e for e in self._entries if e.action == 'You Sold']

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
        if not self._bought_by_date:
            return None
        else:
            _return_value: list[JournalEntry] = []

        journal_number = 20001

        for settlement_date in sorted(self._bought_by_date.keys()):
            txns = self._bought_by_date[settlement_date]
            ref_number = f"PUR-{settlement_date}"
            symbols = ', '.join(sorted(set(t.symbol for t in txns)))
            notes = f"{settlement_date} Purchases - {symbols}"
            total_amount = sum(t.amount for t in txns)

            # Debit: Investment accounts (one per transaction)
            for txn in txns:
                _row = JournalEntry(
                    journal_date=settlement_date,
                    reference_number=ref_number,
                    journal_number_prefix='MMW-',
                    journal_number_suffix=str(journal_number),
                    notes=notes,
                    journal_type='both',
                    currency='USD',
                    account='Investments - Fidelity Brokerage Account',
                    description=f"Purchase - {txn.symbol}",
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
                description=f"Purchase - {symbols}",
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
        if not self._sold_by_date:
            return None
        else:
            _return_value: list[JournalEntry] = []

        journal_number = 30001

        for settlement_date in sorted(self._sold_by_date.keys()):
            txns = self._sold_by_date[settlement_date]
            ref_number = f"SAL-{settlement_date}"
            symbols = ', '.join(sorted(set(t.symbol for t in txns)))
            notes = f"{settlement_date} Sales - {symbols}"
            total_proceeds = sum(t.amount for t in txns)
            total_cost_basis = sum(t.cost_basis for t in txns if t.cost_basis)
            gain_loss = total_proceeds - total_cost_basis

            # Debit: Cash (proceeds)
            _row = JournalEntry(
                journal_date=settlement_date,
                reference_number=ref_number,
                journal_number_prefix='MMW-',
                journal_number_suffix=str(journal_number),
                notes=notes,
                journal_type='both',
                currency='USD',
                account='Cash - Fidelity Cash Management Account',
                description=f"Sale Proceeds - {symbols}",
                contact_name='',
                debit=total_proceeds,
                credit=None,
                project_name='',
                status='published',
                exchange_rate='',
                account_code=None
            )
            _return_value.append(_row)

            # Credit: Investment accounts (cost basis per transaction)
            for txn in txns:
                if txn.cost_basis:
                    _row = JournalEntry(
                        journal_date=settlement_date,
                        reference_number=ref_number,
                        journal_number_prefix='MMW-',
                        journal_number_suffix=str(journal_number),
                        notes=notes,
                        journal_type='both',
                        currency='USD',
                        account='Investments - Fidelity Brokerage Account',
                        description=f"Sale Cost Basis - {txn.symbol}",
                        contact_name='',
                        debit=None,
                        credit=txn.cost_basis,
                        project_name='',
                        status='published',
                        exchange_rate='',
                        account_code=None
                    )
                    _return_value.append(_row)

            # Gain/Loss entry
            if gain_loss != 0:
                if gain_loss > 0:
                    # Realized gain: Credit to income
                    _row = JournalEntry(
                        journal_date=settlement_date,
                        reference_number=ref_number,
                        journal_number_prefix='MMW-',
                        journal_number_suffix=str(journal_number),
                        notes=notes,
                        journal_type='both',
                        currency='USD',
                        account='Income - Realized Gains',
                        description=f"Realized Gain - {symbols}",
                        contact_name='',
                        debit=None,
                        credit=gain_loss,
                        project_name='',
                        status='published',
                        exchange_rate='',
                        account_code=None
                    )
                else:
                    # Realized loss: Debit to expense
                    _row = JournalEntry(
                        journal_date=settlement_date,
                        reference_number=ref_number,
                        journal_number_prefix='MMW-',
                        journal_number_suffix=str(journal_number),
                        notes=notes,
                        journal_type='both',
                        currency='USD',
                        account='Expense - Realized Losses',
                        description=f"Realized Loss - {symbols}",
                        contact_name='',
                        debit=abs(gain_loss),
                        credit=None,
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
        print("-" * 130)

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
        print("-" * 130)

        entries = self.journal_entries
        """Return a formatted table of journal entries."""

        lines: list = [
            f"{'Date':<12} {'Journal #':<12} {'Description':<35} {'Account':<40} {'Debit':>12} {'Credit':>12}",
            "-" * 130
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
                desc_display = e.description[:33] + ".." if e.description and len(e.description) > 35 else (e.description or "")
                account_display = e.account[:38] + ".." if len(e.account) > 40 else e.account
                lines.append(
                    f"{str(e.journal_date):<12} {e.journal_number:<12} {desc_display:<35} {account_display:<40} {debit_str:>12} {credit_str:>12}"
                )
            lines.append("-" * 130)
            total_debit = sum(e.debit for e in entries if e.debit)
            total_credit = sum(e.credit for e in entries if e.credit)
            lines.append(f"{'Total':<102} {total_debit:>12,.2f} {total_credit:>12,.2f}")

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
