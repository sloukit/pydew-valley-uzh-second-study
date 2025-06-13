from dataclasses import dataclass, field
from typing import Callable

from src.enums import Map, SeedType
from src.npc.bases.npc_base import NPCBase
from src.npc.behaviour.ai_behaviour_tree_base import Context


class NPCSharedContext:
    targets = set()
    current_map: Map = Map.NEW_FARM
    get_round: Callable[[], int] | None = None
    get_rnd_timer: Callable[[], float] | None = None


@dataclass
class NPCIndividualContext(Context):
    npc: NPCBase
    # list of available seeds depending on game version and round number
    allowed_seeds: list[SeedType] = field(default_factory=list)
    adhering_to_measures: bool = field(default=False)
