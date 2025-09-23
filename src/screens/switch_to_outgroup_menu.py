from collections.abc import Callable

import pygame

from src.enums import GameState, StudyGroup
from src.gui.menu.general_menu import GeneralMenu
from src.settings import SCREEN_HEIGHT, SCREEN_WIDTH

# This menu is for when the player decides whether they will join the outgroup.


class OutgroupMenu(GeneralMenu):
    def __init__(
        self,
        player,
        switch_screen: Callable[[GameState], None],
        send_switch_telemetry: Callable[[], None],
    ):
        options = ["Ja", "Nein"]
        title = "Möchtest zu den Hornlingen wechseln?\nAchtung: Diese Entscheidung ist endgültig!"
        size = (400, 400)

        self.player = player
        self.send_switch_telemetry = send_switch_telemetry
        super().__init__(title, options, switch_screen, size)

    def button_action(self, text):
        if "Ja" in text:
            self.player.study_group = StudyGroup.OUTGROUP
            self.send_switch_telemetry()
        elif "Nein" in text:
            self.switch_screen(GameState.PLAY)

    def outgroup_handle_event(self, event: pygame.event.Event) -> bool:
        if super().handle_event(event):
            return True
        return False

    def draw_title(self):
        text_surf = self.font.render(self.title, False, "Black")
        midtop = (SCREEN_WIDTH / 2, SCREEN_HEIGHT / 20)
        text_rect = text_surf.get_frect(midtop=midtop)

        bg_rect = pygame.Rect((0, 0), (600, 100))
        bg_rect.center = text_rect.center

        pygame.draw.rect(self.display_surface, "White", bg_rect, 0, 4)
        self.display_surface.blit(text_surf, text_rect)
