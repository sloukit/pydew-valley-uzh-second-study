from collections.abc import Callable

from src.enums import StudyGroup
from src.npc.npc import NPC


class DeadNpcsRegistry:
    def __init__(
        self,
        current_map_name: str | None,
        telemetry_callback: Callable[[str, dict], None],
    ):
        self.data: dict[str : dict[str : list[int]]] = {}
        self.current_map_name: str = current_map_name
        self.telemetry_callback = telemetry_callback

    def register_death(self, dying_npc: NPC):
        self._get_dead_npcs_list(dying_npc.study_group).append(dying_npc.npc_id)
        print(f"{self.data=}")
        del dying_npc
        self.telemetry_callback("dead_npc_registry_update", self.data)

    def get_ingroup_deaths_amount(self) -> int:
        return self._count_dead_npcs_by_study_group(StudyGroup.INGROUP)

    def get_outgroup_deaths_amount(self) -> int:
        return self._count_dead_npcs_by_study_group(StudyGroup.OUTGROUP)

    def get_total_deaths_amount(self) -> int:
        return self.get_outgroup_deaths_amount() + self.get_ingroup_deaths_amount()

    def set_current_map_name(self, current_map_name: str):
        self.current_map_name = current_map_name

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
            if study_group.name not in current_map_data.keys():
                continue
            dead_npcs_list: list[int] = current_map_data[study_group.name]
            result += len(dead_npcs_list)
        return result

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
