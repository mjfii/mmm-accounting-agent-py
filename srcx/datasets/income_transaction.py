from dataclasses import dataclass
from datetime import date
from typing import Optional


@dataclass
class IncomeTransaction:
    """Represents a single income transaction entry."""
    settlement_date: date
    security_name: str
    symbol: str
    cusip: str
    description: str
    quantity: Optional[float]
    price: Optional[float]
    amount: float
