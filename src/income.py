"""Income class for reading and managing INC scrape files."""

import csv
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import List, Optional


@dataclass
class IncomeTransaction:
    """Represents a single income transaction (dividend, interest, etc.)."""

    settlement_date: date
    security_name: str
    symbol: str
    cusip: str
    description: str
    quantity: Optional[float]
    price: Optional[float]
    amount: float

    @property
    def is_reinvestment(self) -> bool:
        """Check if this transaction is a reinvestment."""
        return 'Reinvestment' in self.description

    @classmethod
    def from_csv_row(cls, row: dict) -> 'IncomeTransaction':
        """Create an IncomeTransaction instance from a CSV row dictionary."""
        return cls(
            settlement_date=date.fromisoformat(row['settlement_date']),
            security_name=row['security_name'],
            symbol=row['symbol'],
            cusip=row['cusip'],
            description=row['description'],
            quantity=float(row['quantity']) if row['quantity'] else None,
            price=float(row['price']) if row['price'] else None,
            amount=float(row['amount'])
        )


class Income:
    """Manages income transaction data from INC CSV files."""

    def __init__(self, csv_path: Optional[Path] = None):
        """
        Initialize Income container.

        Args:
            csv_path: Optional path to CSV file to load on initialization
        """
        self.transactions: List[IncomeTransaction] = []
        if csv_path:
            self.load_from_csv(csv_path)

    def load_from_csv(self, csv_path: Path) -> None:
        """
        Load income transactions from a CSV file.

        Args:
            csv_path: Path to the INC CSV file

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
                self.transactions.append(IncomeTransaction.from_csv_row(row))

    @property
    def amount(self) -> float:
        """Calculate total amount across all income transactions, excluding reinvestments."""
        return sum(t.amount for t in self.transactions if not t.is_reinvestment)

    def __len__(self) -> int:
        """Return the number of income transactions."""
        return len(self.transactions)

    def __iter__(self):
        """Iterate over income transactions."""
        return iter(self.transactions)

    def __repr__(self) -> str:
        """String representation of Income."""
        return f"Income(count={len(self.transactions)})"
