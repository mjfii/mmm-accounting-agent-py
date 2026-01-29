import csv
from csv import DictReader
from datetime import date
from pathlib import Path
from srcx.common.file_location import FileLocation


class Summary:
    """
    Represents account summary data for a statement period.

    Hydrates from a SUM CSV file which contains a single record with
    period and year-to-date account values.
    """
    def __init__(self, file_location: FileLocation) -> None:
        """
        Initialize Summary for a specific month and year.
        """
        self._file_location = file_location
        self._load_from_csv(self._file_location.summary_file)

    def _load_from_csv(self, csv_path: Path) -> None:
        """Load summary data from CSV file."""
        if not csv_path.exists():
            raise FileNotFoundError(f"CSV file not found: {csv_path}")

        with open(csv_path, 'r', encoding='utf-8') as f:
            reader: DictReader[str] = csv.DictReader(f)
            rows = [row for row in reader if any(row.values())]

            if len(rows) == 0:
                raise ValueError(f"CSV file has no data rows: {csv_path}")

            if len(rows) > 1:
                raise ValueError(f"CSV file has multiple data rows (expected 1): {csv_path}")

            row = rows[0]
            self._period_start = date.fromisoformat(row['period_start'])
            self._period_end = date.fromisoformat(row['period_end'])
            self._beginning_value_period = float(row['beginning_value_period'])
            self._additions_period = float(row['additions_period'])
            self._subtractions_period = float(row['subtractions_period'])
            self._change_investment_value_period = float(row['change_investment_value_period'])
            self._ending_value_period = float(row['ending_value_period'])
            self._beginning_value_ytd = float(row['beginning_value_ytd'])
            self._additions_ytd = float(row['additions_ytd'])
            self._subtractions_ytd = float(row['subtractions_ytd'])
            self._change_investment_value_ytd = float(row['change_investment_value_ytd'])
            self._ending_value_ytd = float(row['ending_value_ytd'])
            self._income_period = float(row['income_period'])
            self._income_ytd = float(row['income_ytd'])

    @property
    def year(self) -> int:
        return self._year

    @property
    def month(self) -> int:
        return self._month

    @property
    def period_start(self) -> date:
        return self._period_start

    @property
    def period_end(self) -> date:
        return self._period_end

    @property
    def beginning_value_period(self) -> float:
        return self._beginning_value_period

    @property
    def additions_period(self) -> float:
        return self._additions_period

    @property
    def subtractions_period(self) -> float:
        return self._subtractions_period

    @property
    def change_investment_value_period(self) -> float:
        return self._change_investment_value_period

    @property
    def ending_value_period(self) -> float:
        return self._ending_value_period

    @property
    def income_period(self) -> float:
        return self._income_period

    @property
    def unrealized_gains(self) -> float:
        return self.change_investment_value_period - self.income_period

    @property
    def validated(self) -> bool:
        if (self.beginning_value_period + self.additions_period +
            self.subtractions_period + self.income_period +
            self.unrealized_gains) == self.ending_value_period:
            return True
        else: return False

    def __str__(self):
        return f"{self._file_location.summary_file}"

    def __float__(self):
        return self.ending_value_period

    def __repr__(self) -> str:
        """String representation of Summary."""
        return (
            f"Summary(\n"
            f"  period start = {self.period_start},\n"
            f"  period end = {self.period_end},\n"
            f"  beginning value = ${self.beginning_value_period:,.2f},\n"
            f"  additions = ${self.additions_period:,.2f},\n"
            f"  subtractions = ${self.subtractions_period:,.2f},\n"
            f"  change in value = ${self.change_investment_value_period:,.2f},\n"
            f"  dividends = ${self.income_period:,.2f},\n"
            f"  unrealized gains = ${self.unrealized_gains:,.2f},\n"
            f"  ending value = ${self.ending_value_period:,.2f},\n"
            f"  validated = {self.validated}\n"
            f")"
        )

if __name__ == '__main__':
    _summary = Summary(FileLocation(2025, 9))
    print(repr(_summary))
