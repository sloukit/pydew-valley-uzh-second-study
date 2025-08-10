from collections.abc import Callable

import pygame

from src.enums import GameState
from src.gui.menu.general_menu import GeneralMenu
from src.support import get_translated_string as get_translated_msg


class PauseMenu(GeneralMenu):
    def __init__(
        self,
        switch_screen: Callable[[GameState], None],
    ):
        options = [get_translated_msg("resume"), get_translated_msg("options")]
        title = get_translated_msg("pause_menu")
        size = (400, 400)
        super().__init__(title, options, switch_screen, size)

        self._music_paused = False

    def button_action(self, text: str):
        if text == get_translated_msg("resume"):
            # unpause from clicking resume
            self._music_paused = False
            pygame.mixer.unpause()
            self.switch_screen(GameState.PLAY)
        if text == get_translated_msg("options"):
            self.switch_screen(GameState.SETTINGS)

    def handle_event(self, event: pygame.event.Event) -> bool:
        # pause music
        if not self._music_paused and pygame.mixer.get_busy():
            self._music_paused = True
            pygame.mixer.pause()

        if super().handle_event(event):
            return True

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                # unpause from pressing esc
                self._music_paused = False
                pygame.mixer.unpause()
                self.switch_screen(GameState.PLAY)
                return True

        return False

    def setter(self, paused):
        # setter api is easier for someone in the future
        self._music_paused = paused
