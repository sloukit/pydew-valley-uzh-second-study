"""Sickness timing logic.

For any given player, all NPCs' status will be computed in advance
so that when the eruption happens, the game doesn't have to pick which NPCs will
get sick and whether they will die or recover on the fly.

For adhering NPCs, it will also be decided when the NPCs go to the bathhouse this way."""

import asyncio  # noqa: F401
from collections import deque
from dataclasses import dataclass
from itertools import chain
from math import ceil, floor
from random import choice, randint, random, sample
from typing import Callable

from src.enums import NPCSicknessStatusChange
from src.xplat import get_request_with_callback  # noqa: F401

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

_DEATH_LIKELIHOOD = 0.5

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

    def as_dict(self):
        return {
            "npc_id": self.npc_id,
            "timestamp": self.timestamp,
            "change_type": self.change_type.value,
        }


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


def _roll_death():
    return random() < _DEATH_LIKELIHOOD


def _roll_death_count_for_ingrp(
    current_count: int, current_round: int, adherence: bool
):
    """Roll how many NPCs will die in the ingroup for the current round."""
    if adherence and current_round > 9:
        # Force every remaining NPC to survive in this case.
        return 0
    computed = 0
    computed += _roll_death()
    if (
        current_count + computed < _MAXIMUM_DEATH_COUNT
        and not adherence
        and current_round < 10
    ):
        # Roll a second time if not in the adherence condition,
        # the round allows it, and there are few enough deaths that
        # a successful roll won't go past the maximum death count.
        computed += _roll_death()
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
        NPCSicknessStatusChange.SICKNESS,
    )


def _get_sickness(npc_id: int, current_round: int):
    return NPCSicknessStatus(
        npc_id, current_round, randint(1, 2) * 300, NPCSicknessStatusChange.SICKNESS
    )


class NPCSicknessManager:
    def __init__(
        self,
        get_round: Callable[[], int],
        send_telemetry: Callable[[str, dict], None],
        adherence: bool = False,
    ):
        self.get_round = get_round
        self.send_telemetry = send_telemetry
        self.adherence = adherence
        self._ingrp_adhering_ids = set()
        self._outgrp_adhering_ids = set()
        # Using deques so we can pull the events out as time passes in the game.
        self.computed_status_changes: dict[int, deque[NPCSicknessStatus]] = {
            n: deque() for n in range(7, 13)
        }

    def get_status_from_server(self, jwt: str):
        # TODO: add this.
        pass

    # region Sickness event generation (first login)
    def _generate_death_events(
        self,
        status_dict: dict[int, list[NPCSicknessStatus]],
        ingrp_eligible: list[int],
        outgrp_eligible: list[int],
    ):
        """Generate death events for the last 6 rounds."""
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
                    selected_ids = sample(ingrp_eligible, curr_ingrp_rnd_deaths)
                    for npc_id in selected_ids:
                        status_dict[rnd].append(_get_death(npc_id, rnd))
                        ingrp_eligible.remove(npc_id)
                    ingrp_death_count += curr_ingrp_rnd_deaths

            if outgrp_death_count < _MAXIMUM_DEATH_COUNT:
                kill_another_outgrp_npc = _roll_death()
                if not kill_another_outgrp_npc:
                    # Checks were already performed for the ingroup, so we can safely
                    # jump to the next loop.
                    continue
                selected_npc_id = choice(outgrp_eligible)
                status_dict[rnd].append(_get_death(selected_npc_id, rnd))
                outgrp_eligible.remove(selected_npc_id)
                outgrp_death_count += kill_another_outgrp_npc

    def _compute_nonlethal_sickness(
        self,
        status_dict: dict,
        deaths: dict,
        ingrp_sick_eligible: list[int],
        outgrp_sick_eligible: list[int],
        ingrp_adherence_pickable: list[int],
        outgrp_adherence_pickable: list[int],
    ):
        current_ingrp_sick_npcs = []
        current_outgrp_sick_npcs = []
        for rnd in range(7, 13):
            # Selection for the ingroup (non-adhering NPCs)
            if ingrp_sick_eligible:
                for dead_id in deaths[rnd][0]:
                    try:
                        ingrp_sick_eligible.remove(dead_id)
                    except ValueError:
                        pass

                nominal_target_count = (
                    2
                    + 4 * (not self.adherence)
                    + 2 * (not self.adherence and rnd < 10)
                    - len(deaths[rnd][0])
                )

                actual_sample_length = min(
                    len(ingrp_sick_eligible), nominal_target_count
                )
                if actual_sample_length:
                    current_ingrp_sick_npcs = sample(
                        ingrp_sick_eligible, actual_sample_length
                    )
                else:
                    current_ingrp_sick_npcs.clear()

            # Selection for the ingroup (adhering NPCs)
            current_ingrp_adherent = choice(ingrp_adherence_pickable)
            ingrp_adherence_pickable.remove(current_ingrp_adherent)
            current_ingrp_sick_npcs.append(current_ingrp_adherent)

            # Selection for the outgroup (non-adhering NPCs)
            if outgrp_sick_eligible:
                for dead_id in deaths[rnd][1]:
                    try:
                        outgrp_sick_eligible.remove(dead_id)
                    except ValueError:
                        pass

                nominal_target_count = 4 + (rnd < 10) - len(deaths[rnd][1])
                actual_sample_length = min(
                    len(outgrp_sick_eligible), nominal_target_count
                )

                if actual_sample_length:
                    current_outgrp_sick_npcs = sample(
                        outgrp_sick_eligible, actual_sample_length
                    )
                else:
                    current_outgrp_sick_npcs.clear()

            # Selection for the outgroup (adhering NPCs)
            current_outgrp_adherent = choice(outgrp_adherence_pickable)
            outgrp_adherence_pickable.remove(current_outgrp_adherent)
            current_outgrp_sick_npcs.append(current_outgrp_adherent)

            # Generate all the sickness start events in one fell swoop.
            for npc_id in chain(current_ingrp_sick_npcs, current_outgrp_sick_npcs):
                status_dict[rnd].append(_get_sickness(npc_id, rnd))

    def _compute_bathhouse_timings(self, status_dict: dict):
        """Generate bathhouse timings for each adhering NPC in both groups."""
        ingrp_pickable = self._ingrp_adhering_ids
        outgrp_pickable = self._outgrp_adhering_ids
        for rnd in range(7, 13):
            for npc_id in chain(ingrp_pickable, outgrp_pickable):
                # It is assumed an NPC takes 45 seconds to leave the map and come back in all instances.
                if rnd == 7:
                    # Allowed range for bathhouse access: 1 minute (60 seconds) to 5 minutes (300 seconds).
                    # i.e. the allowed timeframe is 240 seconds long.
                    # Since an NPC takes 45 seconds to go to the bathhouse, take the bath and then come back,
                    # the allowed range for NPCs to go to the bathhouse is only 195 seconds long.
                    bathhouse_tstamp = (
                        random() * 195 + 60
                    )  # Add 1 minute to the rolled duration.
                else:
                    # Allowed range in all other rounds: until 3 minutes after round start.
                    # Again, since an NPC takes 45 seconds to go take the bath, that leaves only
                    # 135 seconds worth of time to roll a bathhouse moment.
                    bathhouse_tstamp = random() * 135
                status_dict[rnd].append(
                    NPCSicknessStatus(
                        npc_id,
                        rnd,
                        bathhouse_tstamp,
                        NPCSicknessStatusChange.GO_TO_BATHHOUSE,
                    )
                )

    def _compute_npc_status(self):
        """Calculate all sickness-related status change events
        for NPCs."""
        ingrp_adherence_pickable = list(self._ingrp_adhering_ids)
        outgrp_adherence_pickable = list(self._outgrp_adhering_ids)

        status_changes: dict[int, list[NPCSicknessStatus]] = {
            n: [] for n in range(7, 13)
        }

        deaths = {n: ([], []) for n in range(7, 13)}

        # For each group, select which NPCs are going to die first.
        ingrp_sick_death_eligible = list(
            _INGRP_ID_SAMPLING.difference(self._ingrp_adhering_ids)
        )
        outgrp_sick_death_eligible = list(
            _OUTGRP_ID_SAMPLING.difference(self._outgrp_adhering_ids)
        )

        # Note: using copies here as we're also going to pick through those same sets of IDs to decide when other NPCs get sick.
        self._generate_death_events(
            status_changes,
            ingrp_sick_death_eligible.copy(),
            outgrp_sick_death_eligible.copy(),
        )

        # Next, we generate sickness events for NPCs scheduled to die in their death round.
        # These will then be removed from sampling for the current round, and once the death round is reached
        # when selecting other NPCs to fall sick in said round, removed from the eligible pool entirely.
        for death_event in chain.from_iterable(status_changes.values()):
            if death_event.change_type != NPCSicknessStatusChange.DIE:
                continue
            status_changes[death_event.round_no].append(
                _get_sickness_from_death_evt(death_event)
            )

            current_npc = death_event.npc_id
            is_ingrp = current_npc < _ID_POOL_SIZE
            deaths[death_event.round_no][not is_ingrp].append(death_event.npc_id)

        # Pick which NPCs will suffer from nonlethal sickness in each round.
        self._compute_nonlethal_sickness(
            status_changes,
            deaths,
            ingrp_sick_death_eligible,
            outgrp_sick_death_eligible,
            ingrp_adherence_pickable,
            outgrp_adherence_pickable,
        )

        # Generate random timings for the NPCs to head to the bathhouse for each round.
        self._compute_bathhouse_timings(status_changes)

        # Sort all NPC sickness events by timestamp in each round's list and then put them in the queues in that order.
        for round_no, event_list in status_changes.items():
            event_list.sort(key=lambda evt: evt.timestamp)
            self.computed_status_changes[round_no].extend(event_list)

        # Send the status to the server.
        self.send_telemetry(
            "npc_status",
            {n: [evt.as_dict() for evt in val] for n, val in status_changes.items()},
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

    def compute_sickness_events(self):
        self.select_adhering_npcs()
        self._compute_npc_status()

    # endregion
