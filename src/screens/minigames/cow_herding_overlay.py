import math
from typing import Callable

import pygame

from src.colors import SL_ORANGE_BRIGHT, SL_ORANGE_BRIGHTEST
from src.fblitter import FBLITTER
from src.gui.menu.abstract_menu import AbstractMenu
from src.screens.minigames.gui import (
    Linebreak,
    Text,
    TextChunk,
    _draw_box,
    _ReturnButton,
)
from src.settings import SCREEN_HEIGHT, SCREEN_WIDTH
from src.support import get_outline, import_font
from src.support import get_translated_string as get_translated_msg


class _CowHerdingScoreboard(AbstractMenu):
    _return_func: Callable[[], None]

    _return_button: _ReturnButton | None
    _return_button_text: str

    _surface: pygame.Surface | None

    font_title: pygame.Font
    font_number: pygame.Font
    font_description: pygame.Font
    font_button: pygame.Font

    def __init__(self, return_func: Callable[[], None]):
        super().__init__(
            title=get_translated_msg("cow_herding_title"),
            size=(SCREEN_WIDTH, SCREEN_HEIGHT),
        )

        self._return_func = return_func

        self._return_button = None
        self._return_button_text = get_translated_msg("return_to_town")

        self._surface = None

        self.font_title = import_font(48, "font/LycheeSoda.ttf")
        self.font_number = import_font(36, "font/LycheeSoda.ttf")
        self.font_description = import_font(24, "font/LycheeSoda.ttf")
        self.font_button = import_font(32, "font/LycheeSoda.ttf")

    def setup(
        self,
        time_needed: float,
        cows_herded_in: int,
        opp_time: float,
        is_outgroup: bool = False,
    ):
        box_center = (SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2)
        padding = (16, 24)

        self._surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        self._surface.fill((0, 0, 0, 64))

        self.button_setup()

        button_top_margin = 32
        button_area_height = self._return_button.rect.height + button_top_margin

        text = Text(
            TextChunk(get_translated_msg("finished_minigame"), self.font_title),
            Linebreak(),
            TextChunk(f"{time_needed:.2f} ", self.font_number),
            TextChunk(get_translated_msg("self_time"), self.font_description),
            Linebreak(),
            TextChunk(
                get_translated_msg(
                    f"{'in' if is_outgroup else 'out'}group_time"
                ).format(opp_time),
                self.font_description,
            ),
            Linebreak(),
            TextChunk(
                get_translated_msg(f"{'out' if is_outgroup else 'in'}grp_cheer")
                if opp_time > time_needed
                else get_translated_msg(
                    f"{'out' if is_outgroup else 'in'}grp_disappointed"
                ),
                self.font_description,
            ),
            Linebreak(),
            TextChunk(
                get_translated_msg("[money win]")
                if opp_time > time_needed
                else get_translated_msg("[money lost]"),
                self.font_description,
            ),
        )
        box_size = (
            text.surface_rect.width + padding[0] * 2,
            text.surface_rect.height + padding[1] * 2 + button_area_height,
        )

        _draw_box(self._surface, box_center, box_size)

        text_surface = pygame.Surface(text.surface_rect.size, pygame.SRCALPHA)
        text.draw(text_surface)
        self._surface.blit(
            text_surface,
            (
                box_center[0] - text.surface_rect.width / 2,
                box_center[1] - text.surface_rect.height / 2 - button_area_height / 2,
            ),
        )

        self._return_button.move(
            (
                box_center[0] - self._return_button.rect.width / 2,
                box_center[1]
                - self._return_button.rect.height
                + box_size[1] / 2
                - padding[1],
            )
        )

    def button_action(self, name: str):
        if name == self._return_button.text:
            self._return_func()

    def button_setup(self):
        self._return_button = _ReturnButton(self._return_button_text)
        self.buttons.append(self._return_button)

    def draw_title(self):
        FBLITTER.schedule_blit(self._surface, (0, 0))
        # self.display_surface.blit(self._surface, (0, 0))

    def update(self, dt):
        self.mouse_hover()

        self.update_buttons(dt)

    def draw_description(self):
        pass


class _CowHerdingOverlay:
    display_surface: pygame.Surface

    font_countdown: pygame.Font
    font_timer: pygame.Font

    font_description: pygame.Font
    font_objective: pygame.Font

    timer_chars: dict[str, pygame.Surface]
    timer_char_width: int
    timer_char_height: int

    def __init__(self):
        self.display_surface = pygame.display.get_surface()

        self.font_countdown = import_font(128, "font/LycheeSoda.ttf")
        self.font_timer = import_font(48, "font/LycheeSoda.ttf")

        self.font_description = import_font(32, "font/LycheeSoda.ttf")
        self.font_objective = import_font(24, "font/LycheeSoda.ttf")

        # maps all chars in "0123456789.:" to pygame surfaces rendered with font_timer
        self.timer_chars = {
            char: self.font_timer.render(char, True, SL_ORANGE_BRIGHTEST)
            for char in "0123456789.:"
        }
        # ensures that the timer numbers maintain their position by using equal spacing
        self.timer_char_width = max(
            char.get_width() for char in self.timer_chars.values()
        )
        self.timer_char_height = max(
            char.get_height() for char in self.timer_chars.values()
        )

    def _render_countdown_text(self, text: str):
        rendered_text = self.font_countdown.render(text, False, SL_ORANGE_BRIGHTEST)
        rendered_text = get_outline(rendered_text, SL_ORANGE_BRIGHT, resize=True)
        return rendered_text

    def draw_countdown(
        self, current_time: float, ready_up_duration: int, cd_duration: int
    ):
        """
        Displays "Ready?" if current_time < ready_up_duration,
        ceil(abs(current_time)) if current_time < sum(durations),
        else "GO!"
        :param current_time: current time in seconds (between 0 and sum(durations))
        :param ready_up_duration: duration of the "Ready?" prompt
        :param cd_duration: duration of the countdown
        """
        current_time_int = math.floor(current_time)
        current_fraction = current_time - current_time_int

        if current_time_int < ready_up_duration:
            rendered_text = self._render_countdown_text(get_translated_msg("ready"))
            if ready_up_duration - 0.5 < current_time:
                rendered_text = pygame.transform.scale_by(
                    rendered_text,
                    max(0.0, 1 - ((current_fraction - 0.5) * 2) * 4.5 / 2),
                )
                alpha = 1 - ((current_fraction - 0.5) * 2) * 4.5 / 2
                rendered_text.set_alpha(max(0, int(alpha * 255)))

            FBLITTER.schedule_blit(
                rendered_text,
                (
                    SCREEN_WIDTH / 2 - rendered_text.get_width() / 2,
                    SCREEN_HEIGHT / 3 - rendered_text.get_height() / 2,
                ),
            )
            # self.display_surface.blit(
            #     rendered_text,
            #     (
            #         SCREEN_WIDTH / 2 - rendered_text.get_width() / 2,
            #         SCREEN_HEIGHT / 3 - rendered_text.get_height() / 2,
            #     ),
            # )

        elif current_time_int < ready_up_duration + cd_duration:
            rendered_text = self._render_countdown_text(
                f"{abs(ready_up_duration + cd_duration - current_time_int)}"
            )

            if current_fraction <= 0.25:
                rendered_text = pygame.transform.scale_by(
                    rendered_text, current_fraction * 4.5
                )
                alpha = current_fraction * 4 * 1.5 - 0.5
                rendered_text.set_alpha(max(0, int(alpha * 255)))

        else:
            rendered_text = self._render_countdown_text(get_translated_msg("go"))

            if current_fraction <= 1 / 4:
                rendered_text = pygame.transform.scale_by(
                    rendered_text,
                    math.sin(current_fraction * 4 * 2 * math.pi + math.pi) / 8 + 1,
                )
                alpha = current_fraction * 4 * 1.5 - 0.5
                rendered_text.set_alpha(max(0, int(alpha * 255)))

        FBLITTER.schedule_blit(
            rendered_text,
            (
                SCREEN_WIDTH / 2 - rendered_text.get_width() / 2,
                SCREEN_HEIGHT / 3 - rendered_text.get_height() / 2,
            ),
        )
        # self.display_surface.blit(
        #     rendered_text,
        #     (
        #         SCREEN_WIDTH / 2 - rendered_text.get_width() / 2,
        #         SCREEN_HEIGHT / 3 - rendered_text.get_height() / 2,
        #     ),
        # )

    def draw_description(self):
        box_center = (SCREEN_WIDTH / 2, SCREEN_HEIGHT / 4)

        text = Text(
            TextChunk(get_translated_msg("cow_minigame_desc"), self.font_description),
            Linebreak(),
            Linebreak((0, 24)),
            TextChunk(
                get_translated_msg("cow_minigame_desc_l1"), self.font_description
            ),
            Linebreak(),
            TextChunk(
                get_translated_msg("cow_minigame_desc_l2"), self.font_description
            ),
        )

        FBLITTER.draw_box(box_center, text.surface_rect.size)

        text_surface = pygame.Surface(text.surface_rect.size, pygame.SRCALPHA)
        text.draw(text_surface)
        FBLITTER.schedule_blit(
            text_surface,
            (
                box_center[0] - text.surface_rect.width / 2,
                box_center[1] - text.surface_rect.height / 2,
            ),
        )
        # self.display_surface.blit(
        #     text_surface,
        #     (
        #         box_center[0] - text.surface_rect.width / 2,
        #         box_center[1] - text.surface_rect.height / 2,
        #     ),
        # )

    def draw_objective(
        self,
        own_cows_total: int,
        own_cows_herded_in: int,
        opp_cows_total: int,
        opp_cows_herded_in: int,
        is_outgrp: bool = False,
    ):
        box_top_right = (SCREEN_WIDTH, 0)
        padding = 12

        text = Text(
            TextChunk(get_translated_msg("goal"), self.font_description),
            Linebreak(),
            TextChunk(get_translated_msg("ch_goal"), self.font_objective),
            Linebreak((0, 32)),
            TextChunk(
                get_translated_msg(f"{'out' if is_outgrp else 'in'}group_score"),
                self.font_objective,
            ),
            Linebreak(),
            TextChunk(
                f"({own_cows_herded_in}/{own_cows_total}) "
                + get_translated_msg("cow_count"),
                self.font_objective,
            ),
            Linebreak((0, 32)),
            TextChunk(
                get_translated_msg(f"{'in' if is_outgrp else 'out'}group_score"),
                self.font_objective,
            ),
            Linebreak(),
            TextChunk(
                f"({opp_cows_herded_in}/{opp_cows_total}) "
                + get_translated_msg("cow_count"),
                self.font_objective,
            ),
        )

        FBLITTER.draw_box(
            (
                box_top_right[0] - text.surface_rect.width / 2,
                box_top_right[1] + text.surface_rect.height / 2,
            ),
            (
                text.surface_rect.width + padding * 2,
                text.surface_rect.height + padding * 2,
            ),
        )

        text_surface = pygame.Surface(text.surface_rect.size, pygame.SRCALPHA)
        text.draw(text_surface)
        FBLITTER.schedule_blit(
            text_surface,
            (
                box_top_right[0] - text.surface_rect.width - padding,
                box_top_right[1] + padding,
            ),
        )
        # self.display_surface.blit(
        #     text_surface,
        #     (
        #         box_top_right[0] - text.surface_rect.width - padding,
        #         box_top_right[1] + padding,
        #     ),
        # )

    def draw_timer(self, current_time: float):
        t = max(0.0, current_time)
        timer_string = (
            f"{int(t / 60):02}"
            + ":"
            + f"{(int(t) - int(t / 60) * 60):02}"
            + "."
            + f"{t - int(t):.2f}"[2:]
        )

        total_length = 0

        for char in timer_string:
            if char.isdigit():
                total_length += self.timer_char_width
            else:
                total_length += self.timer_chars[char].get_width()

        FBLITTER.draw_box(
            (SCREEN_WIDTH / 2, 0),
            (total_length, self.timer_char_height + 32),
        )

        current_length = 0

        offset_y = 3

        for char in timer_string:
            FBLITTER.schedule_blit(
                self.timer_chars[char],
                (SCREEN_WIDTH / 2 - total_length / 2 + current_length, offset_y),
            )
            # self.display_surface.blit(
            #     self.timer_chars[char],
            #     (SCREEN_WIDTH / 2 - total_length / 2 + current_length, offset_y),
            # )
            if char.isdigit():
                current_length += self.timer_char_width
            else:
                current_length += self.timer_chars[char].get_width()
