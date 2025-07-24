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

from src.settings import (
    SICK_INTERVAL,
)

from src.client import get_npc_status  # noqa: F401
from src.enums import NPCSicknessStatusChange
from src.npc.npc import NPC

# Used to sample NPC IDs when selecting which NPCs adhere or not.
_INGRP_ID_SAMPLING_LST = list(range(12))
_INGRP_ID_SAMPLING = set(_INGRP_ID_SAMPLING_LST)
_OUTGRP_ID_SAMPLING_LST = list(range(12, 24))
_OUTGRP_ID_SAMPLING = set(_OUTGRP_ID_SAMPLING_LST)

# Number of NPCs per group.
NPC_POOL_SIZE = 12

# adherent / non-adherent setting: how many adherent ingroup npc
ADH_NPC_INGRP = [int(0.2*NPC_POOL_SIZE), int(0.8*NPC_POOL_SIZE)] # share of adhering npc if ingroup is adherent


# Halve the NPC count for NPC adherence in the outgroup.
_MAXIMUM_DEATH_COUNT = NPC_POOL_SIZE // 2

_DEATH_LIKELIHOOD = 0.5


@dataclass
class NPCSicknessStatus:
    """Represents any status change in an NPC's sickness in any given round."""

    npc_id: int
    round_no: int
    timestamp: float
    change_type: NPCSicknessStatusChange


    def __iter__(self):
        # Yield key-value pairs to allow dict(NPCSicknessStatus_object)
        yield 'npc_id', self.npc_id
        yield 'timestamp', self.timestamp
        yield 'change_type', self.change_type.value


def _summarise_event(evt: NPCSicknessStatus):
    match evt.change_type:
        case NPCSicknessStatusChange.DIE:
            action = "die"
        case NPCSicknessStatusChange.SICKNESS:
            action = "get sick"
        case NPCSicknessStatusChange.GO_TO_BATHHOUSE:
            return
        case NPCSicknessStatusChange.SWITCH_TO_RECOVERY:
            action = "recover"
    print(
        f"On round {evt.round_no}, after {round(evt.timestamp, 2)} seconds pass, NPC {evt.npc_id} will {action}"
    )


def _get_death(npc_id: int, death_round: int) -> NPCSicknessStatus:
    """Define a death timestamp for a certain NPC id."""
    # Get sick at 5 or 10 mins (discrete possible times)
    base_tstamp = SICK_INTERVAL * randint(1, 2)
    final_tstamp = base_tstamp + 60 + 120 * random() # die some time after

    return NPCSicknessStatus(
        npc_id, death_round, final_tstamp, NPCSicknessStatusChange.DIE
    )


def _roll_death():
    return random() < _DEATH_LIKELIHOOD


def _roll_death_count_for_ingrp(
    current_count: int, current_round: int, adherence: bool
):
    """Roll how many NPCs will die in the ingroup for the current round."""
    if adherence and current_round > 9: # no deaths in this scenario
        return 0
    computed = _roll_death()
    if (
        current_count + computed < _MAXIMUM_DEATH_COUNT
        and not adherence
        and current_round < 10
    ):
        computed += _roll_death() # second roll for non-adherence
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
        get_rnd_timer: Callable[[], float],
        send_telemetry: Callable[[str, dict], None],
        adherence: bool = False,
    ):
        self.get_round = get_round
        self.get_rnd_timer = get_rnd_timer
        self.send_telemetry = send_telemetry
        self._npcs: dict[int, NPC] = {}
        self.adherence = adherence
        self._ingrp_adhering_ids = set()
        self._outgrp_adhering_ids = set()
        # Using deques so we can pull the events out as time passes in the game.
        self.computed_status_changes: dict[int, deque[NPCSicknessStatus]] = {
            n: deque() for n in range(7, 13)
        }
        self.death_tstamps: dict[int, tuple[int, float]] = {}

    def add_npc(self, npc_id: int, obj: NPC):
        self._npcs[npc_id] = obj
        if npc_id in self._ingrp_adhering_ids or npc_id in self._outgrp_adhering_ids:
            # If the NPC is supposed to adhere to the conditions, it will wear the goggles.
            # This also allows it to go to the bathhouse.
            obj.behaviour_tree_context.adhering_to_measures = True

    @property
    def _next_event(self):
        if len(self.computed_status_changes[self.get_round()])>0:
            return self.computed_status_changes[self.get_round()][0]
        return None

    def update_npc_status(self):
        current_round = self.get_round()
        if current_round < 7 or self._next_event is None: # earlier rounds: do nothing, or no events left
            return
        timestamp = self._next_event.timestamp
        if timestamp > self.get_rnd_timer():
            return # Too early.

        target_npc: int = self._next_event.npc_id

        match self._next_event.change_type:
            case NPCSicknessStatusChange.SICKNESS:
                # Check if the NPC is scheduled to die
                death_tstamp = self.death_tstamps.get(target_npc)
                if (
                    death_tstamp is None
                    or death_tstamp[0] < current_round
                    or timestamp + 300 < death_tstamp[1]
                ): # regular sickness
                    self._npcs[target_npc].get_sick(timestamp)
                    self.computed_status_changes[current_round].popleft()
                    return
                self._npcs[target_npc].get_sick(timestamp, death_tstamp[1])
                self.computed_status_changes[current_round].popleft()
            case NPCSicknessStatusChange.DIE:
                self._npcs[target_npc].die()
                self.computed_status_changes[current_round].popleft()
            case NPCSicknessStatusChange.GO_TO_BATHHOUSE:
                self.computed_status_changes[current_round].popleft()

    def _setup_from_returned_data(self, received: dict | None):
        print(received)

        if received is None:
            return

        received_data = received["data"]

        if received_data is None:
            self.compute_sickness_events()
            return

        print("=================NPC SICKNESS EVENT ORDER=====================")
        for i, evt_list in received_data.items():
            for evt in evt_list:
                computed = NPCSicknessStatus(
                    evt["npc_id"], i, evt["timestamp"], evt["change_type"]
                )
                self.computed_status_changes[int(i)].append(computed)
                _summarise_event(computed)  # this print the event to the terminal
                if computed.change_type == NPCSicknessStatusChange.DIE:
                    self.death_tstamps[computed.npc_id] = (int(i), computed.timestamp)
                if computed.change_type == NPCSicknessStatusChange.GO_TO_BATHHOUSE:
                    if computed.npc_id < NPC_POOL_SIZE:
                        self._ingrp_adhering_ids.add(computed.npc_id)
                    else:
                        self._outgrp_adhering_ids.add(computed.npc_id)

    def get_status_from_server(self, jwt: str):
        get_npc_status(jwt, self._setup_from_returned_data)

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
                if curr_ingrp_rnd_deaths>0:
                    selected_ids = sample(ingrp_eligible, curr_ingrp_rnd_deaths)
                    for npc_id in selected_ids:
                        computed = _get_death(npc_id, rnd)
                        status_dict[rnd].append(computed)
                        self.death_tstamps[npc_id] = (rnd, computed.timestamp)
                        ingrp_eligible.remove(npc_id)
                    ingrp_death_count += curr_ingrp_rnd_deaths

            if outgrp_death_count < _MAXIMUM_DEATH_COUNT:
                kill_another_outgrp_npc = _roll_death()
                if not kill_another_outgrp_npc:
                    # Checks were already performed for the ingroup, so we can safely
                    # jump to the next loop.
                    continue
                selected_npc_id = choice(outgrp_eligible)
                computed = _get_death(selected_npc_id, rnd)
                status_dict[rnd].append(computed)
                self.death_tstamps[selected_npc_id] = (rnd, computed.timestamp)
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
            if len(ingrp_adherence_pickable) > 0:
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

        status_changes: dict[int, list[NPCSicknessStatus]] = { #split into rounds
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
            is_ingrp = current_npc < NPC_POOL_SIZE
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
            {n: [dict(evt) for evt in val] for n, val in status_changes.items()},
        )

    def select_adhering_npcs(self):
        """Determine which NPCs adhere to the health measures.

        The adherence parameter only affects the ingroup.
        The outgroup always has a 50/50 proportion of adherence."""
        self._ingrp_adhering_ids = set(
            sample(_INGRP_ID_SAMPLING_LST, ADH_NPC_INGRP[self.adherence])
        )
        self._outgrp_adhering_ids = set(
            sample(_OUTGRP_ID_SAMPLING_LST, NPC_POOL_SIZE // 2)
        )

    def compute_sickness_events(self):
        self.select_adhering_npcs()
        self._compute_npc_status()

    # endregion
