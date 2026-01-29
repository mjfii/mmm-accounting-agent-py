from dataclasses import dataclass
from datetime import date
from typing import Optional


@dataclass
class ActivityTransaction:
    """Represents a single securities activity transaction entry (buy/sell)."""
    settlement_date: date
    action: str
    symbol: str
    security_name: str
    quantity: float
    price: float
    amount: float
    transaction_cost: Optional[float]
    basket: Optional[str]
    cost_basis: Optional[float]
