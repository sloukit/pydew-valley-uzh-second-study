from abc import ABC, abstractmethod

import pygame

from src import settings
from src.enums import Direction, EntityState, Layer
from src.gui.interface import indicators
from src.settings import SCALED_TILE_SIZE
from src.sprites.base import CollideableSprite, Sprite
from src.sprites.setup import EntityAsset
from src.support import get_entity_facing_direction, screen_to_tile


class Entity(CollideableSprite, ABC):
    frames: dict[str, settings.AniFrames]
    frame_index: int
    _current_ani_frame: list[pygame.Surface] | None

    state: EntityState
    facing_direction: Direction

    direction: pygame.Vector2
    speed: int
    collision_sprites: pygame.sprite.Group

    def __init__(
        self,
        pos: settings.Coordinate,
        assets: EntityAsset,
        groups: tuple[pygame.sprite.Group, ...],
        collision_sprites: pygame.sprite.Group,
        z=Layer.MAIN,
    ):
        self.assets = assets

        self._current_ani = None
        self._current_hitbox = None
        self._current_frame = None

        # Because the following three attributes are properties that depend on
        # each other, the first two of them must be set without calling their
        # property setter
        self._frame_index = 0
        self._facing_direction = Direction.RIGHT
        self.state = EntityState.IDLE

        self.focused = False
        self.focused_indicator = None

        super().__init__(
            pos,
            self.assets[self.state][self.facing_direction].get_frame(0),
            groups,
            z=z,
        )

        # movement
        self.direction = pygame.Vector2()
        self.speed = 100
        self.collision_sprites = collision_sprites
        self.is_colliding = False

        self.last_hitbox_rect = self.hitbox_rect

        # Axe hitbox, which allows for independent usage of the axe by any
        # entity (player or NPC)
        self.axe_hitbox = pygame.Rect(0, 0, 32, 32)

    def _update_axe_hitbox(self):
        match self.facing_direction:
            case Direction.DOWN:
                self.axe_hitbox.x = self.rect.centerx - 24
                self.axe_hitbox.y = self.rect.centery + 24
            case Direction.UP:
                self.axe_hitbox.x = self.rect.centerx - 8
                self.axe_hitbox.bottom = self.rect.centery + 8
            case Direction.LEFT:
                self.axe_hitbox.right = self.rect.centerx - 16
                self.axe_hitbox.y = self.rect.centery + 8
            case Direction.RIGHT:
                self.axe_hitbox.x = self.rect.centerx + 16
                self.axe_hitbox.y = self.rect.centery + 8

    def update_animation(self):
        self._current_ani = self.assets[self.state][self.facing_direction]

    def update_hitbox(self):
        self._current_hitbox = self._current_ani.get_hitbox()

    def update_frame(self):
        self._current_frame = self._current_ani.get_frame(self.frame_index)

    @property
    def state(self):
        return self._state

    @state.setter
    def state(self, state: EntityState):
        self._state = state
        self.update_animation()
        self.update_hitbox()
        self.update_frame()

    @property
    def facing_direction(self):
        return self._facing_direction

    @facing_direction.setter
    def facing_direction(self, direction: Direction):
        self._facing_direction = direction
        self.update_animation()
        self.update_hitbox()
        self.update_frame()

    @property
    def frame_index(self):
        return self._frame_index

    @frame_index.setter
    def frame_index(self, frame_index: int):
        self._frame_index = frame_index
        self.update_frame()

    def get_state(self):
        if self.direction:
            self.state = EntityState.WALK
        else:
            self.state = EntityState.IDLE

    def get_facing_direction(self):
        self.facing_direction = get_entity_facing_direction(
            self.direction, self.facing_direction
        )
        self._update_axe_hitbox()

    def get_target_pos(self):
        return screen_to_tile(self.hitbox_rect.center)

    def get_tile_pos(self) -> tuple[int, int]:
        return (
            int(self.hitbox_rect.centerx / SCALED_TILE_SIZE),
            int(self.hitbox_rect.centery / SCALED_TILE_SIZE),
        )

    def focus(self):
        self.focused = True
        self.focused_indicator = Sprite(
            (0, 0), indicators.ENTITY_FOCUSED, (self.groups()[0],), Layer.EMOTES
        )

    def unfocus(self):
        self.focused = False
        if self.focused_indicator:
            self.focused_indicator.kill()
            self.focused_indicator = None

    def teleport(self, pos: tuple[float, float]):
        """
        Moves the Entity rect directly to the specified point
        """
        self.rect.update(
            (pos[0] - self.rect.width / 2, pos[1] - self.rect.height / 2),
            self.rect.size,
        )

    @staticmethod
    def _interpolated_move(
        hitbox_rect: pygame.Rect,
        movement_x: float,
        movement_y: float,
        collision_check_func,
        max_movement_per_step: float = 8.0,
    ) -> None:
        """
        Move hitbox_rect by the given movement amounts, checking collision at intermediate steps
        if the movement is large. This prevents boundary bypassing during lag spikes.

        Args:
            hitbox_rect: The rect to move
            movement_x: Total x movement for this frame
            movement_y: Total y movement for this frame
            collision_check_func: Function to call for collision checking
            max_movement_per_step: Maximum movement per step before interpolation kicks in
        """
        max_movement = max(abs(movement_x), abs(movement_y))

        if (
            max_movement > max_movement_per_step
        ):  # Checks needed steps if the movement is fast
            steps = int(max_movement / max_movement_per_step) + 1
            step_x = movement_x / steps
            step_y = movement_y / steps

            for _ in range(steps):  # Each step checks for collision
                hitbox_rect.x += step_x
                hitbox_rect.y += step_y
                collision_check_func()
        else:  # if the movement is small enough to do in one step
            hitbox_rect.x += movement_x
            hitbox_rect.y += movement_y
            collision_check_func()

    @abstractmethod
    def move(self, dt: float):
        pass

    def check_collision(self) -> bool:
        """
        :return: true: Entity collides with a sprite in self.collision_sprites,
        otherwise false
        """
        colliding_rect = None

        for sprite in self.collision_sprites:
            if sprite is not self:
                if sprite.hitbox_rect.colliderect(self.hitbox_rect):
                    colliding_rect = sprite.hitbox_rect
                    distances_rect = colliding_rect

                    if isinstance(sprite, Entity):
                        # When colliding with another entity, the hitbox to
                        # compare to will also reflect its last-frame's state
                        distances_rect = sprite.last_hitbox_rect

                    # Compares each point of the last-frame's hitbox to the
                    # hitbox the Entity collided with, to check at which
                    # direction the collision happened first
                    distances = (
                        abs(self.last_hitbox_rect.right - distances_rect.left),
                        abs(self.last_hitbox_rect.left - distances_rect.right),
                        abs(self.last_hitbox_rect.bottom - distances_rect.top),
                        abs(self.last_hitbox_rect.top - distances_rect.bottom),
                    )

                    shortest_distance = min(distances)
                    if shortest_distance == distances[0]:
                        self.hitbox_rect.right = colliding_rect.left
                    elif shortest_distance == distances[1]:
                        self.hitbox_rect.left = colliding_rect.right
                    elif shortest_distance == distances[2]:
                        self.hitbox_rect.bottom = colliding_rect.top
                    elif shortest_distance == distances[3]:
                        self.hitbox_rect.top = colliding_rect.bottom

        self.is_colliding = bool(colliding_rect)

    @abstractmethod
    def animate(self, dt: float):
        """
        Animate the Entity. Child classes should implement method and
        set current image based on self._current_ani_frame
        """
        self.frame_index += 4 * dt

    def _prepare_for_update(self):
        # Updating all attributes necessary for updating the Entity
        self.last_hitbox_rect.update(self.hitbox_rect)
        self.get_state()
        self.get_facing_direction()

    def _do_common_update_ops(self):
        self._prepare_for_update()

        if self.focused_indicator:
            self.focused_indicator.rect.update(
                (
                    self.rect.centerx - self.focused_indicator.rect.width / 2,
                    self.rect.centery - 56 - self.focused_indicator.rect.height / 2,
                ),
                self.focused_indicator.rect.size,
            )

    def update(self, dt: float):
        self._do_common_update_ops()
        self.move(dt)
        self.animate(dt)
        self.image = self._current_frame

    def update_blocked(self, dt):
        """Only used when cutscenes are run, and entities are not meant to move."""
        self._do_common_update_ops()
        self.animate(dt)
        self.image = self._current_frame
