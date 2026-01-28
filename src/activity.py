"""Activity class for reading and managing ACT scrape files."""

import csv
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import List, Optional


@dataclass
class ActivityTransaction:
    """Represents a single securities buy/sell transaction."""

    settlement_date: date
    action: str
    symbol: str
    security_name: str
    quantity: Optional[float]
    price: Optional[float]
    amount: float
    transaction_cost: Optional[float]
    basket: Optional[str]
    cost_basis: Optional[float] = None

    @classmethod
    def from_csv_row(cls, row: dict) -> 'ActivityTransaction':
        """Create an ActivityTransaction instance from a CSV row dictionary."""
        return cls(
            settlement_date=date.fromisoformat(row['settlement_date']),
            action=row['action'],
            symbol=row['symbol'],
            security_name=row['security_name'],
            quantity=float(row['quantity']) if row['quantity'] else None,
            price=float(row['price']) if row['price'] else None,
            amount=float(row['amount']),
            transaction_cost=float(row['transaction_cost']) if row['transaction_cost'] else None,
            basket=row['basket'] if row['basket'] else None,
            cost_basis=float(row['cost_basis']) if row.get('cost_basis') else None
        )


class Activity:
    """Manages securities activity data from ACT CSV files."""

    def __init__(self, csv_path: Optional[Path] = None):
        """
        Initialize Activity container.

        Args:
            csv_path: Optional path to CSV file to load on initialization
        """
        self.transactions: List[ActivityTransaction] = []
        if csv_path:
            self.load_from_csv(csv_path)

    def load_from_csv(self, csv_path: Path) -> None:
        """
        Load activity transactions from a CSV file.

        Args:
            csv_path: Path to the ACT CSV file

        Raises:
            FileNotFoundError: If the CSV file doesn't exist
            ValueError: If the CSV has invalid data
        """
        csv_path = Path(csv_path)
        if not csv_path.exists():
            raise FileNotFoundError(f"CSV file not found: {csv_path}")

        self.transactions = []
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                self.transactions.append(ActivityTransaction.from_csv_row(row))

    def __len__(self) -> int:
        """Return the number of activity transactions."""
        return len(self.transactions)

    def __iter__(self):
        """Iterate over activity transactions."""
        return iter(self.transactions)

    def __repr__(self) -> str:
        """String representation of Activity."""
        return f"Activity(count={len(self.transactions)})"
