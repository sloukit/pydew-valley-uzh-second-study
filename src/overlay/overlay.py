from collections.abc import Callable
from typing import Any

import pygame

from src.enums import ClockVersion
from src.fblitter import FBLITTER
from src.gui.health_bar import HealthProgressBar
from src.npc.npcs_state_registry import NpcsStateRegistry
from src.overlay.bath_info import BathInfo
from src.overlay.box_keybindings import BoxKeybindings, BoxKeybindingsLabel
from src.overlay.clock import Clock
from src.overlay.dead_npcs_box import DeadNpcsBox
from src.overlay.fps import FPS
from src.overlay.game_time import GameTime
from src.overlay.money import Money
from src.settings import OVERLAY_POSITIONS


class Overlay:
    def __init__(
        self,
        entity,
        item_frames,
        game_time: GameTime,
        get_world_time: Callable[[None], tuple[int, int]],
        clock: pygame.time.Clock,
        round_config: dict[str, Any],
        npcs_state_registry: NpcsStateRegistry,
    ) -> None:
        # general setup
        self.display_surface = pygame.display.get_surface()
        self.player = entity

        self.box_keybindings = BoxKeybindings()
        self.dead_npcs_box = DeadNpcsBox(npcs_state_registry)
        self.bath_info = BathInfo()

        # imports
        self.item_frames = item_frames

        self.visible = True

        # ui objects
        self.health_bar = HealthProgressBar(self.player)

        self.clock = Clock(game_time, get_world_time, ClockVersion.DIGITAL)
        self.FPS = FPS(clock)
        self.box_keybindings_label = BoxKeybindingsLabel(entity)
        self.money = Money(entity)

        self.round_config = round_config
        self.is_debug_mode_version: bool = False

    def display(self, current_round: int = 1):
        if not self.visible:
            return

        # seeds
        seed_surf = self.item_frames[self.player.get_current_seed_string()]
        seed_rect = seed_surf.get_frect(midbottom=OVERLAY_POSITIONS["seed"])
        FBLITTER.schedule_blit(seed_surf, seed_rect)
        # self.display_surface.blit(seed_surf, seed_rect)

        # Money amount display
        self.money.display()

        # Dead npcs amount display
        self.dead_npcs_box.display()

        # Box keybindings label display
        self.box_keybindings_label.display()
        self.box_keybindings.draw(self.display_surface, current_round)

        # tool
        tool_surf = self.item_frames[self.player.get_current_tool_string()]
        tool_rect = tool_surf.get_frect(midbottom=OVERLAY_POSITIONS["tool"])
        FBLITTER.schedule_blit(tool_surf, tool_rect)
        # self.display_surface.blit(tool_surf, tool_rect)

        self.clock.display()
        if self.is_debug_mode_version:
            self.FPS.display()

        # health bar
        if self.round_config.get("healthbar", False):
            self.health_bar.draw(self.display_surface, self.player.in_outgroup)

        # bath info display
        self.bath_info.display(current_round)
