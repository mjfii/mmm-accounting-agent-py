from typing import Optional
from pathlib import Path
import srcx.common as cmn
from srcx.hydrators import Summary
from srcx.hydrators import Income
from srcx.hydrators import Activity

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

    @property
    def summary(self) -> Summary:
        return self._summary

    @property
    def income(self) -> Income:
        return self._income

    @property
    def activity(self) -> Activity:
        return self._activity

    def write(self) -> dict[str, Optional[Path]]:
        _return_value: dict[str, Optional[Path]] = {}
        _return_value.update(self.income.write())
        _return_value.update(self.activity.write())
        return _return_value

    def pprint(self, log: bool = False):
        print()
        self.summary.pprint(log=log)
        self.income.pprint(log=log)
        self.activity.pprint(log=log)

if __name__ == '__main__':
    _statement = Statement(2025, 9)
    _statement.pprint()
