import pygame

from src.camera import Camera
from src.fblitter import FBLITTER


class PersistentSpriteGroup(pygame.sprite.Group):
    _persistent_sprites: list[pygame.sprite.Sprite]

    def __init__(self, *sprites):
        """
        This Group subclass allows certain Sprites to be added as persistent
        Sprites, which will not be removed when calling Group.empty.
        When needing to remove all Sprites, including persistent Sprites, you
        should call PersistentSpriteGroup.empty_persistent.
        """
        super().__init__(*sprites)
        self._persistent_sprites = []

    def add_persistent(self, *sprites: pygame.sprite.Sprite):
        """
        Add a persistent Sprite. This Sprite will not be removed
        from the Group when Group.empty is called.
        """
        super().add(*sprites)
        self._persistent_sprites.extend(sprites)

    def empty(self):
        super().empty()
        self.add(*self._persistent_sprites)

    def empty_persistent(self):
        """
        Remove all sprites, including persistent Sprites.
        """
        super().empty()


class AllSprites(PersistentSpriteGroup):
    def __init__(self, *sprites):
        super().__init__(*sprites)
        self.display_surface = pygame.display.get_surface()
        self.offset = pygame.Vector2()
        self.cam_surf = pygame.Surface(self.display_surface.get_size())

    def update_blocked(self, dt: float):
        for sprite in self:
            getattr(sprite, "update_blocked", sprite.update)(dt)

    def draw(self, camera: Camera, game_paused: bool):
        sorted_sprites = sorted(self, key=lambda spr: (spr.z, spr.hitbox_rect.bottom))

        camera_rect = camera.get_viewport_rect()
        for sprite in sorted_sprites:
            # including game_paused condition to prevent drawing overlaps between tutorial text boxes and menus
            if (
                sprite.z > 0
                and not game_paused
                and sprite.hitbox_rect.colliderect(camera_rect)
            ):
                sprite.draw(self.display_surface, camera.apply(sprite), camera)

        FBLITTER.reset_to_default_surf()
        FBLITTER.blit_all()
