from enum import Enum

from pathfinding.core.grid import Grid

from src.npc.behaviour.ai_behaviour_tree_base import (
    Action,
    Condition,
    NodeWrapper,
    Selector,
    Sequence,
)
from src.npc.behaviour.cow_behaviour_tree import CowIndividualContext, player_nearby
from src.npc.setup import AIData
from src.npc.utils import pf_wander
from src.settings import SCALED_TILE_SIZE


class CowHerdingContext:
    barn_grid: Grid = None
    default_grid: Grid = None
    range_grid: Grid = None


def wander_barn(context: CowIndividualContext) -> bool:
    return pf_wander(context.cow, pf_grid=CowHerdingContext.barn_grid)


def wander_range(context: CowIndividualContext) -> bool:
    return pf_wander(context.cow, pf_grid=CowHerdingContext.range_grid)


def flee_from_player(context: CowIndividualContext) -> bool:
    return context.cow.flee_from_pos(
        (
            AIData.player.rect.centerx / SCALED_TILE_SIZE,
            AIData.player.rect.centery / SCALED_TILE_SIZE,
        ),
        pf_grid=CowHerdingContext.default_grid,
    )


class CowHerdingBehaviourTree(NodeWrapper, Enum):
    WanderBarn = Selector(Action(wander_barn))
    WanderRange = Selector(Action(wander_range))
    Flee = Selector(Sequence(Condition(player_nearby), Action(flee_from_player)))
