import csv
from csv import DictReader
from datetime import date
from pathlib import Path
from typing import Iterator, Optional, Union
from srcx.common.file_location import FileLocation
from srcx.datasets.income_transaction import IncomeTransaction
from srcx.datasets.journal_entry import JournalEntry
from srcx.common.journal_writer import write_journal_entries
from srcx.common.log_writer import write_log
from collections import defaultdict


class Income(object):
    """
    Represents income data for a statement period.

    Hydrates from an INC CSV file which contains multiple records
    representing dividends, interest, and reinvestment transactions.
    """
    def __init__(self, file_location: FileLocation) -> None:
        """
        Initialize Income for a specific month and year.
        """
        self._file_location = file_location
        self._entries: list[IncomeTransaction] = []
        self._load(self._file_location.income_file)

    def _load(self, csv_path: Path) -> None:
        """Load income data from CSV file."""
        if not csv_path.exists():
            raise FileNotFoundError(f"CSV file not found: {csv_path}")

        with open(csv_path, 'r', encoding='utf-8') as f:
            reader: DictReader[str] = csv.DictReader(f)
            for row in reader:
                if not any(row.values()):
                    continue

                entry = IncomeTransaction(
                    settlement_date=date.fromisoformat(row['settlement_date']),
                    security_name=row['security_name'],
                    symbol=row['symbol'],
                    cusip=row['cusip'],
                    description=row['description'],
                    quantity=float(row['quantity']) if row['quantity'] else None,
                    price=float(row['price']) if row['price'] else None,
                    amount=float(row['amount']),
                )
                self._entries.append(entry)

        # group transactions by date
        self._income_by_date = defaultdict(list)
        for txn in self.income:
            self._income_by_date[txn.settlement_date].append(txn)

    @property
    def year(self) -> int:
        return self._file_location.year

    @property
    def month(self) -> int:
        return self._file_location.month

    @property
    def entries(self) -> list[IncomeTransaction]:
        return self._entries

    @property
    def income(self) -> list[IncomeTransaction]:
        """Return only dividend entries."""
        return [e for e in self._entries if e.description == 'Dividend Received']

    @property
    def total_income(self) -> float:
        """Total of all positive income amounts (excludes reinvestment)."""
        return sum(e.amount for e in self.income)

    @property
    def total_reinvestment(self) -> float:
        """Total of all reinvestment amounts (negative values)."""
        return abs(sum(e.amount for e in self._entries if e.description == 'Reinvestment'))

    @property
    def journal_entries(self) -> Union[list[JournalEntry], None]:

        if not self._income_by_date:
            return None
        else:
            _return_value: list[JournalEntry] = []

        #
        journal_number = 10001

        for settlement_date in sorted(self._income_by_date.keys()):
            txns = self._income_by_date[settlement_date]
            ref_number = f"DIV-{settlement_date}"
            symbols = ', '.join(sorted(set(t.symbol for t in txns)))
            notes = f"{settlement_date} Dividends - {symbols}"
            total_amount = sum(t.amount for t in txns)

            for txn in txns:
                _row = JournalEntry(
                    journal_date = settlement_date,
                    reference_number =  ref_number,
                    journal_number_prefix = 'MMW-',
                    journal_number_suffix =  str(journal_number),
                    notes =  notes,
                    journal_type = 'both',
                    currency = 'USD',
                    account = 'Cash - Fidelity Cash Management Account',
                    description = f"Dividend - {txn.symbol}",
                    contact_name = '',
                    debit = txn.amount,
                    credit = None,
                    project_name = '',
                    status = 'published',
                    exchange_rate = '',
                    account_code=None
                )
                _return_value.append(_row)

            _row = JournalEntry(
                journal_date = settlement_date,
                reference_number =  ref_number,
                journal_number_prefix = 'MMW-',
                journal_number_suffix =  str(journal_number),
                notes =  notes,
                journal_type = 'both',
                currency = 'USD',
                account = 'Income - Ordinary Dividends',
                description = f"Income - {symbols}",
                contact_name = '',
                debit = None,
                credit = total_amount,
                project_name = '',
                status = 'published',
                exchange_rate = '',
                account_code = None
            )
            _return_value.append(_row)

            journal_number += 1

        return _return_value

    def write(self) -> dict[str, Optional[Path]]:
        """Write dividend journal entries to CSV file."""
        return {
            "dividends": write_journal_entries(self.journal_entries, self._file_location.dividend_file)
        }

    def pprint(self, log: bool = False) -> None:

        output_lines: list[str] = []

        output_lines.append(f"{self.__repr__()}")
        output_lines.append("-" * 130)

        _header = (
            f"Payment Count: {len(self.entries)}\n"
            f"Entry Count: {len(self._income_by_date)}\n"
            f"Total Income: {self.total_income:,.2f}\n"
            f"Income File: {self._file_location.income_file}\n"
            f"Dividend File: {self._file_location.dividend_file}"
        )

        output_lines.append(_header)
        output_lines.append("-" * 130)

        entries = self.journal_entries

        output_lines.append(f"{'Date':<12} {'Journal #':<12} {'Description':<35} {'Account':<40} {'Debit':>12} {'Credit':>12}")
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
                desc_display = e.description[:33] + ".." if e.description and len(e.description) > 35 else (e.description or "")
                account_display = e.account[:38] + ".." if len(e.account) > 40 else e.account
                output_lines.append(
                    f"{str(e.journal_date):<12} {e.journal_number:<12} {desc_display:<35} {account_display:<40} {debit_str:>12} {credit_str:>12}"
                )
            output_lines.append("-" * 130)
            total_debit = sum(e.debit for e in entries if e.debit)
            total_credit = sum(e.credit for e in entries if e.credit)
            output_lines.append(f"{'Total':<102} {total_debit:>12,.2f} {total_credit:>12,.2f}")

        output = "\n".join(output_lines)
        print(output)

        if log:
            write_log(output, self._file_location.log_file)

        return None

    def __len__(self) -> int:
        return len(self._entries)

    def __iter__(self) -> Iterator[IncomeTransaction]:
        return iter(self._entries)

    def __str__(self) -> str:
        return f"{self._file_location.income_file}"

    def __float__(self) -> float:
        return self.total_income

    def __repr__(self) -> str:
        """String representation of Income."""
        return f"Income(FileLocation(year={self.year}, month={self.month}, root='{self._file_location.root}'))"

if __name__ == '__main__':
    _income = Income(FileLocation(2025, 9, root='/Users/mick/GitHub/mjfii/mmm-accounting-agent-py'))
    _income.pprint()
