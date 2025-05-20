import textwrap
from abc import ABC, ABCMeta, abstractmethod
from operator import attrgetter

import pygame

from src import utils
from src.enums import Layer
from src.fblitter import FBLITTER
from src.settings import GVT_TB_SIZE, TB_SIZE
from src.sprites.base import Sprite
from src.support import resource_path
from src.timer import Timer


class AbstractTextBoxMeta(ABCMeta, type(Sprite)):
    pass


class AbstractTextBox(ABC, metaclass=AbstractTextBoxMeta):
    _TB_IMAGE: pygame.Surface | None = None
    _CNAME_SURF_RECT: pygame.Rect = pygame.Rect(8, 0, 212, 67)
    _TXT_SURF_REGULAR_AREA: pygame.Rect = pygame.Rect()

    @classmethod
    @abstractmethod
    def _prepare_base_tb_image(
        cls, cname_surf: pygame.Surface, txt_surf: pygame.Surface
    ):
        pass

    @classmethod
    @abstractmethod
    def _get_max_txt_width(cls):
        return 0

    @classmethod
    @abstractmethod
    def _get_tb_size(cls):
        return (0, 0)

    @abstractmethod
    def _prepare_image(self):
        pass

    def _advance_by_one(self):
        self._chr_index += 1
        if self._chr_index >= len(self.text):
            self._finished_advancing = True
        else:
            self._txt_needs_rerender = True

    @abstractmethod
    def _prerender_text_ani(self):
        pass

    @property
    def finished_advancing(self):
        return self._finished_advancing

    @finished_advancing.setter
    def finished_advancing(self, val: bool):
        self._finished_advancing = val
        if val:
            self._chr_index = len(self.text)

    @abstractmethod
    def __init__(self, character_name: str, text: str, font: pygame.Font):
        self.font = font
        self.name = character_name
        max_text_width = self._get_max_txt_width()
        estimated_character_width = self.font.size("M")[
            0
        ]  # Get width of a normal character
        # Adjust dynamically
        adjusted_chars_per_line = max_text_width // estimated_character_width

        self.text = textwrap.fill(text, width=adjusted_chars_per_line)

        self.image = pygame.Surface(self._get_tb_size(), flags=pygame.SRCALPHA)
        self._prepare_image()
        self._tmp_img = self._TB_IMAGE.copy()

        cname: pygame.Surface = self.font.render(
            self.name, True, color=pygame.Color("black")
        )
        cname_rect = cname.get_rect(center=self._CNAME_SURF_RECT.center)
        self._tmp_img.blit(cname, cname_rect)
        self._fin_img = self.image
        self.timer = Timer(50, True, autostart=False, func=self._advance_by_one)
        self.image = self._tmp_img.copy()

        self._finished_advancing = False
        self._txt_needs_rerender = True
        self._chr_index = 1


class TBBase(Sprite, AbstractTextBox):
    @classmethod
    def _get_max_txt_width(cls):
        return 0

    def _prepare_image(self):
        pass

    @classmethod
    def _get_tb_size(cls):
        return (0, 0)

    def _prerender_text_ani(self):
        pass

    @classmethod
    def _prepare_base_tb_image(
        cls, cname_surf: pygame.Surface, txt_surf: pygame.Surface
    ):
        pass

    def __init__(
        self, character_name: str, text: str, font: pygame.Font, left: int, top: int
    ):
        AbstractTextBox.__init__(self, character_name, text, font)
        Sprite.__init__(
            self, (left, top), self.image, (), z=Layer.TEXT_BOX, name=character_name
        )

    def draw(self, display_surface: pygame.Surface, rect: pygame.Rect, camera):
        FBLITTER.schedule_blit(self.image, self.rect)
        # display_surface.blit(self.image, self.rect)

    def update(self, *args, **kwargs):
        if not self.timer:
            self.timer.activate()
        self.timer.update()
        # Keeping variable args tuple and keyword arguments dict syntax for compatibility with base method
        if self._finished_advancing and self.image is not self._fin_img:
            self.image = self._fin_img
        elif not self._finished_advancing and self._txt_needs_rerender:
            self._prerender_text_ani()


class TextBox(TBBase):
    """Text box sprite that contains a part of text."""

    _TXT_SURF_EXTREMITIES: tuple[pygame.Rect, pygame.Rect] = (
        pygame.Rect(0, 0, 14, 302),
        pygame.Rect(473, 0, 18, 302),
    )
    _TXT_SURF_REGULAR_AREA: pygame.Rect = pygame.Rect(24, 0, 1, 302)
    _TXT_SURF_RECT: pygame.Rect = pygame.Rect(0, 64, TB_SIZE[0], TB_SIZE[1] - 64)
    _TB_IMAGE: pygame.Surface | None = None

    @classmethod
    def prepare_base_tb_image(
        cls, cname_surf: pygame.Surface, txt_surf: pygame.Surface
    ):
        if cls._TB_IMAGE is not None:
            return
        cls._TB_IMAGE = pygame.Surface(TB_SIZE, flags=pygame.SRCALPHA)
        start = txt_surf.subsurface(cls._TXT_SURF_EXTREMITIES[0])
        regular = txt_surf.subsurface(cls._TXT_SURF_REGULAR_AREA)
        end = txt_surf.subsurface(cls._TXT_SURF_EXTREMITIES[1])
        txt_part_top = 74
        blit_list = [
            (start, pygame.Rect(0, txt_part_top, *start.get_size())),
            (end, pygame.Rect(473, txt_part_top, *end.get_size())),
            *(
                (regular, pygame.Rect(x, txt_part_top, *regular.get_size()))
                for x in range(start.get_width(), 473)
            ),
            (cname_surf, cls._CNAME_SURF_RECT),
        ]
        cls._TB_IMAGE.fblits(blit_list)

    @classmethod
    def _get_max_txt_width(cls):
        return TB_SIZE[0] - 6

    @classmethod
    def _get_tb_size(cls):
        return TB_SIZE

    def __init__(
        self, character_name: str, text: str, font: pygame.Font, left: int, top: int
    ):
        """Create a text box.

        :param character_name: The character meant to speak using this text box.
        :param text: The dialogue the character is supposed to say.
        :param font: The font used to render this dialogue.
        :param left: The value used to set the left side position of the box
        :param top:  The value used to set the top side position of the box"""

        super().__init__(character_name, text, font, left, top)

    def _prerender_text_ani(self):
        text_surf = self.font.render(
            self.text[: self._chr_index], True, color=pygame.Color("black")
        )
        text_rect = text_surf.get_rect(topleft=(15, 90))
        blit_list = [(self._tmp_img, (0, 0)), (text_surf, text_rect)]
        self.image.fblits(blit_list)
        self._txt_needs_rerender = False

    def _prepare_image(self):
        cname = self.font.render(self.name, True, color=pygame.Color("black"))
        cname_rect = cname.get_rect(center=self._CNAME_SURF_RECT.center)
        text_surf = self.font.render(self.text, True, color=pygame.Color("black"))
        text_rect = text_surf.get_rect(topleft=(15, 90))
        blit_list = [
            (self._TB_IMAGE, (0, 0)),
            (cname, cname_rect),
            (text_surf, text_rect),
        ]
        self.image.fblits(blit_list)


def prepare_tb_image(cname_surf: pygame.Surface, txt_surf: pygame.Surface):
    TextBox.prepare_base_tb_image(cname_surf, txt_surf)


class GvtTextBox(TBBase):
    @classmethod
    def _prepare_base_tb_image(
        cls, cname_surf: pygame.Surface, txt_surf: pygame.Surface
    ):
        if cls._TB_IMAGE is not None:
            return
        cls._TB_IMAGE = txt_surf.copy()
        cls._TB_IMAGE.blit(cname_surf, (436, 120))

    def _prerender_text_ani(self):
        text_surf = self.font.render(
            self.text[: self._chr_index], True, color=pygame.Color("black")
        )
        text_rect = text_surf.get_rect(topleft=(15, 90))
        blit_list = [(self._tmp_img, (0, 0)), (text_surf, text_rect)]
        self.image.fblits(blit_list)
        self._txt_needs_rerender = False

    def _prepare_image(self):
        cname = self.font.render(self.name, True, color=pygame.Color("black"))
        cname_rect = cname.get_rect(center=self._CNAME_SURF_RECT.center)
        text_surf = self.font.render(self.text, True, color=pygame.Color("black"))
        text_rect = text_surf.get_rect(topleft=(15, 90))
        blit_list = [
            (self._TB_IMAGE, (0, 0)),
            (cname, cname_rect),
            (text_surf, text_rect),
        ]
        self.image.fblits(blit_list)

    def __init__(
        self, character_name: str, text: str, font: pygame.Font, left: int, top: int
    ):
        """Create a government text box.

        :param character_name: The character meant to speak using this text box.
        :param text: The dialogue the character is supposed to say.
        :param font: The font used to render this dialogue.
        :param left: The value used to set the left side position of the box
        :param top:  The value used to set the top side position of the box"""
        super().__init__(character_name, text, font, left, top)

    @classmethod
    def _get_max_txt_width(cls):
        return 364

    @classmethod
    def _get_tb_size(cls):
        return GVT_TB_SIZE


class DialogueManager:
    """Dialogue manager object.
    This class will store all dialogues and has a method to show a dialogue on-screen."""

    def __init__(self, sprite_group: pygame.sprite.Group, dialogue_file_path: str):
        self.spr_grp: pygame.sprite.Group = sprite_group
        # Open the dialogues file and dump all of its content in here,
        # while purging the raw file content from its comments.
        with open(resource_path(dialogue_file_path), "r") as dialogue_file:
            self.dialogues: dict[str, list[list[str, str]]] = utils.json_loads(
                dialogue_file.read()
            )
        self._tb_list: list[TBBase] = []
        self._msg_index: int = 0
        self._showing_dialogue: bool = False
        self.font: pygame.Font = pygame.font.Font(
            resource_path("font/LycheeSoda.ttf"), 20
        )

    showing_dialogue = property(attrgetter("_showing_dialogue"))

    def _purge_tb_list(self):
        for tb in self._tb_list:
            tb.kill()
        self._tb_list.clear()
        self._msg_index = 0

    def _create_tb(self, cname: str, txt: str, left: int, top: int):
        self._tb_list.append(TextBox(cname, txt, self.font, left, top))

    def _push_current_tb_to_foreground(self):
        if not self._msg_index:
            self._tb_list[0].add(self.spr_grp)
            return
        self._tb_list[self._msg_index - 1].kill()
        self._tb_list[self._msg_index].add(self.spr_grp)

    def _get_current_tb(self):
        return self._tb_list[self._msg_index]

    def _create_gvt_tb(self, cname: str, txt: str, left: int, top: int):
        self._tb_list.append(GvtTextBox(cname, txt, self.font, left, top))

    def open_gvt_dialogue(self, dial: str, left: int, top: int):
        if self._showing_dialogue:
            return

        try:
            dial_info = self[dial]
        except LookupError as exc:
            raise ValueError(f"dialogue ID '{dial}' does not exist") from exc

        if self._msg_index:
            self._purge_tb_list()

        self._showing_dialogue = True

        for cname, portion in dial_info:
            self._create_gvt_tb(cname, portion, left, top)

        self._push_current_tb_to_foreground()

    def open_dialogue(self, dial: str, left: int, top: int):
        """Opens a text box with the current dialogue ID's first text showed on-screen.
        Does nothing if a text box is already on-screen.
        :param dial: The dialogue ID for which you want to open textboxes on the screen.
        :param left: The value used to set the left side position of the textboxes
        :param top:  The value used to set the top side position of the textboxes
        :raise ValueError: if the given dialogue ID does not exist."""
        if self._showing_dialogue:
            return

        try:
            dial_info = self[dial]
        except LookupError as exc:
            raise ValueError(f"dialogue ID '{dial}' does not exist") from exc

        if self._msg_index:
            self._purge_tb_list()

        self._showing_dialogue = True

        for cname, portion in dial_info:
            self._create_tb(cname, portion, left, top)

        self._push_current_tb_to_foreground()

    def close_dialogue(self) -> None:
        self._purge_tb_list()
        self._showing_dialogue = False

    @property
    def current_tb_finished_advancing(self):
        return self._get_current_tb().finished_advancing

    def advance(self, allow_skip_to_next_msg=True):
        """Show the next part of the current dialogue, or forces the current textbox to display
        the whole text before it finishes typing.
        If the end of the dialogue is reached, clears the textboxes away
        from the screen and returns control to the player."""
        if not self._get_current_tb().finished_advancing:
            # Textbox is still animating, forcing it to skip to the end
            self._get_current_tb().finished_advancing = True
            return
        if not allow_skip_to_next_msg:
            return
        self._msg_index += 1
        if self._msg_index >= len(self._tb_list):
            # Reached the end of the dialogue, clear everything away to make space for the next dialogue
            self.close_dialogue()
            return
        self._push_current_tb_to_foreground()

    def __getitem__(self, item: str) -> list[list[str, str]]:
        return self.dialogues[item]

    def set_item(self, item: str, value: list[list[str, str]]) -> None:
        self.dialogues[item] = value
