from math import radians, sin
from random import shuffle
from typing import Final, List

import pygame
from pygame.sprite import Group

from src.fblitter import FBLITTER
from src.settings import SCREEN_HEIGHT
from src.sprites.base import Sprite

_ANGLE_STEP: Final[int] = 15
_BUBBLE_WAVE_EXTENT: Final[int] = 20
_shufflable_angles: Final[List[int]] = list(range(0, 180, 15))


class BathBubble(Sprite):
    def __init__(self, sin_angle, pos, surf, groups, z):
        super().__init__(pos, surf, groups, z)
        self._init_pos = pos
        self.reached_end = False
        self.sin_angle = sin_angle
        self._init_ctrx = self.rect.centerx

    def reset(self, sin_angle):
        self.reached_end = False
        self.sin_angle = sin_angle
        self.rect.topleft = self._init_pos
        self._init_ctrx + _BUBBLE_WAVE_EXTENT * sin(radians(self.sin_angle))

    def update(self, dt, *args, **kwargs):
        if self.reached_end:
            return
        self.rect.y -= 180 * dt
        self.sin_angle += _ANGLE_STEP * dt * 20
        self.sin_angle %= 360
        self.rect.centerx = self._init_ctrx + _BUBBLE_WAVE_EXTENT * sin(
            radians(self.sin_angle)
        )
        self.reached_end = self.rect.bottom <= 0


class BubbleMgr:
    _SURF: pygame.Surface | None = None

    @classmethod
    def set_bathbubble_surf(cls, surf: pygame.Surface):
        if cls._SURF is not None:
            return
        cls._SURF = surf

    def __init__(self):
        self.bubble_grp: Group[BathBubble] = Group()
        self.active = False

        shuffle(_shufflable_angles)
        for i in range(7):
            # I personally hate this syntax, but everything has been built this way and it's
            # not worth the hassle to rewrite it all. I tried last summer but it seems everybody
            # decided to reuse it later on... oh well.
            BathBubble(
                _shufflable_angles[i],
                (160 * (i + 1) - 40, SCREEN_HEIGHT + 20 * i),
                self._SURF,
                (self.bubble_grp,),
                0,
            ).add(self.bubble_grp)

    @property
    def finished(self):
        return all(bubble.reached_end for bubble in self.bubble_grp)

    def start(self):
        self.active = True
        self.reset()

    def reset(self):
        shuffle(_shufflable_angles)
        for i, bubble in enumerate(self.bubble_grp):
            bubble.reset(_shufflable_angles[i])

    def update(self, dt, *args, **kwargs):
        if not self.active:
            return
        for bubble in self.bubble_grp:
            bubble.update(dt, *args, **kwargs)
        if self.finished:
            self.active = False

    def draw(self):
        blit_list = [(bubble.image, bubble.rect) for bubble in self.bubble_grp]
        FBLITTER.schedule_blits(blit_list)
