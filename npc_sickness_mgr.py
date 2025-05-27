"""Sickness timing logic.

For any given player, all NPCs' status will be computed in advance
so that when the eruption happens, the game doesn't have to pick which NPCs will
get sick and whether they will die or recover on the fly.

For adhering NPCs, it will also be decided when the NPCs go to the bathhouse this way."""

from collections import deque
from dataclasses import dataclass
from itertools import chain
from math import ceil, floor
from random import choice, randint, random, sample
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
_ADHERENCE_OUTGRP_COUNT = _MAXIMUM_DEATH_COUNT = _ID_POOL_SIZE // 2

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


def _get_death(npc_id: int, death_round: int) -> NPCSicknessStatus:
    """Define a death timestamp for a certain NPC id."""

    # Select when the NPC will start being sick, and work out the exact time at which the NPC will die
    # from that. Players and NPCs can only get sick at fixed intervals, i.e. at 5:00 and 10:00 on the in-game timer.
    base_tstamp = 300 * randint(1, 2)
    # Since we don't actually want the NPC to immediately die when it gets sick,
    # we add some randomisation to how long it will survive if it is doomed.
    final_tstamp = base_tstamp + 120 + 180 * random()

    return NPCSicknessStatus(
        npc_id, death_round, final_tstamp, NPCSicknessStatusChange.DIE
    )


def _roll_death_count_for_ingrp(
    current_count: int, current_round: int, adherence: bool
):
    """Roll how many NPCs will die in the ingroup for the current round."""
    if adherence and current_round > 9:
        return 0
    computed = 0
    computed += random() < 0.3
    if (
        current_count + computed < _MAXIMUM_DEATH_COUNT
        and not adherence
        and current_round < 10
    ):
        # Roll a second time if not in the adherence condition,
        # the round allows it, and there are few enough deaths that
        # a successful roll won't go past the maximum death count.
        computed += random() < 0.3
    return computed


def _get_sickness_from_death_evt(orig_evt: NPCSicknessStatus):
    if orig_evt.change_type != NPCSicknessStatusChange.DIE:
        raise ValueError("Given event isn't a death event.")

    orig_tstamp = orig_evt.timestamp
    sickness_tstamp = 300 * (1 + (orig_tstamp > 600))
    return NPCSicknessStatus(
        orig_evt.npc_id,
        orig_evt.round_no,
        sickness_tstamp,
        NPCSicknessStatusChange.SICKNESS
    )


class NPCSicknessManager:
    def __init__(self, get_round: Callable[[], int], adherence: bool = False):
        self.get_round = get_round
        self.adherence = adherence
        self._ingrp_adhering_ids = set()
        self._outgrp_adhering_ids = set()
        self.computed_status_changes: dict[int, deque[NPCSicknessStatus]] = {
            n: deque() for n in range(7, 13)
        }

    def _generate_death_events(self, status_dict: dict):
        """Generate death events for the last 6 rounds."""
        death_eligible_ingrp_npcs = list(
            _INGRP_ID_SAMPLING.difference(  # noqa
                self._ingrp_adhering_ids
            )
        )
        death_eligible_outgrp_npcs = list(
            _OUTGRP_ID_SAMPLING.difference(  # noqa
                self._outgrp_adhering_ids
            )
        )
        ingrp_death_count = 0
        outgrp_death_count = 0
        for rnd in range(7, 13):
            if (
                ingrp_death_count >= _MAXIMUM_DEATH_COUNT
                and outgrp_death_count >= _MAXIMUM_DEATH_COUNT
            ):
                # Stop doing checks if both reached the limit.
                break

            if ingrp_death_count < _MAXIMUM_DEATH_COUNT:
                curr_ingrp_rnd_deaths = _roll_death_count_for_ingrp(
                    ingrp_death_count, rnd, self.adherence
                )
                if curr_ingrp_rnd_deaths:
                    # Don't perform these checks if no NPC was selected to die in the ingroup
                    # for this round.
                    # We can't use "continue" here because the checks still need to be performed
                    # for the outgroup.
                    selected_ids = sample(
                        death_eligible_ingrp_npcs, curr_ingrp_rnd_deaths
                    )
                    for npc_id in selected_ids:
                        status_dict[rnd].append(_get_death(npc_id, rnd))
                        death_eligible_ingrp_npcs.remove(npc_id)
                    ingrp_death_count += curr_ingrp_rnd_deaths

            if outgrp_death_count < _MAXIMUM_DEATH_COUNT:
                kill_another_outgrp_npc = random() < 0.3
                if not kill_another_outgrp_npc:
                    # Checks were already performed for the ingroup, so we can safely
                    # jump to the next loop.
                    continue
                selected_npc_id = choice(death_eligible_outgrp_npcs)
                status_dict[rnd].append(_get_death(selected_npc_id, rnd))
                death_eligible_outgrp_npcs.remove(selected_npc_id)
                outgrp_death_count += kill_another_outgrp_npc

    def _compute_npc_status(self):
        """Calculate all sickness-related status change events
        for NPCs."""
        # TODO: continue this
        status_changes: dict[int, list[NPCSicknessStatus]] = {
            n: [] for n in range(7, 13)
        }  # noqa

        # For each group, select which NPCs are going to die first.
        self._generate_death_events(status_changes)

        # Next, we generate sickness events for NPCs scheduled to die in their death round.
        for death_event in chain.from_iterable(status_changes.values()):
            status_changes[death_event.round_no].append(
                _get_sickness_from_death_evt(death_event)
            )

        # Sort all NPC sickness events by timestamp in each round's list and then put them in the queues in that order.
        for round_no, event_list in status_changes.items():
            event_list.sort(key=lambda evt: evt.timestamp)
            self.computed_status_changes[round_no].extend(event_list)

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
