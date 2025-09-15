from collections.abc import Iterable
from typing import Callable

import pygame

from src.colors import (
    SL_CUSTOM_WHITE,
    SL_ORANGE_BRIGHT,
    SL_ORANGE_BRIGHTER,
    SL_ORANGE_DARK,
    SL_ORANGE_MEDIUM,
)
from src.enums import EndAssessmentDimension
from src.fblitter import FBLITTER
from src.gui.menu.abstract_menu import AbstractMenu
from src.gui.menu.components import AbstractButton
from src.screens.minigames.gui import Text, TextChunk, _ReturnButton  # , _draw_box
from src.settings import (
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
    SIA_BORDER_SIZE,
)
from src.sprites.entities.player import Player
from src.support import get_translated_string as get_translated_msg
from src.support import import_font, resource_path

FONT_HEIGHT = 38


class _EndAssessmentButton(AbstractButton):
    _name: str
    _selected: bool

    def __init__(
        self, name: str, img: pygame.Surface, background_color=SL_ORANGE_BRIGHT
    ):
        super().__init__(img, pygame.Rect())
        self._name = name

        self.color = background_color
        self.content = self._content
        self._content_rect = self.content.get_frect()

        self.rect = self._content_rect.copy()
        self.rect.size = SIA_BORDER_SIZE

        self.initial_rect = self.rect.copy()

        self._selected = False

    @property
    def text(self):
        return self._name

    def draw_hover(self):
        if self.mouse_hover():
            self.hover_active = True
            color = SL_ORANGE_MEDIUM
        else:
            self.hover_active = False
            color = self.color

        if self._selected:
            color = SL_ORANGE_BRIGHTER

        FBLITTER.draw_rect(color, self.rect, 0, 2)
        # pygame.draw.rect(self.display_surface, color, self.rect, 0, 2)

    def move(self, topleft: tuple[float, float]):
        self.rect.topleft = topleft
        self.initial_rect.center = self.rect.center
        self._content_rect.center = self.rect.center

    def draw(self, surface: pygame.Surface):
        FBLITTER.set_current_surf(surface)
        FBLITTER.draw_rect(SL_ORANGE_DARK, self.rect.inflate(6, 6), 6, 4)

        self.display_surface = surface
        self.draw_hover()
        self.draw_content()
        FBLITTER.blit_all()

    def change_img(self, new_img: pygame.Surface):
        self._content.fill((0, 0, 0, 0))
        self._content.blit(new_img, (0, 0))

    def select(self):
        self._selected = True

    def deselect(self):
        self._selected = False


class EndAssessmentMenu(AbstractMenu):
    _return_func: Callable[[], None]
    _selection: tuple[EndAssessmentDimension, ...]
    current_dimension_index: int = 0

    selected_end_assessment: _EndAssessmentButton | None
    _selected_scale: int | None

    _continue_button: _ReturnButton | None
    _continue_button_text: str | None

    selected_end_assessment_buttons: list[_EndAssessmentButton]
    _end_assessment_results: dict[str, int]

    _surface: pygame.Surface | None
    _player_name: Player = None

    font_title: pygame.Font

    def __init__(
        self,
        return_func: Callable[[], None],
        selection: Iterable[EndAssessmentDimension],
        player: Player,
    ):
        self._player = player
        self._selection = tuple(selection)
        super().__init__(
            title="", size=(SCREEN_WIDTH, SCREEN_HEIGHT)
        )  # unneeded dummy data

        self.button_top_margin = 32
        self.button_padding = 48
        self.end_ass_button_wp = (
            SIA_BORDER_SIZE[0] + self.button_padding
        )  # Button width
        self.end_ass_button_hp = (
            SIA_BORDER_SIZE[1] + self.button_padding
        )  # Button height

        self._return_func = return_func

        self.current_dimension_index = 0

        self.selected_end_assessment = None
        self._selected_scale = None

        self._continue_button = None
        self._continue_button_text = get_translated_msg("continue")

        self._end_assessment_buttons: list[_EndAssessmentButton] = []
        self._end_assessment_results = {}

        self.button_setup()

        self.box_center = (SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2)
        self.box_padding = (16, 24)
        self.box_size = (
            self.end_ass_button_wp * 7 + self.box_padding[0] * 2,
            FONT_HEIGHT * 3
            + self.end_ass_button_hp
            + self.box_padding[1] * 2
            + self._continue_button.rect.height
            + self.button_top_margin,
        )

        self._surface = None

        self.font_title = import_font(FONT_HEIGHT, "font/LycheeSoda.ttf")

        self.setup()

    @property
    def selected_end_assessment(self):
        return self._selected_end_assessment

    @selected_end_assessment.setter
    def selected_end_assessment(
        self, end_assessment: _EndAssessmentButton | None = None
    ):
        self._selected_end_assessment = end_assessment
        if self._selected_end_assessment is not None:
            self._selected_scale = int(self._selected_end_assessment.text) + 1

    def setup(self):
        self._surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        self._surface.fill((0, 0, 0, 64))
        self._continue_button.move(
            (
                self.box_center[0] - self._continue_button.rect.width / 2,
                self.box_center[1]
                + self.box_size[1] / 2
                - self.box_padding[1]
                - self._continue_button.rect.height,
            )
        )

    def get_description_text(self) -> Text:
        return Text(TextChunk(self.get_question_by_selection(), self.font_title))

    def get_question_by_selection(self):
        description: str = get_translated_msg(
            f"end_assessment_q{self.current_dimension_index + 1}"  # 1 offset for 1-indexing
        )
        return description.format(name=self._player.name or "")

    @staticmethod
    def _load_end_assessment_img(dim: str, i: int) -> pygame.Surface:
        return pygame.image.load(
            resource_path(f"images/sam/{dim}/sam-{dim}-{i + 1}.png")
        ).convert_alpha()

    def _continue(self):
        if not self.selected_end_assessment:
            return

        dimension = self._selection[self.current_dimension_index].name
        assessment = int(self.selected_end_assessment._name)
        self._end_assessment_results[dimension] = assessment

        self.selected_end_assessment.deselect()
        self.selected_end_assessment = None

        if self.current_dimension_index >= len(self._selection) - 1:
            self.current_dimension_index = 0
            self._return_func(self._end_assessment_results)
        else:
            self.current_dimension_index += 1

    def button_action(self, name: str):
        if name == self._continue_button.text:
            self._continue()
        elif name.isdigit() and 0 <= int(name) <= len(self._end_assessment_buttons) - 1:
            if self.selected_end_assessment:
                self.selected_end_assessment.deselect()
            next_selected_end_assessment = self._end_assessment_buttons[int(name)]
            if self.selected_end_assessment == next_selected_end_assessment:
                self.selected_end_assessment = None
            else:
                next_selected_end_assessment.select()
                self.selected_end_assessment = next_selected_end_assessment

    def button_setup(self):
        self._continue_button = _ReturnButton(self._continue_button_text)
        self.buttons.append(self._continue_button)

        for i in range(7):
            btn = _EndAssessmentButton(
                str(i), self.create_image_number(i), SL_CUSTOM_WHITE
            )
            self._end_assessment_buttons.append(btn)

        self.buttons.extend(self._end_assessment_buttons)

    def draw_title(self):
        FBLITTER.schedule_blit(self._surface, (0, 0))

    def create_image_number(self, number, foreground_color="Black") -> pygame.surface:
        return self.numbers_font.render(f"{number}", False, foreground_color)

    def draw_description(self):
        question_text = self.get_question_by_selection()
        lines = question_text.split("\n") if "\n" in question_text else [question_text]

        # Render each line
        line_surfaces: list[pygame.Surface] = []
        line_heights: list[int] = []
        max_width = 0
        line_spacing = 8

        for line in lines:
            t = Text(TextChunk(line, self.font_title))
            surf = pygame.Surface(t.surface_rect.size, pygame.SRCALPHA)
            t.draw(surf)
            line_surfaces.append(surf)
            line_heights.append(surf.get_frect().height)
            max_width = max(max_width, surf.get_frect().width)

        total_height = sum(line_heights) + (len(line_surfaces) - 1) * line_spacing
        text_surface = pygame.Surface((max_width, total_height), pygame.SRCALPHA)

        # Blit each line with spacing
        y = 0
        for i, surf in enumerate(line_surfaces):
            text_surface.blit(surf, ((max_width - surf.get_frect().width) / 2, y))
            y += line_heights[i] + (line_spacing if i < len(line_surfaces) - 1 else 0)

        # description_text = self.get_description_text()
        # text_surface = pygame.Surface(
        #     description_text.surface_rect.size, pygame.SRCALPHA
        # )
        # description_text.draw(text_surface)

        # Clear and redraw the menu box
        self._surface.fill((0, 0, 0, 0))  # fully clear cached surface
        FBLITTER.set_current_surf(self._surface)
        FBLITTER.draw_box(self.box_center, self.box_size)

        description_position = (
            self.box_center[0] - text_surface.get_frect().width / 2,
            self.box_center[1] - self.box_size[1] / 2 + self.box_padding[1],
        )
        FBLITTER.schedule_blit(
            text_surface,
            description_position,
        )
        for i in range(len(self._end_assessment_buttons)):
            x_offset = (
                -(len(self._end_assessment_buttons) - 1) / 1.75 * self.end_ass_button_wp
            )
            current_button = self._end_assessment_buttons[i]
            current_button.move(
                (
                    self.box_center[0] + x_offset + self.end_ass_button_wp * i,
                    self.box_center[1] - SIA_BORDER_SIZE[1] / 2,  # button height
                )
            )
            if i == 0 or i == 6:
                if i == 0:
                    text_key = (
                        f"end_assessment_q{self.current_dimension_index + 1}_left"
                    )
                else:
                    text_key = (
                        f"end_assessment_q{self.current_dimension_index + 1}_right"
                    )
                # text_key: str = translations_map[i] if i in translations_map.keys() else ""
                # if text_key:
                text_surf = self.font.render(
                    get_translated_msg(text_key), False, "Black"
                )
                curr_button_pos = current_button.rect.midbottom
                FBLITTER.schedule_blit(
                    text_surf,
                    (
                        curr_button_pos[0] - text_surf.get_frect().width / 2,
                        curr_button_pos[1] + 10,
                    ),
                )

        FBLITTER.blit_all()
