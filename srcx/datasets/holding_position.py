from dataclasses import dataclass
from typing import Optional


@dataclass
class HoldingPosition:
    """Represents a single holding position from the holdings scrape."""
    symbol: str
    description: str
    quantity: float
    price: float
    beginning_value: Optional[float]
    ending_value: float
    cost_basis: Optional[float]
    unrealized_gain: Optional[float]
