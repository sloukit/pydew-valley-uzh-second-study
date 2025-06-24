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
    timing_for_bathhouse: float = field(default=0.0)
    going_to_bathhouse: bool = field(default=False)

    def set_behaviour(self, new_behaviour):
        self.npc.conditional_behaviour_tree = new_behaviour
