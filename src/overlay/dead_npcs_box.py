import pygame

from src.npc.dead_npcs_registry import DeadNpcsRegistry
from src.settings import OVERLAY_POSITIONS
from src.support import get_translated_string, import_font, import_image

BLACK = "Black"
RED = "Red"


class DeadNpcsBox:
    def __init__(self, dead_npcs_registry: DeadNpcsRegistry):
        # setup
        self.display_surface = pygame.display.get_surface()
        self.dead_npcs_registry = dead_npcs_registry
        self.img_size = (15, 20)
        self.image = pygame.transform.scale(
            import_image("images/objects/cross.png"), self.img_size
        )

        # dimensions
        self.left = 20
        self.top = 50

        width, height = 700, 55
        self.font = import_font(20, "font/LycheeSoda.ttf")

        self.rect = pygame.Rect(self.left, self.top, width, height)

        self.rect.topleft = OVERLAY_POSITIONS["dead_npcs_box"]

    def display(self):
        background_color = RED
        foreground_color = BLACK

        # rects and surfs
        dead_ingroup_members_surf = self.font.render(
            f"{get_translated_string('died_in_group_members')} ",
            False,
            foreground_color,
        )
        dead_ingroup_members_rect = dead_ingroup_members_surf.get_frect(
            midleft=(self.rect.left + 10, self.rect.top + 20)
        )
        dead_outgroup_members_surf = self.font.render(
            f"{get_translated_string('died_out_group_members')} ",
            False,
            foreground_color,
        )
        dead_outgroup_members_rect = dead_outgroup_members_surf.get_frect(
            midleft=(self.rect.left + 10, self.rect.top + 40)
        )

        # display
        pygame.draw.rect(self.display_surface, background_color, self.rect, 0, 4)
        pygame.draw.rect(self.display_surface, foreground_color, self.rect, 4, 4)
        self.display_surface.blit(dead_ingroup_members_surf, dead_ingroup_members_rect)
        self.display_surface.blit(
            dead_outgroup_members_surf, dead_outgroup_members_rect
        )
        self.draw_img_surface(
            dead_ingroup_members_rect.topright,
            self.dead_npcs_registry.get_ingroup_deaths_amount(),
        )
        self.draw_img_surface(
            dead_outgroup_members_rect.topright,
            self.dead_npcs_registry.get_outgroup_deaths_amount(),
        )

    def draw_img_surface(self, start_img_topleft, amount):
        pad_x = 5
        blit_list = []
        for i in range(0, amount):
            current_img_topleft = (
                start_img_topleft[0] + i * (self.img_size[0] + pad_x),
                start_img_topleft[1],
            )
            img_rect = pygame.Rect(
                current_img_topleft[0],
                current_img_topleft[1],
                self.img_size[0],
                self.img_size[1],
            )

            blit_list.append((self.image, img_rect))
        self.display_surface.fblits(blit_list)
