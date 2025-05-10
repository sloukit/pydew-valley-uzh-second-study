import pygame

from src.npc.dead_npcs_registry import DeadNpcsRegistry
from src.settings import OVERLAY_POSITIONS
from src.support import import_font


class DeadNpcsBox:
    def __init__(self, dead_npcs_registry: DeadNpcsRegistry):
        # setup
        self.display_surface = pygame.display.get_surface()
        self.dead_npcs_registry = dead_npcs_registry

        # dimensions
        self.left = 20
        self.top = 50

        width, height = 240, 80
        self.font = import_font(20, "font/LycheeSoda.ttf")

        self.rect = pygame.Rect(self.left, self.top, width, height)

        self.rect.topleft = OVERLAY_POSITIONS["dead_npcs_box"]

    def display(self):
        black = "Black"
        background_color = "Red"
        foreground_color = black

        # rects and surfs

        dead_ingroup_members_surf = self.font.render(
            f"Died in-group members: {self.dead_npcs_registry.get_ingroup_deaths_amount()}",
            False,
            foreground_color,
        )
        dead_ingroup_members_rect = dead_ingroup_members_surf.get_frect(
            midleft=(self.rect.left + 10, self.rect.top + 20)
        )
        dead_outgroup_members_surf = self.font.render(
            f"Died out-group members: {self.dead_npcs_registry.get_outgroup_deaths_amount()}",
            False,
            foreground_color,
        )
        dead_outgroup_members_rect = dead_outgroup_members_surf.get_frect(
            midleft=(self.rect.left + 10, self.rect.top + 40)
        )
        total_deaths_surf = self.font.render(
            f"Total deaths: {self.dead_npcs_registry.get_total_deaths_amount()}",
            False,
            foreground_color,
        )
        total_deaths_rect = total_deaths_surf.get_frect(
            midleft=(self.rect.left + 10, self.rect.top + 60)
        )

        # display
        pygame.draw.rect(self.display_surface, background_color, self.rect, 0, 4)
        pygame.draw.rect(self.display_surface, foreground_color, self.rect, 4, 4)
        self.display_surface.blit(dead_ingroup_members_surf, dead_ingroup_members_rect)
        self.display_surface.blit(
            dead_outgroup_members_surf, dead_outgroup_members_rect
        )
        self.display_surface.blit(total_deaths_surf, total_deaths_rect)
