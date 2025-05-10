from src.enums import StudyGroup
from src.npc.npc import NPC


class DeadNpcsRegistry:
    def __init__(self):
        self.dead_ingroup_npc: list[int] = []
        self.dead_outgroup_npc: list[int] = []

    def register_death(self, dying_npc: NPC):
        if dying_npc.study_group == StudyGroup.INGROUP:
            self.dead_ingroup_npc.append(dying_npc.npc_id)
        else:
            self.dead_outgroup_npc.append(dying_npc.npc_id)
        del dying_npc

    def get_ingroup_deaths_amount(self) -> int:
        return len(self.dead_ingroup_npc)

    def get_outgroup_deaths_amount(self) -> int:
        return len(self.dead_outgroup_npc)

    def get_total_deaths_amount(self) -> int:
        return self.get_outgroup_deaths_amount() + self.get_ingroup_deaths_amount()
