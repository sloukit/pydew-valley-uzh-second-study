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
from src.enums import StartAssessmentDimension
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


class _StartAssessmentButton(AbstractButton):
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


class StartAssessmentMenu(AbstractMenu):
    _return_func: Callable[[], None]
    _selection: tuple[StartAssessmentDimension, ...]
    _current_dimension_index: int = 0
    _current_dimension: StartAssessmentDimension

    selected_start_assessment: _StartAssessmentButton | None
    _selected_scale: int | None

    _continue_button: _ReturnButton | None
    _continue_button_text: str | None

    selected_start_assessment_buttons: list[_StartAssessmentButton]
    _start_assessment_results: dict[str, int]

    _surface: pygame.Surface | None
    _player_name: Player = None

    font_title: pygame.Font

    def __init__(
        self,
        return_func: Callable[[], None],
        selection: Iterable[StartAssessmentDimension],
        player: Player,
    ):
        self._player = player
        self._selection = tuple(selection)
        super().__init__(
            title=self.get_question_by_selection(), size=(SCREEN_WIDTH, SCREEN_HEIGHT)
        )

        self.button_top_margin = 32
        self.start_assessment_button_padding = 48
        self.start_assessment_button_w = SIA_BORDER_SIZE[0]
        self.start_assessment_button_h = SIA_BORDER_SIZE[1]

        self.start_assessment_button_wp = (
            self.start_assessment_button_w + self.start_assessment_button_padding
        )
        self.start_assessment_button_hp = (
            self.start_assessment_button_h + self.start_assessment_button_padding
        )

        self.box_center = (SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2)
        self.description = self.get_question_by_selection()
        self._return_func = return_func

        self.current_dimension_index = 0

        self.selected_start_assessment = None
        self._selected_scale = None

        self._continue_button = None
        self._continue_button_text = get_translated_msg("continue")

        self._start_assessment_buttons: list[_StartAssessmentButton] = []
        self._start_assessment_results = {}

        self._surface = None

        self.font_title = import_font(38, "font/LycheeSoda.ttf")

        self.setup()

    @property
    def current_dimension_index(self):
        return self._current_dimension_index

    @current_dimension_index.setter
    def current_dimension_index(self, index: int):
        self._current_dimension_index = index
        self._current_dimension = self._selection[self.current_dimension_index]

    @property
    def selected_start_assessment(self):
        return self._selected_start_assessment

    @selected_start_assessment.setter
    def selected_start_assessment(
        self, start_assessment: _StartAssessmentButton | None = None
    ):
        self._selected_start_assessment = start_assessment
        if self._selected_start_assessment is not None:
            self._selected_scale = int(self._selected_start_assessment.text) + 1

    def setup(self):
        padding = (16, 24)

        self._surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        self._surface.fill((0, 0, 0, 64))

        self.button_setup()

        button_area_height = self._continue_button.rect.height + self.button_top_margin

        description_text_surface: pygame.Rect = self.get_description_text().surface_rect

        box_size = (
            self.start_assessment_button_wp * 7 + padding[0] * 2,
            description_text_surface.height
            + self.start_assessment_button_hp
            + padding[1] * 2
            + button_area_height,
        )

        FBLITTER.set_current_surf(self._surface)
        FBLITTER.draw_box(self.box_center, box_size)

        self._continue_button.move(
            (
                self.box_center[0] - self._continue_button.rect.width / 2,
                self.box_center[1]
                - self._continue_button.rect.height
                + box_size[1] / 2
                - padding[1],
            )
        )

        translations_map: dict[int, str] = {
            0: "start_assessment_left_info",
            6: "start_assessment_right_info",
        }

        for i in range(len(self._start_assessment_buttons)):
            x_offset = (
                -(len(self._start_assessment_buttons) - 1)
                / 1.75
                * self.start_assessment_button_wp
            )
            current_button = self._start_assessment_buttons[i]
            current_button.move(
                (
                    self.box_center[0] + x_offset + self.start_assessment_button_wp * i,
                    self.box_center[1] - self.start_assessment_button_h / 2,
                )
            )

            text_key: str = translations_map[i] if i in translations_map.keys() else ""
            if text_key:
                text_surf = self.font.render(
                    get_translated_msg(text_key), False, "Black"
                )
                if i == 0:
                    xpos = current_button.rect.bottomleft[0]
                else:
                    xpos = current_button.rect.bottomright[0]-text_surf.get_frect().width
                FBLITTER.schedule_blit(
                    text_surf,
                    (
                        xpos,
                        current_button.rect.bottomleft[1] + 10,
                    ),
                )
                # self._surface.blit(
                #     text_surf,
                #     (
                #         current_button_bottom_left[0] - half_width_of_text,
                #         current_button_bottom_left[1] + 10,
                #     ),
                # )
        FBLITTER.blit_all()

    def get_description_text(self) -> Text:
        return Text(TextChunk(self.get_question_by_selection(), self.font_title))

    def get_question_by_selection(self):
        description: str = get_translated_msg(
            f"start_assessment_q{self._selection[self.current_dimension_index] + 1}"
        )
        return description.format(name=self._player.name or "")

    @staticmethod
    def _load_start_assessment_img(dim: str, i: int) -> pygame.Surface:
        return pygame.image.load(
            resource_path(f"images/sam/{dim}/sam-{dim}-{i + 1}.png")
        ).convert_alpha()

    def _continue(self):
        if not self.selected_start_assessment:
            return

        dimension = self._selection[self.current_dimension_index].name
        assessment = int(self.selected_start_assessment._name)
        self._start_assessment_results[dimension] = assessment

        self.selected_start_assessment.deselect()
        self.selected_start_assessment = None

        if self.current_dimension_index >= len(self._selection) - 1:
            self.current_dimension_index = 0
            self._return_func(self._start_assessment_results)
        else:
            self.current_dimension_index += 1

    def button_action(self, name: str):
        if name == self._continue_button.text:
            self._continue()
        elif (
            name.isdigit() and 0 <= int(name) <= len(self._start_assessment_buttons) - 1
        ):
            if self.selected_start_assessment:
                self.selected_start_assessment.deselect()
            next_selected_start_assessment = self._start_assessment_buttons[int(name)]
            if self.selected_start_assessment == next_selected_start_assessment:
                self.selected_start_assessment = None
            else:
                next_selected_start_assessment.select()
                self.selected_start_assessment = next_selected_start_assessment

    def button_setup(self):
        self._continue_button = _ReturnButton(self._continue_button_text)
        self.buttons.append(self._continue_button)

        for i in range(7):
            btn = _StartAssessmentButton(
                str(i), self.create_image_number(i), SL_CUSTOM_WHITE
            )
            self._start_assessment_buttons.append(btn)

        self.buttons.extend(self._start_assessment_buttons)

    def draw_title(self):
        FBLITTER.schedule_blit(self._surface, (0, 0))

    def create_image_number(self, number, foreground_color="Black") -> pygame.surface:
        return self.numbers_font.render(f"{number}", False, foreground_color)

    def draw_description(self):
        description_text = self.get_description_text()
        button_area_height = self._continue_button.rect.height + self.button_top_margin
        text_surface = pygame.Surface(
            description_text.surface_rect.size, pygame.SRCALPHA
        )
        description_text.draw(text_surface)

        description_position = (
            self.box_center[0] - description_text.surface_rect.width / 2,
            self.box_center[1]
            - description_text.surface_rect.height / 2
            - self.start_assessment_button_hp / 2
            - button_area_height / 2,
        )
        text_rect = text_surface.get_frect(
            top=description_position[1],
            left=self.rect.left + 50,
            width=self.rect.width - 100,
        )
        FBLITTER.set_current_surf(self._surface)
        FBLITTER.draw_rect(SL_ORANGE_BRIGHT, text_rect)
        FBLITTER.schedule_blit(
            text_surface,
            description_position,
        )
        FBLITTER.blit_all()
