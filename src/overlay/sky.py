import random
from typing import Dict, Final, Tuple

import pygame

from src.enums import Layer
from src.fblitter import FBLITTER
from src.overlay.game_time import GameTime
from src.settings import (
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
)
from src.sprites.water_drop import WaterDrop


class Sky:
    def __init__(self, game_time: GameTime):
        self.display_surface = pygame.display.get_surface()
        self.game_time = game_time
        self.full_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.volcanic_surf = pygame.Surface(
            (SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA
        )
        # color
        self.colors: Final[Dict[str, Tuple[int, int, int]]] = {
            "6": (215, 235, 255),
            "12": (255, 255, 255),
            "18": (255, 240, 234),
            "20": (255, 219, 203),
            "22": (150, 180, 210),
        }

        self.colors_hours = list(map(int, self.colors.keys()))
        self.colors_rgb = list(self.colors.values())
        self.color = self.get_color()

        # volcanic settings
        self.volcanic_color: Final[Tuple[int, int, int, int]] = (165, 124, 82, 100)

    def get_color(self):
        # get time
        hour, minute = self.game_time.get_time()
        precise_hour = hour + minute / 60

        # find nearest hours in self.colors
        color_index = 0
        for index, color_hour in enumerate(self.colors_hours):
            if precise_hour < color_hour:
                color_index = index - 1
                break
        else:
            color_index = -1

        # start and end colors
        start_color = self.colors_rgb[color_index]
        end_color = self.colors_rgb[color_index + 1]
        start_hour = self.colors_hours[color_index]
        end_hour = self.colors_hours[color_index + 1]

        # just for time intervals like 23:00 - 7:00
        end_hour += 24 * (end_hour <= start_hour)
        precise_hour += 24 * (precise_hour < start_hour)

        # calculate color
        color_perc = (precise_hour - start_hour) / (end_hour - start_hour)
        color = [255, 255, 255]
        for index, (start_value, end_value) in enumerate(
            zip(start_color, end_color, strict=True)
        ):
            color[index] = int(color_perc * end_value + (1 - color_perc) * start_value)

        return color

    def display(self, level: int, rnd_timer: float):
        # draw
        self.color = self.get_color()
        self.full_surf.fill(self.color)
        FBLITTER.blit_with_special_flags(self.full_surf, (0, 0), pygame.BLEND_RGBA_MULT)
        # self.display_surface.blit(
        #     self.full_surf, (0, 0), special_flags=pygame.BLEND_RGBA_MULT
        # )

        is_rnd_7 = level == 7
        if level >= 7 and (not is_rnd_7 or rnd_timer >= 30):
            self.volcanic_surf.fill(self.volcanic_color)
            FBLITTER.schedule_blit(self.volcanic_surf, (0, 0))
            # self.display_surface.blit(self.volcanic_surf, (0, 0))


class Rain:
    def __init__(self, all_sprites, level_frames, map_size=None):
        if map_size is None:
            self.floor_w, self.floor_h = (0, 0)
        else:
            self.set_floor_size(map_size)

        self.all_sprites = all_sprites
        self.floor_frames = level_frames["rain floor"]
        self.drop_frames = level_frames["rain drops"]

    def set_floor_size(self, size: tuple[int, int]):
        self.floor_w, self.floor_h = size

    def create_floor(self):
        WaterDrop(
            surf=random.choice(self.floor_frames),
            pos=(
                random.randint(0, self.floor_w),
                random.randint(0, self.floor_h),
            ),
            moving=False,
            groups=self.all_sprites,
            z=Layer.RAIN_FLOOR,
        )

    def create_drops(self):
        WaterDrop(
            surf=random.choice(self.drop_frames),
            pos=(
                random.randint(0, self.floor_w),
                random.randint(0, self.floor_h),
            ),
            moving=True,
            groups=self.all_sprites,
            z=Layer.RAIN_DROPS,
        )

    def update(self):
        self.create_floor()
        self.create_drops()
