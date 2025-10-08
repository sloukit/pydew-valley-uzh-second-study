from collections.abc import Callable

import pygame

from src.enums import GameState
from src.gui.menu.general_menu import GeneralMenu
from src.settings import DEV_MODE, SCREEN_HEIGHT, SCREEN_WIDTH
from src.support import get_translated_string as get_translated_msg

_NOTIFICATION_TXT_TOP = SCREEN_HEIGHT / 20 + 75
_NOTIFICATION_TXT_CENTERX = SCREEN_WIDTH // 2


class NotificationMenu(GeneralMenu):
    def __init__(
        self,
        switch_screen: Callable[[GameState], None],
        message: str,
    ):
        options = [get_translated_msg("ok")]
        title = get_translated_msg("notification")
        size = (400, 400)
        self._message = message
        super().__init__(title, options, switch_screen, size)
        self._cached_msg: pygame.Surface = self.font.render(
            message, False, "black", wraplength=600
        )

    def set_message(self, msg: str):
        self._message = msg
        self._cached_msg = self.font.render(msg, False, "black", wraplength=600)
        self._change_ok_btn_placement()

    def _change_ok_btn_placement(self):
        # Shift around the OK button's position depending on how much space is needed to render the text.
        text_rect = self._cached_msg.get_frect(
            top=_NOTIFICATION_TXT_TOP, centerx=_NOTIFICATION_TXT_CENTERX
        )
        bg_rect = pygame.Rect(0, 0, text_rect.width + 40, text_rect.height + 20)
        bg_rect.center = text_rect.center
        btn = self.buttons[0]
        btn.rect.y = bg_rect.bottom + 20
        btn._content_rect.center = btn.rect.center
        btn.initial_rect.center = btn.rect.center

    def button_action(self, text: str):
        if DEV_MODE:  # Only print debug information if running in debug mode
            print(text)
        if text == get_translated_msg("ok"):
            self.switch_screen(GameState.PLAY)
        # if text == "Quit":
        #     self.quit_game()

    def handle_event(self, event: pygame.event.Event) -> bool:
        if super().handle_event(event):
            return True

        if event.type == pygame.KEYDOWN:
            if event.key in [
                pygame.K_ESCAPE,
                pygame.K_RETURN,
                pygame.K_SPACE,
                pygame.K_BACKSPACE,
            ]:
                self.switch_screen(GameState.PLAY)
                return True

        return False

    def draw_title(self):
        super().draw_title()

        text_rect = self._cached_msg.get_frect(
            top=_NOTIFICATION_TXT_TOP, centerx=_NOTIFICATION_TXT_CENTERX
        )

        bg_rect = pygame.Rect(0, 0, text_rect.width + 40, text_rect.height + 20)
        bg_rect.center = text_rect.center

        pygame.draw.rect(self.display_surface, "white", bg_rect, 0, 4)
        self.display_surface.blit(self._cached_msg, text_rect)
