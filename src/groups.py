import pygame

from src.camera import Camera
from src.enums import Layer
from src.fblitter import FBLITTER
from src.settings import (
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
)

_BLUR_FACTOR = 4


class PersistentSpriteGroup(pygame.sprite.Group):
    _persistent_sprites: list[pygame.sprite.Sprite]

    def __init__(self, *sprites) -> None:
        """
        This Group subclass allows certain Sprites to be added as persistent
        Sprites, which will not be removed when calling Group.empty.

        When needing to remove all Sprites, including persistent Sprites, you
        should call PersistentSpriteGroup.empty_persistent.
        """
        super().__init__(*sprites)
        self._persistent_sprites = []

    def add_persistent(self, *sprites: pygame.sprite.Sprite) -> None:
        """
        Add a persistent Sprite. This Sprite will not be removed

        from the Group when Group.empty is called.
        """
        super().add(*sprites)
        self._persistent_sprites.extend(sprites)

    def empty(self) -> None:
        """Empty the Group, but keep persistent Sprites.

        This is useful for clearing the Group while keeping certain Sprites
        """
        super().empty()
        self.add(*self._persistent_sprites)

    def empty_persistent(self) -> None:
        """
        Remove all sprites, including persistent Sprites.
        """
        super().empty()


class AllSprites(PersistentSpriteGroup):
    def __init__(self, *sprites) -> None:
        super().__init__(*sprites)
        self.display_surface = pygame.display.get_surface()
        self.offset = pygame.Vector2()
        self.cam_surf = pygame.Surface(self.display_surface.get_size())

    def update_blocked(self, dt: float) -> None:
        for sprite in self:
            getattr(sprite, "update_blocked", sprite.update)(dt)

    def draw(
        self, camera: Camera, game_paused: bool, has_goggles, is_main_draw=True
    ) -> None:
        sorted_sprites = sorted(self, key=lambda spr: (spr.z, spr.hitbox_rect.bottom))

        # Apply blur effect only if the player has goggles equipped
        # Blur only matters when drawn from main
        if has_goggles and is_main_draw:
            # box blur is too slow, so use smoothscale instead
            surface = pygame.transform.smoothscale(
                pygame.transform.smoothscale(
                    self.display_surface,
                    (SCREEN_WIDTH // _BLUR_FACTOR, SCREEN_HEIGHT // _BLUR_FACTOR),
                ),
                (SCREEN_WIDTH, SCREEN_HEIGHT),
            )
            self.display_surface.blit(surface, (0, 0))
            # FBLITTER.schedule_blit(surface, (0, 0)) # breaks?

        camera_rect = camera.get_viewport_rect()
        for sprite in sorted_sprites:
            # including game_paused condition to prevent drawing overlaps between tutorial text boxes and menus
            # Text boxes are UI elements and should be drawn regardless of camera/world position.
            if not game_paused and sprite.z > 0:
                if sprite.z >= Layer.TEXT_BOX or sprite.hitbox_rect.colliderect(
                    camera_rect
                ):
                    sprite.draw(self.display_surface, camera.apply(sprite), camera)

        FBLITTER.reset_to_default_surf()
        FBLITTER.blit_all()
