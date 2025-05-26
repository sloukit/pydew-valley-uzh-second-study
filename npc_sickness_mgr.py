"""Sickness timing logic.

For any given player, all NPCs' status will be computed in advance
so that when the eruption happens, the game doesn't have to pick which NPCs will
get sick and whether they will die or recover on the fly.

For adhering NPCs, it will also be decided when the NPCs go to the bathhouse this way."""

from collections import deque
from dataclasses import dataclass
from math import ceil, floor
from random import randint, random, sample
from typing import Callable

from src.enums import NPCSicknessStatusChange

# Used to sample NPC IDs when selecting which NPCs adhere or not.
_INGRP_ID_SAMPLING_LST = list(range(12))
_INGRP_ID_SAMPLING = set(_INGRP_ID_SAMPLING_LST)
_OUTGRP_ID_SAMPLING_LST = list(range(12, 24))
_OUTGRP_ID_SAMPLING = set(_OUTGRP_ID_SAMPLING_LST)

# Number of NPCs per group.
_ID_POOL_SIZE = 12
# Proportion of adhering NPCs in the ingroup during the "adherence" condition
_ADHERENCE_INGRP_COUNT = _ID_POOL_SIZE * 0.8
# Proportion of adhering NPCs in the ingroup during the "non-adherence" condition.
_REBEL_ADHERENCE_INGRP_COUNT = _ID_POOL_SIZE * 0.2
# Halve the NPC count for NPC adherence in the outgroup.
_ADHERENCE_OUTGRP_COUNT = _ID_POOL_SIZE // 2

# Sentinel object returned if an NPC doesn't die.
_WILL_NOT_DIE = object()


def _get_ingrp_adhering_count(adherence: bool = False):
    """Return the exact number of NPCs adhering to the health measures in the ingroup.
    Since exact proportions might equal non-integer numbers, the number is randomly selected between the
    ceiling and floor of the exact count for the given condition."""

    exact_nb = _ADHERENCE_INGRP_COUNT if adherence else _REBEL_ADHERENCE_INGRP_COUNT

    return randint(floor(exact_nb), ceil(exact_nb))


@dataclass
class NPCSicknessStatus:
    """Represents any status change in an NPC's sickness in any given round."""

    npc_id: int
    round_no: int
    timestamp: float
    change_type: NPCSicknessStatusChange


def _get_death(npc_id: int, used_death_rounds: set) -> NPCSicknessStatus | object:
    """Define a death timestamp for a certain NPC id."""
    if random() < 0.5:
        return _WILL_NOT_DIE

    # Define the death round.
    death_round = randint(7, 12)
    while death_round in used_death_rounds:
        # Attempt to get another one if an NPC already dies during this round.
        death_round = randint(7, 12)
    used_death_rounds.add(death_round)

    base_tstamp = 300 * randint(1, 2)
    final_tstamp = base_tstamp + 200 * random()

    return NPCSicknessStatus(
        npc_id, death_round, final_tstamp, NPCSicknessStatusChange.DIE
    )


class NPCSicknessManager:
    def __init__(self, get_round: Callable[[], int], adherence: bool = False):
        self.get_round = get_round
        self.adherence = adherence
        self._ingrp_adhering_ids = set()
        self._outgrp_adhering_ids = set()
        self.computed_status_changes = {n: deque() for n in range(7, 13)}

    def _compute_npc_status(self):
        # TODO: continue this
        status_changes = {n: [] for n in range(7, 13)}  # noqa

        # For each group, select which NPCs are going to die first.
        death_eligible_ingrp_npcs = _INGRP_ID_SAMPLING.difference(  # noqa
            self._ingrp_adhering_ids
        )
        death_eligible_outgrp_npcs = _OUTGRP_ID_SAMPLING.difference(  # noqa
            self._outgrp_adhering_ids
        )

    def select_adhering_npcs(self):
        """Determine which NPCs adhere to the health measures.

        The adherence parameter only affects the ingroup.
        The outgroup always has a 50/50 proportion of adherence."""
        self._ingrp_adhering_ids = set(
            sample(_INGRP_ID_SAMPLING_LST, _get_ingrp_adhering_count(self.adherence))
        )
        self._outgrp_adhering_ids = set(
            sample(_OUTGRP_ID_SAMPLING_LST, _ADHERENCE_OUTGRP_COUNT)
        )
