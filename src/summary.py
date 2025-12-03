"""Summary class for reading and managing SUM scrape files."""

import csv
from dataclasses import dataclass
from datetime import date
from pathlib import Path


@dataclass
class Summary:
    """Represents account summary data for a statement period."""

    period_start: date
    period_end: date
    beginning_value_period: float
    additions_period: float
    subtractions_period: float
    change_investment_value_period: float
    ending_value_period: float
    beginning_value_ytd: float
    additions_ytd: float
    subtractions_ytd: float
    change_investment_value_ytd: float
    ending_value_ytd: float
    income_period: float
    income_ytd: float

    @classmethod
    def from_csv_row(cls, row: dict) -> 'Summary':
        """Create a Summary instance from a CSV row dictionary."""
        return cls(
            period_start=date.fromisoformat(row['period_start']),
            period_end=date.fromisoformat(row['period_end']),
            beginning_value_period=float(row['beginning_value_period']),
            additions_period=float(row['additions_period']),
            subtractions_period=float(row['subtractions_period']),
            change_investment_value_period=float(row['change_investment_value_period']),
            ending_value_period=float(row['ending_value_period']),
            beginning_value_ytd=float(row['beginning_value_ytd']),
            additions_ytd=float(row['additions_ytd']),
            subtractions_ytd=float(row['subtractions_ytd']),
            change_investment_value_ytd=float(row['change_investment_value_ytd']),
            ending_value_ytd=float(row['ending_value_ytd']),
            income_period=float(row['income_period']),
            income_ytd=float(row['income_ytd'])
        )

    @classmethod
    def from_csv_file(cls, csv_path: Path) -> 'Summary':
        """
        Load summary from a CSV file.

        Args:
            csv_path: Path to the SUM CSV file

        Returns:
            Summary instance

        Raises:
            FileNotFoundError: If the CSV file doesn't exist
            ValueError: If the CSV has no data rows or invalid data
        """
        csv_path = Path(csv_path)
        if not csv_path.exists():
            raise FileNotFoundError(f"CSV file not found: {csv_path}")

        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            # Filter out empty rows (where all values are empty)
            rows = [row for row in reader if any(row.values())]

            if len(rows) == 0:
                raise ValueError(f"CSV file has no data rows: {csv_path}")

            if len(rows) > 1:
                raise ValueError(f"CSV file has multiple data rows (expected 1): {csv_path}")

            return cls.from_csv_row(rows[0])
