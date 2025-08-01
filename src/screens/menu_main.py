# import traceback
import traceback
from collections.abc import Callable
from typing import Any

import pygame
from pygame.mouse import get_pressed as mouse_buttons

from src import client, xplat
from src.enums import CustomCursor, GameState
from src.events import SET_CURSOR, post_event
from src.fblitter import FBLITTER
from src.gui.display_error import DisplayError
from src.gui.menu.general_menu import GeneralMenu
from src.settings import (
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
    # USE_SERVER,
)
from src.support import get_translated_string as get_translated_msg

_SCREEN_CENTER = (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
# MAX_TOKEN_LEN = 3
MAX_TOKEN_LEN = 10
MAX_PLAYERS_NAME_LEN = 16


class MainMenu(GeneralMenu):
    def __init__(
        self,
        switch_screen: Callable[[GameState], None],
        set_token: Callable[[dict[str, Any]], None],
        set_players_name: Callable[[dict[str, Any]], None],
    ) -> None:
        options = [
            get_translated_msg("play"),
            get_translated_msg("quit"),
            get_translated_msg("prompt_auth_data"),
        ]
        title = get_translated_msg("title_screen")
        size = (400, 400)
        super().__init__(title, options, switch_screen, size)
        # This function references a method of the main `Game` object.
        self.set_token = set_token
        self.set_players_name = set_players_name
        self.token = ""  # Variable to store token
        self.players_name = ""  # Variable to store players_name
        self.round_config = {}
        self.play_button_enabled = False  # Initialize as False

        # Input fields
        self.input_active = False
        self.players_name_active = False
        self.input_box = pygame.Rect(100, 390, 200, 50)
        self.players_name_box = pygame.Rect(100, 390, 200, 50)
        self.input_text = ""
        self.players_name_text = ""

        # Error
        self.display_error = DisplayError()

        # Cursor blinking
        self.cursor_visible = True
        self.cursor_timer = pygame.time.get_ticks()
        self.cursor_interval = 500

    def reset_fields(self) -> None:
        """Reset all input fields and hide them."""
        self.input_active = False
        self.players_name_active = False
        self.input_text = ""
        self.players_name_text = ""
        self.play_button_enabled = False

    def validate_players_name(self, players_name: str) -> bool:
        """Validate if `players_name` is shorter or equal to MAX_PLAYERS_NAME_LEN and alphanumeric."""
        return len(players_name) <= MAX_PLAYERS_NAME_LEN and players_name.isalnum()

    def draw_input_box(self, box, input_text, label_text, input_active) -> None:
        button_width = 400
        button_height = 50
        box_color = (255, 255, 255)
        border_color = (141, 133, 201)
        text_color = (0, 0, 0)
        background_color = (210, 204, 255)

        box.width = button_width
        box.height = button_height
        box.centerx = _SCREEN_CENTER[0]

        background_rect = box.copy()
        background_rect.inflate_ip(0, 50)
        background_rect.move_ip(0, -8)
        FBLITTER.draw_rect(background_color, background_rect, border_radius=10)
        # pygame.draw.rect(
        #     self.display_surface, background_color, background_rect, border_radius=10
        # )

        if input_active:
            label_font = self.font
            label_surface = label_font.render(label_text, True, text_color)
            label_rect = label_surface.get_rect(midbottom=(box.centerx, box.top + 5))
            FBLITTER.schedule_blit(label_surface, label_rect)
            # self.display_surface.blit(label_surface, label_rect)

        FBLITTER.draw_rect(box_color, box, border_radius=10)
        FBLITTER.draw_rect(border_color, box, 3, border_radius=10)
        # pygame.draw.rect(self.display_surface, box_color, box, border_radius=10)
        # pygame.draw.rect(self.display_surface, border_color, box, 3, border_radius=10)

        font = self.font
        text_surface = font.render(input_text, True, text_color)
        text_rect = text_surface.get_rect(midleft=(box.x + 10, box.centery))
        FBLITTER.schedule_blit(text_surface, text_rect)
        # self.display_surface.blit(text_surface, text_rect)

        if input_active:
            current_time = pygame.time.get_ticks()
            if current_time - self.cursor_timer >= self.cursor_interval:
                self.cursor_visible = not self.cursor_visible
                self.cursor_timer = current_time
            if self.cursor_visible:
                cursor_rect = pygame.Rect(text_rect.topright, (2, text_rect.height))
                FBLITTER.draw_rect(text_color, cursor_rect)
                # pygame.draw.rect(self.display_surface, text_color, cursor_rect)

    def draw(self) -> None:
        super().draw()
        if self.input_active:
            self.draw_input_box(
                self.input_box,
                self.input_text,
                get_translated_msg("prompt_token"),
                self.input_active,
            )
        if self.players_name_active:
            self.draw_input_box(
                self.players_name_box,
                self.players_name_text,
                get_translated_msg("prompt_plyname"),
                self.players_name_active,
            )
        self.display_error.display()

    def post_login_callback(self, login_response: dict) -> None:
        """Meant to be used as a callback function post-login."""
        # jwt = login_response["jwt"]
        # Pass the JWT back to the main Game object:
        # self.set_token(jwt)
        self.round_config = self.set_token(login_response)
        self.token = self.input_text
        self.players_name_active = True
        self.input_active = False
        self.input_text = ""
        # get players_name only if used in introduction
        if self.round_config.get("character_introduction_text", ""):
            self.players_name_active = True
        else:
            self.players_name_active = True
            self.set_players_name("")
            self.play_button_enabled = True
            self.remove_button(get_translated_msg("prompt_auth_data"))
            self.draw()
        self.input_text = ""

    def error_login_callback(self, login_error: Exception) -> None:
        """Meant to be used as an error callback function post-login."""
        self.display_error.set_error_message(login_error)

    def do_login(self, token: str) -> None:
        """Log in with a play token."""
        client.authn(token, self.post_login_callback, self.error_login_callback)

    def button_action(self, text) -> None:
        if text == get_translated_msg("play") and self.play_button_enabled:
            post_event(SET_CURSOR, cursor=CustomCursor.ARROW)
            self.switch_screen(GameState.PLAY)
        elif text == get_translated_msg("prompt_auth_data"):
            self.input_active = True
            self.token = ""  # Reset token each time we re-enter
        elif text == get_translated_msg("quit"):
            self.quit_game()

    def handle_event(self, event: pygame.event.Event) -> bool:
        if super().handle_event(event):
            return True

        if self.display_error.is_visible():
            if event.type == pygame.KEYDOWN and event.key in [
                pygame.K_RETURN,
                pygame.K_KP_ENTER,
                pygame.K_ESCAPE,
            ]:
                self.display_error.set_error_message(None)
                self.reset_fields()
                return True

        if event.type == pygame.MOUSEBUTTONDOWN and mouse_buttons()[0]:
            self.pressed_button = self.get_hovered_button()
            if self.input_box.collidepoint(event.pos) and not self.players_name_active:
                self.input_active = True
                self.players_name_active = False
                return True
            elif self.players_name_box.collidepoint(event.pos):
                self.input_active = False
                self.players_name_active = True
                return True
            else:
                self.input_active = False
                self.players_name_active = False

        if event.type == pygame.KEYDOWN:
            # Ignore the Tab key
            if event.key == pygame.K_TAB:
                return True

            if self.input_active:
                if event.key in [pygame.K_RETURN, pygame.K_KP_ENTER]:
                    if self.input_text:
                        try:
                            self.do_login(self.input_text)
                        except Exception as error:
                            self.display_error.set_error_message(error)
                        finally:
                            self.input_active = False

                        return True
                elif event.key == pygame.K_ESCAPE:
                    self.reset_fields()
                    return True
                elif event.key == pygame.K_BACKSPACE:
                    self.input_text = self.input_text[:-1]
                    return True
                elif len(self.input_text) < MAX_TOKEN_LEN:
                    self.input_text += event.unicode
                    return True

            if self.players_name_active:
                if event.key in [pygame.K_RETURN, pygame.K_KP_ENTER]:
                    if self.validate_players_name(self.players_name_text):
                        self.players_name = self.players_name_text
                        self.set_players_name(self.players_name)
                        self.play_button_enabled = True
                        self.players_name_active = False
                        self.remove_button(get_translated_msg("prompt_auth_data"))
                        self.draw()
                    return True
                elif event.key == pygame.K_ESCAPE:
                    self.reset_fields()
                    return True
                elif event.key == pygame.K_BACKSPACE:
                    self.players_name_text = self.players_name_text[:-1]
                    return True
                elif self.validate_players_name(self.players_name_text + event.unicode):
                    self.players_name_text += event.unicode
                    return True

            if not self.input_active and not self.players_name_active:
                if event.key in [pygame.K_RETURN, pygame.K_KP_ENTER]:
                    if not self.token and not self.players_name:
                        self.button_action(get_translated_msg("prompt_auth_data"))
                        return True
                    elif self.play_button_enabled:
                        self.button_action(get_translated_msg("play"))
                        return True
                elif event.key == pygame.K_ESCAPE:
                    self.button_action(get_translated_msg("quit"))
                    return True
        return False
