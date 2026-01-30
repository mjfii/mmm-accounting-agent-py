import csv
from pathlib import Path
from typing import Optional

from srcx.datasets.journal_entry import JournalEntry


def write_journal_entries(entries: list[JournalEntry], file_path: Path) -> Optional[Path]:
    """
    Write journal entries to a CSV file.

    Args:
        entries: List of JournalEntry objects to write
        file_path: Path to the output CSV file

    Returns:
        The file path if entries were written, None if entries list was empty
    """
    if not entries:
        return None

    file_path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        'Journal Date', 'Reference Number', 'Journal Number Prefix',
        'Journal Number Suffix', 'Notes', 'Journal Type', 'Currency',
        'Account', 'Description', 'Contact Name', 'Debit', 'Credit',
        'Project Name', 'Status', 'Exchange Rate'
    ]

    with open(file_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for entry in entries:
            row = {
                'Journal Date': str(entry.journal_date),
                'Reference Number': entry.reference_number,
                'Journal Number Prefix': entry.journal_number_prefix,
                'Journal Number Suffix': entry.journal_number_suffix,
                'Notes': entry.notes or '',
                'Journal Type': entry.journal_type,
                'Currency': entry.currency,
                'Account': entry.account,
                'Description': entry.description or '',
                'Contact Name': entry.contact_name or '',
                'Debit': entry.debit if entry.debit else '',
                'Credit': entry.credit if entry.credit else '',
                'Project Name': entry.project_name or '',
                'Status': entry.status,
                'Exchange Rate': entry.exchange_rate or ''
            }
            writer.writerow(row)

    return file_path
