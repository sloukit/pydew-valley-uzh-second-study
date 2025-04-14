from dataclasses import dataclass, field

from src.enums import SeedType
from src.settings import Coordinate


def _none():
    return None


@dataclass
class PlantInfo:
    plant_type: SeedType
    age: int = field(default=0)

    def __post_init__(self):
        if self.age < 0:
            raise ValueError("corrupt save file: plants cannot have a negative age")

    def __json__(self):
        """Return self in a JSON-serialisable format."""
        return {"plant_type": self.plant_type.value, "age": self.age}


@dataclass
class TileInfo:
    watered: bool
    pos: Coordinate
    plant_info: PlantInfo | None = field(default=None)

    def __json__(self):
        """Return self in a JSON-serialisable format."""
        return {
            "watered": self.watered,
            "pos": self.pos,
            "plant_info": getattr(self.plant_info, "__json__", _none)(),
        }
