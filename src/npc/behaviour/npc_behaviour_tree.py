from __future__ import annotations

import random
from enum import Enum
from typing import Callable

import pygame

from src.enums import Direction, FarmingTool, ItemToUse, Map, StudyGroup
from src.npc.behaviour.ai_behaviour_tree_base import (
    Action,
    Condition,
    NodeWrapper,
    Selector,
    Sequence,
)
from src.npc.behaviour.context import NPCIndividualContext, NPCSharedContext
from src.npc.utils import pf_move_to, pf_wander
from src.settings import SCALED_TILE_SIZE
from src.sprites.objects.tree import Tree
from src.support import distance, near_tiles


def walk_to_pos(
    context: NPCIndividualContext,
    target_position: tuple[int, int],
    on_path_completion: Callable[[], None] = None,
):
    """
    :return: True if path has successfully been created, otherwise False
    """

    if target_position in NPCSharedContext.targets:
        return False

    if pf_move_to(context.npc, target_position):
        if len(context.npc.pf_path) > 1:
            facing = (
                context.npc.pf_path[-1][0] - context.npc.pf_path[-2][0],
                context.npc.pf_path[-1][1] - context.npc.pf_path[-2][1],
            )
        else:
            facing = (
                context.npc.pf_path[-1][0]
                - context.npc.rect.centerx / SCALED_TILE_SIZE,
                context.npc.pf_path[-1][1]
                - context.npc.rect.centery / SCALED_TILE_SIZE,
            )

        facing = (facing[0], 0) if abs(facing[0]) > abs(facing[1]) else (0, facing[1])

        NPCSharedContext.targets.add(target_position)

        @context.npc.on_path_completion
        def _():
            context.npc.direction.update(facing)
            context.npc.get_facing_direction()
            context.npc.direction.update((0, 0))

            if on_path_completion is not None:
                on_path_completion()

        @context.npc.on_stop_moving
        def _():
            NPCSharedContext.targets.discard(target_position)

        return True
    return False


def wander(context: NPCIndividualContext) -> bool:
    return pf_wander(context.npc)


# region Logic for farm NPCs to potentially "leave the map" and come back to go to the bathhouse
def will_leave_farm_for_bathhouse(context: NPCIndividualContext) -> bool:
    shared_ctx = NPCSharedContext
    current_round = shared_ctx.get_round()
    is_rnd_7 = current_round == 7
    return (
        context.adhering_to_measures
        and shared_ctx.current_map == Map.NEW_FARM
        and current_round >= 7
        and shared_ctx.get_rnd_timer() >= 30 * is_rnd_7
        and not context.going_to_bathhouse
    )


def go_to_bathhouse(context: NPCIndividualContext) -> bool:
    context.timing_for_bathhouse = NPCSharedContext.get_rnd_timer()
    context.going_to_bathhouse = True
    is_outgrp = context.npc.study_group == StudyGroup.OUTGROUP
    return walk_to_pos(
        context,
        (24 + 30 * is_outgrp, 40),
        lambda: print("Finished" if __debug__ else None),
    )


def will_return_to_farm_from_bathhouse(context: NPCIndividualContext) -> bool:
    shared_ctx = NPCSharedContext
    is_outgrp = context.npc.study_group == StudyGroup.OUTGROUP
    return (
        context.adhering_to_measures
        and context.going_to_bathhouse
        and shared_ctx.current_map == Map.NEW_FARM
        and context.npc.get_tile_pos() == (24 + 30 * is_outgrp, 40)
        and shared_ctx.get_rnd_timer() - context.timing_for_bathhouse >= 45
    )


def _reset_state_to_normal(context: NPCIndividualContext, behaviour):
    context.going_to_bathhouse = False
    context.set_behaviour(behaviour)


def return_from_bathhouse_farm(context: NPCIndividualContext):
    is_outgrp = context.npc.study_group == StudyGroup.OUTGROUP
    return walk_to_pos(
        context,
        (17 + 44 * is_outgrp, 27),
        lambda: _reset_state_to_normal(context, NPCBehaviourTree.FARMING),
    )


# endregion


# region Forest-NPC logic to go to the bathhouse
def will_leave_forest_for_bathhouse(context: NPCIndividualContext) -> bool:
    shared_ctx = NPCSharedContext
    current_round = shared_ctx.get_round()
    is_rnd_7 = current_round == 7
    return (
        context.adhering_to_measures
        and shared_ctx.current_map == Map.FOREST
        and current_round >= 7
        and shared_ctx.get_rnd_timer() >= 30 * is_rnd_7
        and not context.going_to_bathhouse
    )


def go_to_bathhouse_forest(context: NPCIndividualContext):
    context.timing_for_bathhouse = NPCSharedContext.get_rnd_timer()
    return walk_to_pos(
        context, (9, 18), lambda: print("Finished moving") if __debug__ else None
    )


def will_return_to_forest(context: NPCIndividualContext):
    position = context.npc.get_tile_pos()
    return (
        context.adhering_to_measures
        and NPCSharedContext.current_map == Map.FOREST
        and position[0] <= 9
        and position[1] == 18
        and NPCSharedContext.get_rnd_timer() - context.timing_for_bathhouse >= 45
        and context.going_to_bathhouse
    )


def return_from_bathhouse_forest(context: NPCIndividualContext):
    context.going_to_bathhouse = False
    return walk_to_pos(
        context, (10, 18), _reset_state_to_normal(context, NPCBehaviourTree.WOODCUTTING)
    )


# endregion


# region "Go to bathhouse" logic for town map
def will_leave_to_bathhouse(context: NPCIndividualContext) -> bool:
    shared_ctx = NPCSharedContext
    current_round = shared_ctx.get_round()
    is_rnd_7 = current_round == 7
    return (
        context.adhering_to_measures
        and current_round >= 7
        and shared_ctx.current_map == Map.TOWN
        and shared_ctx.get_rnd_timer() >= 30 * is_rnd_7
        and not context.going_to_bathhouse
    )


def go_to_bathhouse_town(context: NPCIndividualContext) -> bool:
    return walk_to_pos(
        context, (54, 43), lambda: print("Finished moving") if __debug__ else None
    )


def will_leave_bathhouse(context: NPCIndividualContext):
    shared_ctx = NPCSharedContext
    return (
        context.adhering_to_measures
        and context.going_to_bathhouse
        and shared_ctx.current_map == Map.TOWN
        and shared_ctx.get_rnd_timer() - context.timing_for_bathhouse >= 30
    )


def leave_bathhouse(context: NPCIndividualContext):
    return walk_to_pos(
        context,
        (55, 22),
        lambda: _reset_state_to_normal(context, NPCBehaviourTree.FARMING),
    )


# endregion


# region farming-exclusive logic
def will_farm(context: NPCIndividualContext) -> bool:
    """
    2 in 3 chance to go farming instead of wandering around
    :return: 2/3 true | 1/3 false
    """
    if context.npc.is_sick:
        return False

    return random.randint(0, 2) < 2


def will_harvest_plant(context: NPCIndividualContext) -> bool:
    """
    :return: True: harvestable plants available AND 1/3, otherwise False
    """
    return len(context.npc.soil_area.harvestable_tiles) and random.randint(0, 2) == 2


def harvest_plant(context: NPCIndividualContext) -> bool:
    """
    Finds a random harvestable tile in a radius of 10 around the
    NPC, makes the NPC walk to and harvest it.
    :return: True if such a Tile has been found and the NPC successfully
             created a path towards it, otherwise False
    """
    harvestable_tiles = context.npc.get_personal_soil_area_tiles("harvestable")
    if not len(harvestable_tiles):
        return False

    radius = 10

    tile_coord = context.npc.get_tile_pos()

    loop_count = 0
    for pos in near_tiles(tile_coord, radius, shuffle=True):
        if pos in harvestable_tiles:
            path_created = walk_to_pos(context, pos)
            if path_created:
                return True
            loop_count += 1
            if loop_count > 5:
                break

    return False


def will_create_new_farmland(context: NPCIndividualContext) -> bool:
    """
    :return: True: untilled farmland available AND
    (all other farmland planted and watered OR 1/3), otherwise False
    """
    if context.npc.is_sick:
        return False

    untilled_tiles = context.npc.get_personal_soil_area_tiles("untilled")
    if not untilled_tiles:
        return False

    unplanted_farmland_available = len(
        context.npc.get_personal_soil_area_tiles("unplanted")
    )
    unwatered_farmland_available = len(
        context.npc.get_personal_soil_area_tiles("unwatered")
    )

    return (
        unplanted_farmland_available == 0 and unwatered_farmland_available == 0
    ) or random.randint(0, 2) == 0


def create_new_farmland(context: NPCIndividualContext) -> bool:
    """
    Finds a random untilled but farmable tile, that is adjacent to farmed tiles,
    makes the NPC walk to and till it.
    Will prefer Tiles that are adjacent to already tilled Tiles in 6/7 of
    all cases. Will prefer Tiles within a 10 tile radius around the NPC.
    :return: True if such a Tile has been found and the NPC successfully
             created a path towards it, otherwise False
    """
    untilled_tiles = context.npc.get_personal_adjacent_untilled_tiles()
    if not untilled_tiles:
        return False

    radius = 10

    # current NPC position on the tilemap
    tile_coord = context.npc.get_tile_pos()

    weighted_coords = []
    coords = []

    for pos in near_tiles(tile_coord, radius):
        if pos in untilled_tiles:
            if context.npc.soil_area.tiles.get(pos).pf_weight:
                weighted_coords.append(pos)
            else:
                coords.append(pos)

    w_coords: list[tuple[float, tuple[int, int]]] = []

    for pos in weighted_coords:
        w_coords.append((1 * len(weighted_coords), pos))

    for pos in coords:
        w_coords.append((7 * len(coords), pos))

    order = sorted(
        range(len(w_coords)), key=lambda i: random.random() ** (1.0 / w_coords[i][0])
    )

    def on_path_completion():
        if context.npc.is_sick:
            return False

        context.npc.tool_active = True
        context.npc.current_tool = FarmingTool.HOE
        context.npc.tool_index = context.npc.current_tool.value - 1
        context.npc.frame_index = 0

    loop_count = 0
    for pos in order:
        path_created = walk_to_pos(
            context, w_coords[pos][1], on_path_completion=on_path_completion
        )
        if path_created:
            return True
        loop_count += 1
        if loop_count > 5:
            break

    loop_count = 0
    for pos in sorted(
        untilled_tiles,
        key=lambda tile: distance(tile, tile_coord),
    ):
        path_created = walk_to_pos(context, pos, on_path_completion=on_path_completion)
        if path_created:
            return True
        loop_count += 1
        if loop_count > 5:
            break

    return False


def will_plant_tilled_farmland(context: NPCIndividualContext) -> bool:
    """
    :return: True if unplanted farmland available AND
    (all other farmland watered OR 3/4), otherwise False
    """
    if not len(context.npc.get_personal_soil_area_tiles("unplanted")):
        return False

    unwatered_farmland_available = len(
        context.npc.get_personal_soil_area_tiles("unwatered")
    )

    return unwatered_farmland_available == 0 or random.randint(0, 3) <= 2


def plant_adjacent_or_random_seed(context: NPCIndividualContext) -> bool:
    """
    Finds a random unplanted but tilled tile, makes the NPC walk to and plant
    a seed on it. Prefers tiles within a 10 tile radius around the NPC.
    The seed selected is dependent on the respective amount of planted
    seeds from all seed types, as well as the seed types that have been
    planted on tiles adjacent to the randomly selected tile.
    :return: True if such a Tile has been found and the NPC successfully
             created a path towards it, otherwise False
    """
    soil_layer = context.npc.soil_area
    unplanted_tiles = context.npc.get_personal_soil_area_tiles("unplanted")
    if not len(unplanted_tiles):
        return False

    radius = 10

    tile_coord = context.npc.get_tile_pos()

    def on_path_completion():
        seed_type: FarmingTool | None = None

        # NPCs will only plant a seed from an adjacent tile if every seed
        # type is planted on at least
        # 1/(number of available seed types * 1.5)
        # of all planted tiles
        total_planted = sum(soil_layer.planted_types.values())
        seed_types_count = len(soil_layer.planted_types.keys())

        threshold = total_planted / (seed_types_count * 1.5)

        will_plant_adjacent_seed = not total_planted or all(
            seed_type > threshold for seed_type in soil_layer.planted_types.values()
        )

        if will_plant_adjacent_seed:
            adjacent_seed_types = set()
            for dx, dy in soil_layer.neighbor_directions:
                neighbor_pos = (pos[0] + dx, pos[1] + dy)
                neighbor = soil_layer.tiles.get(neighbor_pos)
                if neighbor and neighbor.plant:
                    neighbor_seed_type = neighbor.plant.seed_type
                    adjacent_seed_types.add(
                        (
                            soil_layer.planted_types[neighbor_seed_type],
                            neighbor_seed_type.as_fts(),
                        )
                    )

            # If multiple adjacent seed types are found, the one that has
            # been planted the least is used
            if adjacent_seed_types:
                seed_type = min(adjacent_seed_types, key=lambda i: i[0])[1]

        # If no adjacent seed type has been found, the type with that has
        # been planted the least is used
        if not seed_type:
            seed_type = min(
                context.allowed_seeds,
                key=lambda x: soil_layer.planted_types[x],
            ).as_fts()

        context.npc.current_seed = seed_type
        context.npc.seed_index = (
            context.npc.current_seed.value - FarmingTool.get_first_seed_id().value
        )
        context.npc.use_tool(ItemToUse.SEED)

    # FIXME: Since path generation has a high performance impact the maximum loop count
    #  is limited to 10. Removing this can cause the game to stutter
    loop_count = 0
    for pos in near_tiles(tile_coord, radius, shuffle=True):
        if pos in unplanted_tiles:
            path_created = walk_to_pos(
                context, pos, on_path_completion=on_path_completion
            )
            if path_created:
                return True
            loop_count += 1
            if loop_count > 5:
                break

    loop_count = 0
    for pos in sorted(unplanted_tiles, key=lambda tile: distance(tile, tile_coord)):
        path_created = walk_to_pos(context, pos, on_path_completion=on_path_completion)
        if path_created:
            return True
        loop_count += 1
        if loop_count > 5:
            break

    return False


def water_farmland(context: NPCIndividualContext) -> bool:
    """
    Finds a random unwatered but planted tile, makes the NPC walk to and water
    it. Prefers tiles within a 10 tile radius around the NPC.
    :return: True if such a Tile has been found and the NPC successfully
             created a path towards it, otherwise False
    """
    unwatered_tiles = context.npc.get_personal_soil_area_tiles("unwatered")
    if not len(unwatered_tiles):
        return False

    radius = 10

    tile_coord = context.npc.get_tile_pos()

    def on_path_completion():
        if context.npc.is_sick:
            return False

        context.npc.tool_active = True
        context.npc.current_tool = FarmingTool.WATERING_CAN
        context.npc.tool_index = context.npc.current_tool.value - 1
        context.npc.frame_index = 0

    loop_count = 0
    for pos in near_tiles(tile_coord, radius):
        if pos in unwatered_tiles:
            path_created = walk_to_pos(
                context, pos, on_path_completion=on_path_completion
            )
            if path_created:
                return True
            loop_count += 1
            if loop_count > 5:
                break

    loop_count = 0
    for pos in sorted(unwatered_tiles, key=lambda tile: distance(tile, tile_coord)):
        path_created = walk_to_pos(context, pos, on_path_completion=on_path_completion)
        if path_created:
            return True
        loop_count += 1
        if loop_count > 5:
            break

    return False


# endregion


# region woodcutting-exclusive logic
def will_cut_wood(context: NPCIndividualContext) -> bool:
    """
    1 in 5 chance to go woodcutting instead of wandering around
    :return: 1/5 true | 4/5 false
    """
    return random.randint(0, 4) == 0


def direction_to_vector(direction: Direction, invert: bool = False) -> tuple[int, int]:
    """
    Translate a Direction enum member to a movement vector
    :param direction: Direction to use
    :param invert: Whether the returned vector should be inverted
    :return: Movement vector (i.e. (0, -1) for Direction.UP etc.)
    """
    dir_ = (0, 0)
    match direction:
        case Direction.UP:
            dir_ = 0, -1
        case Direction.DOWN:
            dir_ = 0, 1
        case Direction.LEFT:
            dir_ = -1, 0
        case Direction.RIGHT:
            dir_ = 1, 0

    return dir_ if not invert else (-dir_[0], -dir_[1])


def offset_edge_midpoint(
    direction: Direction, rect: pygame.FRect, hitbox_size: tuple[float, float]
) -> tuple[float, float]:
    """
    Calculate the coordinate of the midpoint of an object's edge in the given
    direction, offset by half the given hitbox size.
    :param direction: Direction of the edge
    :param rect: Rect whose edges should be used
    :param hitbox_size: Size of the hitbox by which size the edge midpoint
                        should be offset
    """
    hitbox_size = hitbox_size[0] / 2, hitbox_size[1] / 2
    midpoint = (0, 0)
    match direction:
        case Direction.UP:
            midpoint = rect.centerx, rect.top - hitbox_size[1]
        case Direction.DOWN:
            midpoint = rect.centerx, rect.bottom + hitbox_size[1]
        case Direction.LEFT:
            midpoint = rect.left - hitbox_size[0], rect.centery
        case Direction.RIGHT:
            midpoint = rect.right + hitbox_size[0], rect.centery

    return midpoint


def chop_tree(context: NPCIndividualContext) -> bool:
    """
    Finds a random tree, makes the NPC walk to and chop it. Prefers trees
    within an 8 tile radius around the NPC.
    :return: True if a Tree has been found and the NPC successfully
             created a path towards it, otherwise False
    """
    if not context.npc.tree_sprites:
        return False

    radius = 8

    directions = [Direction.LEFT, Direction.RIGHT]
    random.shuffle(directions)

    trees = [tree for tree in context.npc.tree_sprites if tree.alive]
    random.shuffle(trees)

    def on_path_completion(tree: Tree, direction_: Direction):
        def inner():
            if tree.alive and not context.npc.is_sick:
                context.npc.tool_active = True
                context.npc.current_tool = FarmingTool.AXE
                context.npc.tool_index = context.npc.current_tool.value - 1
                context.npc.frame_index = 0

            context.npc.direction.update(direction_to_vector(direction_, invert=True))
            context.npc.get_facing_direction()
            context.npc.direction.update((0, 0))

        return inner

    first_iteration = True

    for _ in range(2):
        for tree in trees:
            if first_iteration:
                if (
                    distance(tree.hitbox_rect.center, context.npc.hitbox_rect.center)
                    > radius * SCALED_TILE_SIZE
                ):
                    continue
            for direction in directions:
                tree_pos = (
                    int(tree.hitbox_rect.center[0] / SCALED_TILE_SIZE),
                    int(tree.hitbox_rect.center[1] / SCALED_TILE_SIZE),
                )
                tup = direction_to_vector(direction)
                path_created = walk_to_pos(
                    context,
                    (tree_pos[0] + tup[0], tree_pos[1] + tup[1]),
                    on_path_completion=on_path_completion(tree, direction),
                )
                if path_created:
                    tree_edge_coord = offset_edge_midpoint(
                        direction, tree.hitbox_rect, context.npc.hitbox_rect.size
                    )
                    context.npc.create_step_to_coord(tree_edge_coord)
                    return True

        first_iteration = False
    return False


# endregion


# region do nothing
def will_do_nothing(context: NPCIndividualContext) -> bool:
    """
    Certain types of NPCs do not perform any actions.
    """
    return True


def do_nothing(context: NPCIndividualContext) -> bool:
    return True


# endregion


# region for cheering
def will_cheer(context: NPCIndividualContext) -> bool:
    """
    1 in 500 chance to cheer instead of nothing
    :return: 1/500 true | 499/500 false
    """
    return random.randint(0, 499) == 0


def cheer(context: NPCIndividualContext) -> bool:
    context.npc.emote_manager.show_emote(context.npc, "cheer_ani")


# endregion


# region behaviour trees
class NPCBehaviourTree(NodeWrapper, Enum):
    FARMING = Selector(
        Sequence(
            Condition(will_farm),
            Selector(
                Sequence(Condition(will_harvest_plant), Action(harvest_plant)),
                Sequence(
                    Condition(will_create_new_farmland),
                    Action(create_new_farmland),
                ),
                Sequence(
                    Condition(will_plant_tilled_farmland),
                    Action(plant_adjacent_or_random_seed),
                ),
                Action(water_farmland),
            ),
        ),
        Action(wander),
    )

    WOODCUTTING = Selector(
        Sequence(Condition(will_cut_wood), Selector(Action(chop_tree))),
        Action(wander),
    )

    DO_NOTHING = Selector(
        Sequence(Condition(will_do_nothing), Selector(Action(do_nothing))),
        Action(do_nothing),
    )

    CHEER = Selector(
        Sequence(Condition(will_cheer), Selector(Action(cheer))),
        Action(do_nothing),
    )

    FARM_GO_TO_BATHHOUSE = Selector(
        Sequence(
            Condition(will_return_to_farm_from_bathhouse),
            Action(return_from_bathhouse_farm),
        ),
        Sequence(Condition(will_leave_farm_for_bathhouse), Action(go_to_bathhouse)),
        Action(do_nothing),
    )

    FOREST_GO_TO_BATHHOUSE = Selector(
        Sequence(
            Condition(will_return_to_forest), Action(return_from_bathhouse_forest)
        ),
        Sequence(
            Condition(will_leave_forest_for_bathhouse), Action(go_to_bathhouse_forest)
        ),
        Action(do_nothing),
    )

    TOWN_GO_TO_BATHHOUSE = Selector(
        Sequence(Condition(will_leave_bathhouse), Action(leave_bathhouse)),
        Sequence(Condition(will_leave_to_bathhouse), Action(go_to_bathhouse_town)),
        Action(do_nothing),
    )


# endregion
