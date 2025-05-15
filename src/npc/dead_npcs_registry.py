from collections.abc import Callable

from src.enums import Map, StudyGroup
from src.npc.npc import NPC

DEAD_NPC_REGISTRY_UPDATE_EVENT = "dead_npc_registry_update"


class DeadNpcsRegistry:
    def __init__(
        self,
        current_map_name: str | None,
        telemetry_callback: Callable[[str, dict], None],
    ):
        self.data: dict[str : dict[str : list[int]]] = {}
        self.current_map_name: str = current_map_name
        self.telemetry_callback = telemetry_callback

    def restore_registry(self, restored_registry: dict):
        self.current_map_name = restored_registry["current_map_name"]
        self.data = restored_registry["data"]

    def register_death(self, dying_npc: NPC):
        self._get_dead_npcs_list(dying_npc.study_group).append(dying_npc.npc_id)
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
            dead_npcs_list: list[int] = current_map_data[study_group.name]
            if npc_id in dead_npcs_list:
                result = True
                break
        return result

    def _get_dead_npcs_list(self, study_group: StudyGroup) -> list[int]:
        map_data: dict[str : list[[int]]] = (
            self.data[self.current_map_name]
            if self.current_map_name in self.data.keys()
            else None
        )
        if map_data is None:
            map_data = {}
            self.data[self.current_map_name] = map_data
        return self._get_npc_ids(map_data, study_group)

    def _get_npc_ids(
        self, map_data: dict[str, list[int]], study_group: StudyGroup
    ) -> list[int]:
        study_group_data: list[int] = (
            map_data[study_group.name] if study_group.name in map_data.keys() else None
        )
        if study_group_data is None:
            study_group_data = []
            map_data[study_group.name] = study_group_data

        return study_group_data

    def _count_dead_npcs_by_study_group(self, study_group: StudyGroup) -> int:
        result: int = 0
        for map_name in self.data.keys():
            current_map_data: dict[str : list[[int]]] = self.data[map_name]
            if study_group.name not in current_map_data:
                continue
            dead_npcs_list: list[int] = current_map_data[study_group.name]
            result += len(dead_npcs_list)
        return result

    def _store_registry(self):
        if self.telemetry_callback is None:
            return
        telemetry_payload = {
            "data": self.data,
            "current_map_name": self.current_map_name,
        }
        self.telemetry_callback(DEAD_NPC_REGISTRY_UPDATE_EVENT, telemetry_payload)
