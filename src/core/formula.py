from dataclasses import dataclass

@dataclass
class Formula:
    id: str
    name_zh: str
    formula_str: str
    latex_str: str = ""

    @property
    def left_side(self) -> str:
        if "=" in self.formula_str:
            return self.formula_str.split("=")[0].strip()
        return self.formula_str

    @property
    def right_side(self) -> str:
        if "=" in self.formula_str:
            return self.formula_str.split("=")[1].strip()
        return ""
