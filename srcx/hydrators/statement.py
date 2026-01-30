from typing import Optional, Union
from pathlib import Path
import srcx.common as cmn
from srcx.hydrators import Summary
from srcx.hydrators import Income
from srcx.hydrators import Activity
from srcx.hydrators import Holdings
from srcx.datasets.journal_entry import JournalEntry
from srcx.common.journal_writer import write_journal_entries

class Statement(object):
    """
    Represents account summary data for a statement period.

    Hydrates from a SUM CSV file which contains a single record with
    period and year-to-date account values.
    """
    def __init__(self, year: int, month: int) -> None:
        self._file_location = cmn.FileLocation(year=year, month=month, root='/Users/mick/GitHub/mjfii/mmm-accounting-agent-py')
        self._summary = Summary(self._file_location)
        self._income = Income(self._file_location)
        self._activity = Activity(self._file_location)
        self._holdings = Holdings(self._file_location)

    @property
    def summary(self) -> Summary:
        return self._summary

    @property
    def income(self) -> Income:
        return self._income

    @property
    def activity(self) -> Activity:
        return self._activity

    @property
    def holdings(self) -> Holdings:
        return self._holdings

    @property
    def journal_entries(self) -> Union[list[JournalEntry], None]:
        """Aggregate all journal entries from income, activity, and holdings."""
        all_entries: list[JournalEntry] = []

        # Add dividend entries
        if self.income.journal_entries:
            all_entries.extend(self.income.journal_entries)

        # Add purchase entries
        if self.activity.purchase_journal_entries:
            all_entries.extend(self.activity.purchase_journal_entries)

        # Add sale entries
        if self.activity.sale_journal_entries:
            all_entries.extend(self.activity.sale_journal_entries)

        # Add unrealized entries
        if self.holdings.journal_entries:
            all_entries.extend(self.holdings.journal_entries)

        return all_entries if all_entries else None

    def write(self) -> dict[str, Optional[Path]]:
        _return_value: dict[str, Optional[Path]] = {}
        _return_value.update(self.income.write())
        _return_value.update(self.activity.write())
        _return_value.update(self.holdings.write())
        # Write combined entries file
        _return_value['entries'] = write_journal_entries(self.journal_entries, self._file_location.entries_file)
        return _return_value

    def pprint(self, log: bool = False):
        if log:
            log_file = self._file_location.log_file
            if log_file.exists():
                log_file.unlink()
        print()
        self.summary.pprint(log=log)
        self.income.pprint(log=log)
        self.activity.pprint(log=log)
        self.holdings.pprint(log=log)

if __name__ == '__main__':
    _statement = Statement(2025, 9)
    _statement.pprint()
