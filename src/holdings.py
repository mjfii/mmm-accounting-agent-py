"""Holdings class for reading and managing HLD scrape files."""

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional


@dataclass
class Holding:
    """Represents a single holding position from the statement."""

    symbol: str
    description: str
    quantity: float
    price: float
    beginning_value: Optional[float]
    ending_value: float
    cost_basis: Optional[float]
    unrealized_gain: Optional[float]
    change_from_prior_period: Optional[float] = None

    @property
    def is_money_market(self) -> bool:
        """Check if this holding is a money market fund (no cost basis)."""
        return self.cost_basis is None or self.cost_basis == 0.0

    @property
    def change_in_value(self) -> float:
        """
        Calculate change in value based on holding type and available data.

        Logic:
        - If money market fund: 0.0
        - If no beginning_value: ending_value - cost_basis
        - If beginning_value > 0: ending_value - beginning_value
        - Else: 0.0
        """
        if self.is_money_market:
            return 0.0

        if self.beginning_value is None or self.beginning_value == 0.0:
            return self.ending_value - (self.cost_basis if self.cost_basis else 0.0)

        if self.beginning_value > 0.0:
            return self.ending_value - self.beginning_value

        return 0.0

    @classmethod
    def from_csv_row(cls, row: dict) -> 'Holding':
        """Create a Holding instance from a CSV row dictionary."""
        return cls(
            symbol=row['symbol'],
            description=row['description'],
            quantity=float(row['quantity']),
            price=float(row['price']),
            beginning_value=float(row['beginning_value']) if row['beginning_value'] and row['beginning_value'] != 'unavailable' else None,
            ending_value=float(row['ending_value']),
            cost_basis=float(row['cost_basis']) if row['cost_basis'] else None,
            unrealized_gain=float(row['unrealized_gain']) if row['unrealized_gain'] else None,
            change_from_prior_period=float(row['change_from_prior_period']) if 'change_from_prior_period' in row and row['change_from_prior_period'] else None
        )


class Holdings:
    """Manages holdings data from HLD CSV files."""

    def __init__(self, csv_path: Optional[Path] = None):
        """
        Initialize Holdings container.

        Args:
            csv_path: Optional path to CSV file to load on initialization
        """
        self.holdings: List[Holding] = []
        if csv_path:
            self.load_from_csv(csv_path)

    def load_from_csv(self, csv_path: Path) -> None:
        """
        Load holdings from a CSV file.

        Args:
            csv_path: Path to the HLD CSV file

        Raises:
            FileNotFoundError: If the CSV file doesn't exist
            ValueError: If the CSV has invalid data
        """
        csv_path = Path(csv_path)
        if not csv_path.exists():
            raise FileNotFoundError(f"CSV file not found: {csv_path}")

        self.holdings = []
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                self.holdings.append(Holding.from_csv_row(row))

    @property
    def change_in_value(self) -> float:
        """Calculate total change in value across all holdings."""
        return sum(h.change_in_value for h in self.holdings)

    def __len__(self) -> int:
        """Return the number of holdings."""
        return len(self.holdings)

    def __iter__(self):
        """Iterate over holdings."""
        return iter(self.holdings)

    def __repr__(self) -> str:
        """String representation of Holdings."""
        return f"Holdings(count={len(self.holdings)})"