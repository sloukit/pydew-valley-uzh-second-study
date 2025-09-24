from urllib.error import HTTPError

import pygame

from src.exceptions import LoginError, TooEarlyLoginError
from src.fblitter import FBLITTER
from src.settings import OVERLAY_POSITIONS
from src.support import (
    get_translated_string,
    import_font,
)


class DisplayError:
    def __init__(self):
        # setup
        self.display_surface = pygame.display.get_surface()
        self.error_message: str | None = None

        # dimensions
        self.left = 20
        self.top = 20

        width, height = 1000, 500
        self.font = import_font(40, "font/LycheeSoda.ttf")

        self.rect = pygame.Rect(self.left, self.top, width, height)

        self.rect.center = OVERLAY_POSITIONS["display_error"]

    def display(self):
        if self.error_message is None:
            return

        foreground_color = "Black"

        # rects and surfs
        pad_y = 2

        message_surf = self.font.render(
            f"Fehler:\n \n{self.error_message}\n  \nDr\u00fccken Sie Enter oder Esc, um fortzufahren.",
            False,
            foreground_color,
        )
        message_rect = message_surf.get_frect(
            midright=(self.rect.left + 900, self.rect.centery + pad_y)
        )

        # display
        FBLITTER.draw_rect("white", self.rect, 0, 4)
        FBLITTER.draw_rect(foreground_color, self.rect, 4, 4)
        FBLITTER.schedule_blit(message_surf, message_rect)
        # pygame.draw.rect(self.display_surface, "White", self.rect, 0, 4)
        # pygame.draw.rect(self.display_surface, foreground_color, self.rect, 4, 4)
        # self.display_surface.blit(message_surf, message_rect)

    def set_error_message(self, error: Exception | None):
        if isinstance(error, TooEarlyLoginError):
            translation_key = "too_early_login"
        elif isinstance(error, (LoginError, ValueError, HTTPError)):
            translation_key = "login_failed"
        else:
            self.error_message = None
            return

        translation = get_translated_string(translation_key)
        self.error_message = translation.replace("|", "\n")

    def is_visible(self) -> bool:
        return self.error_message is not None
