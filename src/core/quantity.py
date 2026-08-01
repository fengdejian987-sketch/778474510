from dataclasses import dataclass

@dataclass
class PhysicalQuantity:
    id: str
    symbol: str
    name_zh: str
    dimension: str  # e.g. 'M', 'L', 'T', or combined like 'ML2T-2'
    unit: str

    def __repr__(self):
        return f"<Quantity {self.symbol} ({self.name_zh}) [{self.dimension}]>" ,
