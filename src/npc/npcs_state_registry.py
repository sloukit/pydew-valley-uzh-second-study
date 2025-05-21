from collections.abc import Callable
from datetime import datetime

from src.enums import Map, StudyGroup
from src.npc.npc import NPC

NPC_STATE_REGISTRY_UPDATE_EVENT = "npc_state_registry_update"
NPC_DEAD = "npc_dead"
NPC_SICKNESS = "npc_sickness"
NPC_HP = "npc_hp"
NPC_ID = "npc_id"
HEALTH_UPDATE_DELTA_SECONDS = 20


class NpcsStateRegistry:
    def __init__(
        self,
        current_map_name: str | None,
        telemetry_callback: Callable[[str, dict], None],
    ):
        self.last_health_update_timestamp = self.get_current_time()
        self.data: dict[str : dict[str : list[dict]]] = {}
        self.current_map_name: str = current_map_name
        self.telemetry_callback = telemetry_callback
        self.enabled: bool = False

    def restore_registry(self, restored_registry: dict):
        self.current_map_name = restored_registry["current_map_name"]
        self.data = restored_registry["data"]

    def register_health_update(self, npc: NPC):
        if not self.is_enabled():
            return

        npc_states: list[dict] = self._get_npcs_state_list(npc.study_group)
        current_npc_state = self._get_state(npc_states, npc.npc_id)
        current_npc_state[NPC_HP] = npc.hp
        current_npc_state[NPC_SICKNESS] = npc.is_sick

        if self._is_not_ready_to_update():
            return

        self.last_health_update_timestamp = self.get_current_time()
        self._store_registry()

    def get_current_time(self):
        return datetime.now()

    def register_death(self, dying_npc: NPC):
        if not self.is_enabled():
            return

        npc_states: list[dict] = self._get_npcs_state_list(dying_npc.study_group)
        dying_npc_state = self._get_state(npc_states, dying_npc.npc_id)
        dying_npc_state[NPC_DEAD] = True
        del dying_npc
        self._store_registry()

    def get_ingroup_deaths_amount(self) -> int:
        return self._count_dead_npcs_by_study_group(StudyGroup.INGROUP)

    def get_outgroup_deaths_amount(self) -> int:
        return self._count_dead_npcs_by_study_group(StudyGroup.OUTGROUP)

    def get_total_deaths_amount(self) -> int:
        return self.get_outgroup_deaths_amount() + self.get_ingroup_deaths_amount()

    def set_current_map_name(self, current_map: str | Map):
        self.current_map_name = (
            current_map.value if isinstance(current_map, Map) else current_map
        )

    def is_npc_dead(self, npc_id: int, study_group: StudyGroup) -> bool:
        result: bool = False
        for map_name in self.data.keys():
            current_map_data: dict[str : list[[int]]] = self.data[map_name]
            if study_group.name not in current_map_data.keys():
                continue
            dead_npcs_list: list[dict] = current_map_data[study_group.name]
            dying_npc_state = self._get_state(dead_npcs_list, npc_id)
            if dying_npc_state is not None:
                result = (
                    dying_npc_state[NPC_DEAD] if NPC_DEAD in dying_npc_state else False
                )
                break
        return result

    def enable(self) -> None:
        self.enabled = True

    def disable(self) -> None:
        self.enabled = False

    def is_enabled(self) -> bool:
        return self.enabled

    def _is_not_ready_to_update(self):
        return (
            self.get_current_time() - self.last_health_update_timestamp
        ).total_seconds() < HEALTH_UPDATE_DELTA_SECONDS

    def _get_npcs_state_list(self, study_group: StudyGroup) -> list[dict]:
        map_data: dict[str : list[[dict]]] = (
            self.data[self.current_map_name]
            if self.current_map_name in self.data.keys()
            else None
        )
        if map_data is None:
            map_data = {}
            self.data[self.current_map_name] = map_data
        return self._get_npc_states(map_data, study_group)

    def _get_npc_states(
        self, map_data: dict[str, list[dict]], study_group: StudyGroup
    ) -> list[dict]:
        study_group_data: list[dict] = (
            map_data[study_group.name] if study_group.name in map_data.keys() else None
        )
        if study_group_data is None:
            study_group_data = []
            map_data[study_group.name] = study_group_data

        return study_group_data

    def _get_state(self, npc_states: list[dict], npc_id: int) -> dict:
        current_state: dict = self._get_npc_state_data(npc_states, npc_id)
        if current_state is None:
            current_state = {NPC_ID: npc_id}
            npc_states.append(current_state)
        return current_state

    def _get_npc_state_data(self, npc_states, npc_id: int) -> dict | None:
        if npc_states is None or len(npc_states) == 0:
            return None

        for current_state in npc_states:
            if NPC_ID in current_state and current_state[NPC_ID] == npc_id:
                return current_state
        return None

    def _count_dead_npcs_by_study_group(self, study_group: StudyGroup) -> int:
        if not self.is_enabled():
            return 0

        result: int = 0
        for map_name in self.data:
            current_map_data: dict[str : list[dict]] = self.data[map_name]
            if study_group.name not in current_map_data:
                continue
            npc_states_list: list[dict] = current_map_data[study_group.name]
            dead_npc: list[dict] = self._get_dead_npc(npc_states_list)
            result += len(dead_npc)
        return result

    def _get_dead_npc(self, npc_states_list) -> list[dict]:
        if npc_states_list is None or len(npc_states_list) == 0:
            return []
        result: list[dict] = []
        for current_state in npc_states_list:
            if NPC_DEAD in current_state and current_state[NPC_DEAD]:
                result.append(current_state)

        return result

    def _store_registry(self):
        if self.telemetry_callback is None:
            return
        telemetry_payload = {
            "data": self.data,
            "current_map_name": self.current_map_name,
        }
        self.telemetry_callback(NPC_STATE_REGISTRY_UPDATE_EVENT, telemetry_payload)
