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

from src.client import get_npc_events  # noqa: F401
from src.enums import NPCSicknessStatusChange
from src.npc.npc import NPC

# Number of NPCs per group.
NPC_POOL_SIZE = 12

# Used to sample NPC IDs when selecting which NPCs adhere or not.
INGRP_IDS = set(range(NPC_POOL_SIZE))
OUTGRP_IDS = set(range(NPC_POOL_SIZE, NPC_POOL_SIZE*2))

# adherent / non-adherent setting: how many adherent ingroup npc
ADH_NPC_INGRP = [int(0.2*NPC_POOL_SIZE), int(0.8*NPC_POOL_SIZE)] # share of adhering npc if ingroup is adherent

# Halve the NPC count for NPC adherence in the outgroup.
_MAXIMUM_DEATH_COUNT = NPC_POOL_SIZE // 2

_DEATH_LIKELIHOOD = 0.5 # per round, non-adhering have two dice rolls


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

    def __str__(self):
        return f"Rnd {self.round_no:2} TS: {round(self.timestamp, 1):6.1f}: NPC {self.npc_id:2} will {self.change_type.name}"


def get_sickness_evt(npc_id: int, current_round: int):
    return NPCSicknessStatus(
        npc_id, current_round, randint(1, 2) * SICK_INTERVAL, NPCSicknessStatusChange.SICKNESS
    )

def get_death_and_sickness_evt_w_rand_ts(npc_id: int, death_round: int) -> tuple[NPCSicknessStatus, NPCSicknessStatus]:
    """Define a death timestamp for an NPC id: Sick after 5 or 10mins and dead some time after"""
    sick_evt = get_sickness_evt(npc_id, death_round)
    die_tstamp = sick_evt.timestamp + 60 + 120 * random() # die some time after

    return (sick_evt, NPCSicknessStatus(
        npc_id, death_round, die_tstamp, NPCSicknessStatusChange.DIE
    ))


def roll_death():
    return random() < _DEATH_LIKELIHOOD


def roll_death_count_for_ingrp(
    current_round: int, adherence: bool
):
    """Roll how many NPCs will die in the ingroup for the current round. may need capping at max death afterwards"""
    if adherence and current_round > 9: # no deaths in this scenario
        return 0
    n_dead = roll_death()
    if not adherence and current_round < 10:
        n_dead += roll_death() # second roll for non-adherence
    return n_dead




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
        self.ingrp_adhering_ids = set()
        self.outgrp_adhering_ids = set()
        # Using deques so we can pull the events out as time passes in the game.
        self.evt_list = []

    def add_npc(self, npc_id: int, obj: NPC):
        self._npcs[npc_id] = obj
        if npc_id in self.ingrp_adhering_ids or npc_id in self.outgrp_adhering_ids:
            # If the NPC is supposed to adhere to the conditions, it will wear the goggles.
            # This also allows it to go to the bathhouse.
            obj.behaviour_tree_context.adhering_to_measures = True

    @property
    def next_event_this_round(self):
        if len(self.evt_list)>0 and self.evt_list[-1].round_no<=self.get_round():
            return self.evt_list[-1]
        return None

    @property
    def ingrp_non_adh_ids(self):
        return INGRP_IDS.difference(self.ingrp_adhering_ids)

    @property
    def outgrp_non_adh_ids(self):
        return OUTGRP_IDS.difference(self.outgrp_adhering_ids)

    def get_death_evt(self, npc_id, round=None):
        for evt in self.evt_list[::-1]: # the list is reversed to allow popping
            if round is not None and evt.round_no>round:
                return None
            if evt.change_type == NPCSicknessStatusChange.DIE and evt.npc_id==npc_id and (round is None or evt.round_no==round):
                return evt
        return None

    def get_evtdicts_per_round(self, round):
        ret_evts = []
        for evt in self.evt_list[::-1]: # the list is reversed to allow popping
            if evt.round_no==round:
                ret_evts.append(dict(evt))
        return ret_evts

    def get_death_ids(self, round=None):
        ids = []
        for evt in self.evt_list[::-1]: # the list is reversed to allow popping
            if evt.change_type == NPCSicknessStatusChange.DIE and (round is None or evt.round_no==round):
                ids.append(evt.npc_id)
        return ids



    def update_npc_status(self):
        current_round = self.get_round()
        if current_round < 7 or self.next_event_this_round is None: # earlier rounds: do nothing, or no events left
            return
        timestamp = self.next_event_this_round.timestamp
        if timestamp > self.get_rnd_timer():
            return # Too early.

        evt = self.evt_list.pop()
        target_npc: int = evt.npc_id

        match evt.change_type:
            case NPCSicknessStatusChange.SICKNESS:
                # Check if the NPC is scheduled to die
                death_evt = self.get_death_evt(target_npc, current_round)
                if (
                    death_evt is None
                    or timestamp + 300 < death_evt.timestamp
                ): # regular sickness
                    self._npcs[target_npc].get_sick(timestamp)
                else: # sickness leading to death
                    self._npcs[target_npc].get_sick(timestamp, death_evt.timestamp)
            case NPCSicknessStatusChange.DIE:
                self._npcs[target_npc].die()
            case NPCSicknessStatusChange.GO_TO_BATHHOUSE:
                return # debug: how does it work?

    def setup_from_db_data(self, received: dict | None):
        print(received)

        if received is None:
            return

        if received["data"] is None:
            self.compute_event_list()
            return

        print("=================NPC SICKNESS EVENTS FROM DB=====================")
        for i, db_evt_list in received["data"].items():
            for db_evt in db_evt_list:
                evt = NPCSicknessStatus(
                    db_evt["npc_id"], int(i), db_evt["timestamp"], NPCSicknessStatusChange(db_evt["change_type"])
                )
                self.evt_list.append(evt)
                print(str(evt))  # this print the event to the terminal
                if evt.change_type == NPCSicknessStatusChange.GO_TO_BATHHOUSE:
                    if evt.npc_id < NPC_POOL_SIZE:
                        self.ingrp_adhering_ids.add(evt.npc_id)
                    else:
                        self.outgrp_adhering_ids.add(evt.npc_id)
        self.update_adhering_npcs_context_tree()
        # sorting should be ok already but just to be sure...
        self.evt_list.sort(key=lambda s: (s.round_no, s.timestamp), reverse=True)

    def compute_event_list(self):
        """Calculate all sickness-related status change events
        for NPCs."""
        self.select_adhering_npcs()

        # Note: using copies here as we're also going to pick through those same sets of IDs to decide when other NPCs get sick.
        self.generate_death_events()

        # Pick which NPCs will suffer from nonlethal sickness in each round.
        # All while making sure they are not already dead or sick
        self.compute_nonlethal_sickness()

        # Generate random timings for the NPCs to head to the bathhouse for each round.
        self.compute_bathhouse_timings()

        print("=================NPC SICKNESS EVENTS GENERATED=====================")
        # Sort events in reverse, so that we can pop them from the back of the list
        self.evt_list.sort(key=lambda s: (s.round_no, s.timestamp), reverse=True)
        for evt in self.evt_list:
            print(str(evt))

        #Send the status to the server.
        self.send_telemetry(
            "npc_status",
            {n: self.get_evtdicts_per_round(n) for n in range(7, 13)},
        )


    def get_status_from_server(self, jwt: str):
        get_npc_events(jwt, self.setup_from_db_data)

    # region Sickness event generation (first login)
    def generate_death_events(self):
        """Generate death events for the last 6 rounds."""
        ingrp_death_count = 0
        outgrp_death_count = 0
        ingrp_eligible = list(self.ingrp_non_adh_ids)
        outgrp_eligible = list(self.outgrp_non_adh_ids)
        for rnd in range(7, 13):
            if ingrp_death_count < _MAXIMUM_DEATH_COUNT:
                new_deaths = roll_death_count_for_ingrp(rnd, self.adherence)
                if new_deaths>0:
                    new_deaths = min(new_deaths, _MAXIMUM_DEATH_COUNT-ingrp_death_count)
                    selected_ids = sample(ingrp_eligible, new_deaths)
                    for npc_id in selected_ids:
                        sickness, death = get_death_and_sickness_evt_w_rand_ts(npc_id, rnd)
                        self.evt_list += [sickness, death]
                        ingrp_eligible.remove(npc_id)
                    ingrp_death_count += new_deaths
            if outgrp_death_count < _MAXIMUM_DEATH_COUNT:
                if roll_death():
                    selected_npc_id = choice(outgrp_eligible)
                    sickness, death = get_death_and_sickness_evt_w_rand_ts(selected_npc_id, rnd)
                    self.evt_list += [sickness, death]
                    outgrp_eligible.remove(selected_npc_id)
                    outgrp_death_count += 1

    def compute_nonlethal_sickness(self):
        # make copies as we will edit this
        available_ingr_adh = set(self.ingrp_adhering_ids)
        available_outgrp_adh = set(self.outgrp_adhering_ids)
        available_ingr_nonadh = set(self.ingrp_non_adh_ids)
        available_outgrp_nonadh = set(self.outgrp_non_adh_ids)

        for rnd in range(7, 13):
            # dying npcs for this round (remove from sickness possibility)
            die_ids = self.get_death_ids(round=rnd)
            print("die ids round {} {}".format(rnd, die_ids))
            # ingroup non-adhering
            available_ingr_nonadh = available_ingr_nonadh.difference(die_ids)
            sick_count = len(available_ingr_nonadh)-1 # all but one get sick
            if not self.adherence and rnd >=10:
                sick_count -= 2
            if sick_count > 0:
                sick_ids = sample(list(available_ingr_nonadh), sick_count)
                for sick_id in sick_ids:
                    self.evt_list.append(get_sickness_evt(sick_id, rnd))

            # ingroup adhering: one per round and at
            if len(available_ingr_adh) > 0:
                sick_id = choice(list(available_ingr_adh))
                available_ingr_adh.remove(sick_id)
                self.evt_list.append(get_sickness_evt(sick_id, rnd))


            # outgroup non-adhering
            available_outgrp_nonadh = available_outgrp_nonadh.difference(die_ids)
            sick_count = len(available_outgrp_nonadh)-1 # all but one get sick
            if rnd >=10:
                sick_count -= 1
            if sick_count > 0:
                sick_ids = sample(list(available_outgrp_nonadh), sick_count)
                for sick_id in sick_ids:
                    self.evt_list.append(get_sickness_evt(sick_id, rnd))

            # outgroup adhering: one per round and at
            if len(available_outgrp_adh) > 0:
                sick_id = choice(list(available_outgrp_adh))
                available_outgrp_adh.remove(sick_id)
                self.evt_list.append(get_sickness_evt(sick_id, rnd))

    def get_bath_evt(self, npc_id, rnd, s, e):
        t = s+random()*(e-s)
        return  NPCSicknessStatus(
                        npc_id,
                        rnd,
                        t,
                        NPCSicknessStatusChange.GO_TO_BATHHOUSE,
                    )
    def compute_bathhouse_timings(self):
        """Generate bathhouse timings for each adhering NPC in both groups."""
        adhering_ids = self.ingrp_adhering_ids.union(self.outgrp_adhering_ids)
        for rnd in range(7, 13):
            for npc_id in adhering_ids:
                # It is assumed an NPC takes 45 seconds to leave the map and come back in all instances.
                if rnd == 7:
                    # earliest leaving after 60s, latest return after 300s, start between 60 and 255s
                    self.evt_list.append(self.get_bath_evt(npc_id, rnd, 60, 255))
                else:
                    # be back after 180s, leave before 135s
                    self.evt_list.append(self.get_bath_evt(npc_id, rnd, 0, 135))

    def update_adhering_npcs_context_tree(self):
        for id in self.ingrp_adhering_ids | self.outgrp_adhering_ids:
            if id in self._npcs:
                self._npcs[id].behaviour_tree_context.adhering_to_measures = True

    def select_adhering_npcs(self):
        """Determine which NPCs adhere to the health measures.

        The adherence parameter only affects the ingroup.
        The outgroup always has a 50/50 proportion of adherence."""
        self.ingrp_adhering_ids = set(
            sample(list(INGRP_IDS), ADH_NPC_INGRP[self.adherence])
        )
        self.outgrp_adhering_ids = set(
            sample(list(OUTGRP_IDS), NPC_POOL_SIZE // 2)
        )
        self.update_adhering_npcs_context_tree()

    # endregion
