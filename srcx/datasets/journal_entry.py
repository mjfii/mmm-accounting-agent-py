from dataclasses import dataclass
from datetime import date
from typing import Optional


@dataclass
class JournalEntry:
    # return [
    #     'Journal Date', 'Reference Number', 'Journal Number Prefix',
    #     'Journal Number Suffix', 'Notes', 'Journal Type', 'Currency',
    #     'Account', 'Description', 'Contact Name', 'Debit', 'Credit',
    #     'Project Name', 'Status', 'Exchange Rate'
    # ]
    journal_date: date
    reference_number: str
    journal_number_prefix: str
    journal_number_suffix: str
    notes: Optional[str]
    journal_type: str
    currency: str
    account: str
    description: Optional[str]
    contact_name: Optional[str]
    debit: Optional[float]
    credit: Optional[float]
    project_name: Optional[str]
    status: str
    exchange_rate: Optional[str]
    account_code: Optional[str]

    @property
    def journal_number(self) -> str:
        return f"{self.journal_number_prefix}{self.journal_number_suffix}"

    @property
    def amount(self) -> float:
        return self.debit if self.debit else (self.credit if self.credit else 0.0)

    def __str__(self):
        """Return a formatted string for this journal entry."""
        debit_str = f"{self.debit:,.2f}" if self.debit else ""
        credit_str = f"{self.credit:,.2f}" if self.credit else ""
        return (
            f"  journal number = {self.journal_number}"
            f"  date = {self.journal_date}"
            f"  reference = {self.reference_number}"
            f"  account = {self.account}"
            f"  description = {self.description}"
            f"  debit = {debit_str}"
            f"  credit = {credit_str}"
            f"  status = {self.status}"
            f")"
        )
