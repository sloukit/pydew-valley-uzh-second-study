import gc
import random
import warnings
from collections.abc import Callable
from functools import partial
from typing import Any, cast, Final, Tuple

import pygame

from src.camera import Camera
from src.camera.camera_target import CameraTarget
from src.camera.quaker import Quaker
from src.camera.zoom_manager import ZoomManager
from src.controls import Controls
from src.enums import (
    Direction,
    FarmingTool,
    GameState,
    Layer,
    Map,
    ScriptedSequence,
    StudyGroup,
)
from src.events import (
    DIALOG_ADVANCE,
    DIALOG_SHOW,
    SHOW_BATH_INFO,
    SHOW_BOX_KEYBINDINGS,
    START_QUAKE,
    VOLCANO_ERUPTION,
    post_event,
)
from src.exceptions import GameMapWarning
from src.fblitter import FBLITTER
from src.groups import AllSprites, PersistentSpriteGroup
from src.gui.interface.dialog import DialogueManager
from src.gui.interface.emotes import NPCEmoteManager, PlayerEmoteManager
from src.gui.scene_animation import SceneAnimation
from src.npc.behaviour.context import NPCSharedContext
from src.npc.npc import NPC
from src.npc.setup import AIData
from src.npc_sickness_mgr import NPCSicknessManager
from src.overlay.game_time import GameTime
from src.overlay.overlay import Overlay
from src.overlay.sky import Rain, Sky
from src.overlay.soil import SoilManager
from src.overlay.transition import Transition
from src.savefile import SaveFile
from src.screens.game_map import GameMap
from src.screens.minigames.base import Minigame
from src.screens.minigames.cow_herding import CowHerding, CowHerdingState
from src.settings import (
    DEBUG_MODE_VERSION,
    DEFAULT_ANIMATION_NAME,
    EMOTES_LIST,
    GAME_MAP,
    SCALED_TILE_SIZE,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
    TOMATO_OR_CORN_LIST,
    TOOLS_LOG_INTERVAL,
    VOLCANO_POS,
    MapDict,
    SoundDict,
)
from src.sprites.base import AnimatedSprite, Sprite
from src.sprites.bath_bubble import BubbleMgr
from src.sprites.entities.character import Character
from src.sprites.entities.player import Player
from src.sprites.particle import ParticleSprite
from src.sprites.setup import ENTITY_ASSETS
from src.support import (
    get_translated_string as get_translated_msg,
)
from src.support import (
    load_data,
    map_coords_to_tile,
    resource_path,
    save_data,
)

_TO_PLAYER_SPEED_INCREASE_THRESHOLD: Final[int] = 200
_DECIDE_SEQUENCE: Final[Tuple[ScriptedSequence, ScriptedSequence]] = (
    ScriptedSequence.GROUP_MARKET_PASSIVE,
    ScriptedSequence.GROUP_MARKET_ACTIVE,
)
_RESTRICT_NPC_SEQ: Final[Tuple[ScriptedSequence, ScriptedSequence, ScriptedSequence, ScriptedSequence]] = (
    ScriptedSequence.PLAYER_HAT,
    ScriptedSequence.PLAYER_NECKLACE,
    ScriptedSequence.INGROUP_NECKLACE,
    ScriptedSequence.PLAYER_BIRTHDAY,
)
_YES_OR_NO: Final[Tuple[str, str]] = ("checkmark", "cross")



class Level:
    display_surface: pygame.Surface
    switch_screen: Callable[[GameState], None]

    # assets
    font: pygame.Font
    frames: dict
    sounds: SoundDict
    tmx_maps: MapDict
    current_map: Map | None
    prev_map: Map | None
    game_map: GameMap | None
    save_file: SaveFile

    current_minigame: Minigame | None

    # sprite groups
    all_sprites: AllSprites
    collision_sprites: PersistentSpriteGroup
    tree_sprites: PersistentSpriteGroup
    bush_sprites: PersistentSpriteGroup
    interaction_sprites: PersistentSpriteGroup
    drop_sprites: pygame.sprite.Group
    player_exit_warps: pygame.sprite.Group

    # farming
    soil_manager: SoilManager

    # emotes
    _emotes: dict
    player_emote_manager: PlayerEmoteManager
    backup_emote_mgr: PlayerEmoteManager
    npc_emote_manager: NPCEmoteManager

    player: Player
    prev_player_pos: tuple[int, int]
    # weather
    sky: Sky
    rain: Rain
    raining: bool

    # transitions
    map_transition: Transition
    day_transition: Transition
    current_day: int

    # overlay
    overlay: Overlay
    show_hitbox_active: bool

    intro_shown: dict[str, bool]

    # current game version config
    round_config: dict[str, Any]
    get_game_version: Callable[[], int]

    def __init__(
        self,
        switch: Callable[[GameState], None],
        get_set_round: tuple[Callable[[], int], Callable[[int], None]],
        get_rnd_timer: Callable[[], float],
        round_config: dict[str, Any],
        get_game_version: Callable[[], int],
        tmx_maps: MapDict,
        frames: dict[str, dict],
        sounds: SoundDict,
        save_file: SaveFile,
        clock: pygame.time.Clock,
        get_world_time: Callable[[], tuple[int, int]],
        dialogue_manager: DialogueManager,
        send_telemetry: Callable[[str, dict[str, Any]], None],
        npc_mgr: NPCSicknessManager,
    ) -> None:
        # main setup
        self.display_surface = pygame.display.get_surface()
        self.switch_screen = switch
        self.save_file = save_file
        self.dialogue_manager = dialogue_manager
        self.send_telemetry = send_telemetry
        self.npc_mgr = npc_mgr

        # cutscene
        # target_points = [(100, 100), (200, 200), (300, 100), (800, 900)]
        # speeds = [100, 150, 200]  # Different speeds for each segment
        # pauses = [0, 1, 0.5, 2]  # Pauses at each point in seconds
        self.cutscene_animation = SceneAnimation([CameraTarget.get_null_target()])
        self.intro_shown = {}

        self.zoom_manager = ZoomManager()

        # assets
        self.font = pygame.font.Font(resource_path("font/LycheeSoda.ttf"), 30)
        self.frames = frames
        self.sounds = sounds
        self.tmx_maps = tmx_maps
        self.current_map = None
        self.prev_map = None
        self.game_map = None

        self.all_sprites = AllSprites()
        self.collision_sprites = PersistentSpriteGroup()
        self.tree_sprites = PersistentSpriteGroup()
        self.bush_sprites = PersistentSpriteGroup()
        self.interaction_sprites = PersistentSpriteGroup()
        self.drop_sprites = pygame.sprite.Group()
        self.player_exit_warps = pygame.sprite.Group()

        self.camera = Camera(0, 0)
        self.quaker = Quaker(self.camera)
        BubbleMgr.set_bathbubble_surf(frames["level"]["objects"]["bubble"])
        self.bubble_mgr = BubbleMgr()
        self.tool_statistics = {t.name: 0 for t in FarmingTool}

        self.soil_manager = SoilManager(self.all_sprites, self.frames["level"])

        self._emotes = self.frames["emotes"]
        # add additional sprites for scripted sequence "decide_tomato_or_corn"
        # extra sprites are fine, which sprites are actually shown on the wheel depends on emote_list param
        for frame in TOMATO_OR_CORN_LIST:
            self._emotes[frame] = [self.frames["items"][frame]]

        self.player_emote_manager = PlayerEmoteManager(
            self._emotes, EMOTES_LIST, self.all_sprites
        )
        self.backup_emote_mgr = self.player_emote_manager
        self.npc_emote_manager = NPCEmoteManager(self._emotes, self.all_sprites)

        self.controls = Controls

        # level interactions
        self.get_round = get_set_round[0]
        self.set_round = get_set_round[1]
        self.get_rnd_timer = get_rnd_timer
        self.round_config = round_config
        self.get_game_version = get_game_version

        self.player = Player(
            pos=(0, 0),
            assets=ENTITY_ASSETS.RABBIT,
            groups=(),
            collision_sprites=self.collision_sprites,
            controls=self.controls,
            apply_tool=self.apply_tool,
            plant_collision=self.plant_collision,
            interact=self.interact,
            emote_manager=self.player_emote_manager,
            sounds=self.sounds,
            save_file=self.save_file,
            round_config=self.round_config,
            get_game_version=get_game_version,
            send_telemetry=self.send_telemetry,
        )
        self.prev_player_pos = (0, 0)
        self.all_sprites.add_persistent(self.player)
        self.collision_sprites.add_persistent(self.player)

        # weather
        self.game_time = GameTime()
        self.sky = Sky(self.game_time)
        self.rain = Rain(self.all_sprites, self.frames["level"])
        self.raining = False

        self.activate_music()

        # day night cycle
        self.day_transition = Transition(self.reset, self.finish_transition, dur=3200)
        self.current_day = 0

        # overlays
        self.overlay = Overlay(
            self.player,
            frames["items"],
            self.game_time,
            get_world_time,
            clock,
            round_config,
            self.npc_mgr,
        )
        self.show_hitbox_active = False
        self.show_pf_overlay = False
        self.setup_pf_overlay()

        # minigame
        self.current_minigame = None
        self.cow_herding_count = 0

        # switch to outgroup farm
        self.outgroup_farm_entered = False
        self.outgroup_farm_time_entered = None
        self.outgroup_message_received = False
        self.start_become_outgroup = False
        self.start_become_outgroup_time = None
        self.finish_become_outgroup = False

        # map
        self.load_map(GAME_MAP)
        self.map_transition = Transition(
            lambda: self.switch_to_map(self.current_map),
            self.finish_transition,
            dur=2400,
        )

        # Volcano
        self.volcano_erupt_once = False
        self.volcano_event = False
        self.volcano_map_transition = Transition(
            lambda: self.switch_to_map(Map.VOLCANO),
            self.create_volcano,
            dur=2400,
        )
        volcano_image = self.frames["level"]["animations"]["volcano_exploding_new"]
        self.volcano_sprite = AnimatedSprite(
            VOLCANO_POS, volcano_image, z=Layer.VOLCANO
        )
        self.start_volcano_animation = False
        self.volcano_sounds = [
            self.sounds["mixkit-inside-a-volcano-2438"],
            self.sounds["mixkit-volcano-lava-hiss-2447"],
        ]
        self.volcano_erupt_count = 0
        self.sound_no = 0

        # watch the player behaviour in achieving tutorial tasks
        self.tile_farmed = False
        self.crop_planted = False
        self.crop_watered = False
        self.had_slept = False
        self.hit_tree = False

    def hide_bath_signs(self) -> None:
        if not self.round_config.get("bathtub_signs", False):
            gr = self.collision_sprites
            for sprite in gr:
                if sprite.name == "hidden_sign":
                    gr.remove(sprite)
                    sprite.kill()

    def hide_goggles_signs(self):
        if not self.round_config.get("goggles_signs", False):
            for spr in self.collision_sprites:
                if spr.name == "goggles_sign":
                    self.collision_sprites.remove(spr)
                    spr.kill()

    def round_config_changed(self, round_config: dict[str, Any]) -> None:
        self.round_config = round_config
        self.hide_bath_signs()
        self.hide_goggles_signs()
        self.player.round_config_changed(round_config)
        self.overlay.round_config = round_config
        self.overlay.is_debug_mode_version = (
            self.get_game_version() == DEBUG_MODE_VERSION
        )
        self.game_map.round_config_changed(round_config)

    def load_map(self, game_map: Map, from_map: str = None):
        # prepare level state for new map
        # clear all sprite groups
        self.all_sprites.empty()
        self.collision_sprites.empty()
        self.interaction_sprites.empty()
        self.tree_sprites.empty()
        self.bush_sprites.empty()
        self.player_exit_warps.empty()

        # clear existing soil_layer (not done due to the fact we need to keep hoed tiles in memory)
        # self.soil_layer.reset()
        self.quaker.reset()

        # manual memory cleaning
        gc.collect()

        self.game_map = GameMap(
            selected_map=game_map,
            tilemap=self.tmx_maps[game_map],
            scene_ani=self.cutscene_animation,
            zoom_man=self.zoom_manager,
            all_sprites=self.all_sprites,
            collision_sprites=self.collision_sprites,
            interaction_sprites=self.interaction_sprites,
            tree_sprites=self.tree_sprites,
            bush_sprites=self.bush_sprites,
            player_exit_warps=self.player_exit_warps,
            player=self.player,
            player_emote_manager=self.player_emote_manager,
            npc_emote_manager=self.npc_emote_manager,
            soil_manager=self.soil_manager,
            apply_tool=self.apply_tool,
            plant_collision=self.plant_collision,
            frames=self.frames,
            save_file=self.save_file,
            round_config=self.round_config,
            get_game_version=self.get_game_version,
            reference_npc_in_mgr=self.npc_mgr.add_npc,
            disable_minigame=self.can_disable_minigame,
            round_no=self.get_round(),
        )

        self.camera.change_size(*self.game_map.size)

        player_spawn = None

        # search for player entry warp depending on which map they came from
        if from_map and not game_map == Map.MINIGAME:
            player_spawn = self.game_map.player_entry_warps.get(from_map)
            if not player_spawn and (
                self.current_map != Map.VOLCANO and self.prev_map != Map.VOLCANO
            ):
                warnings.warn(
                    f'No valid entry warp found for "{game_map}" '
                    f'from: "{self.current_map}"',
                    GameMapWarning,
                )
        # jump to default spawn point (set to market place) when during decision tomato or corn scripted sequence
        if self.prev_map and self.prev_map == game_map:
            player_spawn = self.prev_player_pos
            self.prev_map = None
        # use default spawnpoint if no origin map is specified,
        # or if no entry warp for the player's origin map is found
        if not player_spawn:
            if self.game_map.player_spawnpoint:
                player_spawn = self.game_map.player_spawnpoint
            else:
                warnings.warn(
                    f"No default spawnpoint found on {game_map}", GameMapWarning
                )
                # fallback to the first player entry warp
                player_spawn = next(iter(self.game_map.player_entry_warps.values()))

        self.player.teleport(player_spawn)

        if self.cutscene_animation.has_animation_name(DEFAULT_ANIMATION_NAME):
            def_animation_targets = self.cutscene_animation.animations[
                DEFAULT_ANIMATION_NAME
            ]
            last_target = def_animation_targets[-1]
            last_targ_pos = pygame.Vector2(last_target.pos)
            center = pygame.Vector2(self.player.rect.center)
            movement = center - last_targ_pos
            speed = (
                max(round(movement.length()) // _TO_PLAYER_SPEED_INCREASE_THRESHOLD, 2)
                * 100
            )
            def_animation_targets.append(
                CameraTarget(self.player.rect.center, len(def_animation_targets), speed)
            )

            self.cutscene_animation.set_current_animation(DEFAULT_ANIMATION_NAME)

            # Starting intro animation for Volcano map in level 7
            if self.current_map == Map.VOLCANO:
                self.cutscene_animation.start()

        self.rain.set_floor_size(self.game_map.get_size())

        self.current_map = game_map
        NPCSharedContext.current_map = game_map

        if game_map == Map.MINIGAME:
            self.current_minigame = CowHerding(
                CowHerdingState(
                    game_map=self.game_map,
                    player=self.player,
                    all_sprites=self.all_sprites,
                    collision_sprites=self.collision_sprites,
                    overlay=self.overlay,
                    sounds=self.sounds,
                ),
                round_config=self.round_config,
            )

            @self.current_minigame.on_finish
            def on_finish():
                self.current_minigame = None
                self.map_transition.reset = partial(self.switch_to_map, Map.TOWN)
                self.start_map_transition()

            self.current_minigame.start()

    def activate_music(self):
        volume = 0.1
        try:
            sound_data = load_data("volume.json")
        except FileNotFoundError:
            sound_data = {
                "music": 50,
                "sfx": 50,
            }
            save_data(sound_data, "volume.json")
        volume = sound_data["music"]
        # sfx = sound_data['sfx']
        self.sounds["music"].set_volume(min((volume / 1000), 0.4))
        self.sounds["music"].play(-1)

    # plant collision
    def plant_collision(self, character: Character):
        area = self.soil_manager.get_area(character.study_group)
        if area.plant_sprites:
            for plant in area.plant_sprites:
                if plant.hitbox_rect.colliderect(character.hitbox_rect):
                    x, y = map_coords_to_tile(plant.hitbox_rect.midbottom)
                    area.harvest((x, y), character.add_resource, self.create_particle)

    def warp_to_map(self, map_name: str):
        if map_name == "bathhouse":
            if not (self.player.is_bath_sick or self.player.is_sick):
                self.player.get_bath_sick(self.get_rnd_timer())
                self.send_telemetry("bath_taken", {"has_effect": True})
            else:
                self.send_telemetry("bath_taken", {"has_effect": False})
            self.bubble_mgr.start()
        if map_name == "minigame":
            self.cow_herding_count += 1
        self.switch_to_map(map_name)

    @property
    def can_disable_minigame(self):
        return self.get_round() > 6 or self.cow_herding_count > 4

    def switch_to_map(self, map_name: Map):
        if self.tmx_maps.get(map_name):
            self.send_telemetry(
                "switch_map",
                {"old_map": str(self.current_map), "new_map": str(map_name)},
            )
            self.load_map(map_name, from_map=self.current_map)
            self.hide_bath_signs()
            self.hide_goggles_signs()
            self.game_map.process_npc_round_config()

        else:
            if map_name == "bathhouse":
                if self.round_config["accessible_bathhouse"]:
                    # self.player.emote_manager.show_emote(self.player, "sad_sick_ani")
                    self.load_map(self.current_map, from_map=map_name)
            else:
                warnings.warn(f'Error loading map: Map "{map_name}" not found')

                # fallback which reloads the current map and sets the player to the
                # entry warp of the map that should have been switched to
                self.load_map(self.current_map, from_map=map_name)

    def create_particle(self, sprite: pygame.sprite.Sprite):
        ParticleSprite(sprite.rect.topleft, sprite.image, self.all_sprites)

    def _play_playeronly_sound(self, sound: str, entity: Character):
        if isinstance(entity, Player):
            self.sounds[sound].play()

    def apply_tool(self, tool: FarmingTool, pos: tuple[int, int], character: Character):
        tool_use_for_statistics = None
        match tool:
            case FarmingTool.AXE:
                for tree in pygame.sprite.spritecollide(
                    character,
                    self.tree_sprites,
                    False,
                    lambda spr, tree_spr: spr.axe_hitbox.colliderect(
                        tree_spr.hitbox_rect
                    ),
                ):
                    tree.hit(character)

                    # check if player achieved task "go to the forest and hit a tree"
                    if isinstance(character, Player):
                        self.hit_tree = True
                        tool_use_for_statistics = tool.name

                    self._play_playeronly_sound("axe", character)
            case FarmingTool.HOE:
                if self.soil_manager.hoe(character, pos):
                    self._play_playeronly_sound("hoe", character)

                    # check if the player achieved task "farm with your hoe"
                    if isinstance(character, Player):
                        self.tile_farmed = True
                        tool_use_for_statistics = tool.name
            case FarmingTool.WATERING_CAN:
                if self.soil_manager.water(character, pos):
                    # check if the player achieved task "water the crop"
                    if isinstance(character, Player):
                        tool_use_for_statistics = tool.name
                        if self.crop_planted:
                            self.crop_watered = True

                self._play_playeronly_sound("water", character)
            case _:  # All seeds
                if self.soil_manager.plant(
                    character, pos, tool, character.remove_resource
                ):
                    self._play_playeronly_sound("plant", character)

                    # check if the player achieved task "plant a crop"
                    if isinstance(character, Player):
                        self.crop_planted = True
                        tool_use_for_statistics = tool.name
                else:
                    self._play_playeronly_sound("cant_plant", character)

        if tool_use_for_statistics is not None:
            self.tool_statistics[tool_use_for_statistics] += 1
            if sum(self.tool_statistics.values()) % TOOLS_LOG_INTERVAL == 0:
                self.send_telemetry("tool_statistics", self.tool_statistics)

    def interact(self):
        collided_interactions = pygame.sprite.spritecollide(
            self.player, self.interaction_sprites, False
        )
        if collided_interactions:
            if collided_interactions[0].name == "Bed":
                self.send_telemetry("going_to_bed", {})
                self.start_day_transition()
            if (
                collided_interactions[0].name == "sign"
                and self.round_config["sign_interaction"]
            ):
                self.show_sign(collided_interactions[0])
            if (
                collided_interactions[0].name == "Trader"
                and self.round_config["market"]
                and not self.player.blocked_from_market
            ):
                self.send_telemetry("marketer_start", {})
                self.switch_screen(GameState.SHOP)
            if collided_interactions[0] in self.bush_sprites.sprites():
                if self.player.axe_hitbox.colliderect(
                    collided_interactions[0].hitbox_rect
                ):
                    collided_interactions[0].hit(self.player)

    def show_sign(self, sign: Sprite) -> None:
        label_key = sign.custom_properties.get("label", "label_not_available")
        post_event(DIALOG_SHOW, dial=label_key)

    def check_outgroup_logic(self) -> None:
        if not self.round_config.get("playable_outgroup", False):
            return

        collided_with_outgroup_farm = pygame.sprite.spritecollide(
            self.player,
            [i for i in self.interaction_sprites if i.name == "Outgroup Farm"],
            False,
        )

        # Starts timer for 60 seconds when player is in outgroup farm
        if collided_with_outgroup_farm:
            if not self.outgroup_farm_entered:
                self.outgroup_farm_time_entered = pygame.time.get_ticks()
                self.outgroup_farm_entered = True

        # Resets the timer when player exits the farm
        else:
            self.outgroup_farm_entered = False
            self.outgroup_farm_time_entered = None
            self.outgroup_message_received = False

        # If the player is in the farm and 60 seconds (currently 15s) have passed
        if (
            self.outgroup_farm_entered
            and pygame.time.get_ticks() - self.outgroup_farm_time_entered >= 15000
        ):
            # Checks if player has already received the message and is not part of the outgroup
            if (
                not self.outgroup_message_received
                and self.player.study_group != StudyGroup.OUTGROUP
            ):
                self.outgroup_message_received = True
                self.switch_screen(GameState.OUTGROUP_MENU)

        # Resets so that message can be displayed again if player exits and reenters farm
        if not self.outgroup_farm_entered:
            self.outgroup_message_received = False

        # checks 60 seconds and 120 seconds after player joins outgroup to convert appearance
        if self.player.study_group == StudyGroup.OUTGROUP:
            # The player immediately loses the necklace.
            delta_time = pygame.time.get_ticks() - (
                self.start_become_outgroup_time or 0
            )
            if not self.start_become_outgroup:
                self.start_become_outgroup_time = pygame.time.get_ticks()
                self.start_become_outgroup = True
                self.player.has_necklace = False

            elif self.finish_become_outgroup:
                pass
            # after 22.5 seconds, the player gets the horn
            elif delta_time > 22500:
                self.player.has_horn = True
                self.finish_become_outgroup = True
            # after 15 seconds player gets the same color as outgroup
            elif 15000 < delta_time < 22500:
                self.player.image_alpha = 255
            # after 7.5 seconds, the player loses the hat, fade in outgroup body
            elif 7500 < delta_time < 15000:
                self.player.has_hat = False
                self.player.has_outgroup_skin = True
                self.player.image_alpha = 35 + 220 * ((delta_time - 7500) / 7500)
            # during first minute fade out ingroup body
            elif delta_time < 7500:
                self.player.image_alpha = 35 + 220 * (1 - delta_time / 7500)

    def handle_event(self, event: pygame.event.Event) -> bool:
        if self.current_minigame and self.current_minigame.running:
            if self.current_minigame.handle_event(event):
                return True

        if event.type == START_QUAKE:
            self.quaker.start(event.duration)
            if event.debug:
                self.set_round(7)
            return True

        elif event.type == VOLCANO_ERUPTION:
            self.volcano(True)

        elif event.type == SHOW_BATH_INFO:
            if __debug__:
                print(
                    f"SHOW_BATH_INFO event received: enabled={self.overlay.bath_info.enabled}, visible={self.overlay.bath_info.visible}"
                )
            self.overlay.bath_info.toggle_visibility()

        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.switch_screen(GameState.PAUSE)
                return True
            self.controls.update_control_state(event.key, True)
        elif event.type == pygame.KEYUP:
            self.controls.update_control_state(event.key, False)
        elif event.type == pygame.MOUSEBUTTONDOWN:
            self.controls.update_control_state(event.button, True)
        elif event.type == pygame.MOUSEBUTTONUP:
            self.controls.update_control_state(event.button, False)

        return False

    def handle_controls(self):
        if self.controls.ADVANCE_DIALOG.click:
            post_event(DIALOG_ADVANCE)

        if self.controls.SHOW_BOX_KEYBINDINGS.click:
            post_event(SHOW_BOX_KEYBINDINGS)

        # TODO: move this back into the debug controls if check once testing is done
        if self.controls.DEBUG_END_ROUND.click:
            self.switch_screen(GameState.ROUND_END)

        # Bath info display available in all game modes (not just debug)
        if self.controls.SHOW_BATH_INFO.click:
            if __debug__:
                print(
                    f"B key pressed: bath_info enabled={self.overlay.bath_info.enabled}"
                )
            post_event(SHOW_BATH_INFO)

        if self.get_game_version() == DEBUG_MODE_VERSION:
            # if self.controls.DEBUG_QUAKE.click:
            #     post_event(START_QUAKE, duration=2.0, debug=True)
            if self.controls.DEBUG_VOLCANO.click:
                post_event(VOLCANO_ERUPTION)

            if self.controls.DEBUG_APPLY_HEALTH.click:
                self.overlay.health_bar.apply_health(1)

            if self.controls.DEBUG_APPLY_DAMAGE.click:
                self.overlay.health_bar.apply_damage(1)

            if self.controls.DEBUG_SELF_ASSESSMENT.click:
                self.switch_screen(GameState.SELF_ASSESSMENT)

            if self.controls.DEBUG_SOCIAL_IDENTITY_ASSESSMENT.click:
                self.switch_screen(GameState.SOCIAL_IDENTITY_ASSESSMENT)

            if self.controls.DEBUG_NOTIFICATION_MENU.click:
                self.switch_screen(GameState.NOTIFICATION_MENU)

            if self.controls.DEBUG_PLAYER_RECEIVES_HAT.click:
                self.start_scripted_sequence(ScriptedSequence.PLAYER_HAT)

            if self.controls.DEBUG_PLAYER_RECEIVES_NECKLACE.click:
                self.start_scripted_sequence(ScriptedSequence.PLAYER_NECKLACE)

            if self.controls.DEBUG_PLAYERS_BIRTHDAY.click:
                self.start_scripted_sequence(ScriptedSequence.PLAYER_BIRTHDAY)

            if self.controls.DEBUG_NPC_RECEIVES_NECKLACE.click:
                self.start_scripted_sequence(ScriptedSequence.INGROUP_NECKLACE)

            if self.controls.DEBUG_PASSIVE_DECIDE_TOMATO_OR_CORN.click:
                self.start_scripted_sequence(ScriptedSequence.GROUP_MARKET_PASSIVE)

            if self.controls.DEBUG_ACTIVE_DECIDE_TOMATO_OR_CORN.click:
                self.start_scripted_sequence(ScriptedSequence.GROUP_MARKET_ACTIVE)

            if self.controls.DEBUG_SHOW_HITBOXES.click:
                self.show_hitbox_active = not self.show_hitbox_active

            if self.controls.DEBUG_SHOW_PF_OVERLAY.click:
                self.show_pf_overlay = not self.show_pf_overlay

            if self.controls.DEBUG_SHOW_DIALOG.click:
                post_event(DIALOG_SHOW, dial="test", is_gvt=True)

            if self.controls.DEBUG_SHOW_SHOP.click:
                self.switch_screen(GameState.SHOP)

    def set_dialogue_from_round_config(self, sequence_type: ScriptedSequence) -> None:
        dialogue_key = f"scripted_sequence_{sequence_type.value}"
        config_key = f"{sequence_type.value}_text"
        new_text = get_translated_msg(self.round_config[config_key])
        self.dialogue_manager.dialogues[dialogue_key][0][1] = new_text

    def start_scripted_sequence(self, sequence_type: ScriptedSequence):
        # do not start new scripted sequence when one is already running
        if self.cutscene_animation.active:
            return

        # scripted sequence dialog text is set from `round_config.json` (derived from `game_levels_3b.xlsx`)
        self.set_dialogue_from_round_config(sequence_type)

        active_group = self.player.study_group
        if active_group == StudyGroup.INGROUP:
            animation_name = "ingroup_gathering"
        else:
            animation_name = "outgroup_gathering"

        if sequence_type in _DECIDE_SEQUENCE:
            if not self.current_map == Map.TOWN and not self.map_transition:
                self.prev_player_pos = cast(tuple[int, int], self.player.rect.center)
                self.prev_map = self.current_map
                self.map_transition.reset = partial(self.switch_to_map, Map.TOWN)
                self.start_map_transition()

        # if switching to TOWN map for a prompt scripted sequence - quit until transition ends
        if not self.map_transition.peaked:
            return

        if self.cutscene_animation.has_animation_name(animation_name):
            npcs: list[Player | NPC] = []
            if self.game_map:
                npcs = [
                    npc
                    for npc in self.game_map.npcs
                    if npc.study_group == active_group and not npc.is_dead
                ]
                # Leave only 4 NPCs and the player
                if sequence_type in _RESTRICT_NPC_SEQ:
                    npcs = self.limit_npcs_amount(npcs)
                if sequence_type in _DECIDE_SEQUENCE:
                    for npc in npcs:
                        npc.has_hat = True
                        npc.has_necklace = True

                other_npcs = [
                    npc
                    for npc in self.game_map.npcs
                    if npc.study_group != active_group and not npc.is_dead
                ]
            if sequence_type == ScriptedSequence.INGROUP_NECKLACE:
                npc_in_center = random.choice(npcs)
                npcs.remove(npc_in_center)
                npcs.append(self.player)
            else:
                npc_in_center = self.player

            self.cutscene_animation.set_current_animation(animation_name)
            self.cutscene_animation.is_end_condition_met = partial(
                self.end_scripted_sequence, sequence_type, npc_in_center
            )

            if sequence_type not in _DECIDE_SEQUENCE or not self.prev_map:
                self.prev_player_pos = cast(
                    tuple[int, int], self.player.rect.center
                )  # else (0, 0)

            meeting_pos = self.cutscene_animation.targets[0].pos
            if sequence_type in _DECIDE_SEQUENCE:
                # find position on map to teleport npc's from study group other then player's
                # (located in a clear field, in the upper part of the TOWN map)
                outgroup_hide_pos = self.cutscene_animation.animations[
                    "outgroup_gathering"
                ][0].pos
            # move player other npc_in_center to the meeting point and make him face to the east (right)
            npc_in_center.teleport(meeting_pos)
            # npc_in_center.direction = pygame.Vector2(1, 0)
            if active_group == StudyGroup.INGROUP:
                npc_in_center.direction.update((1, 0))
            else:
                npc_in_center.direction.update((-1, 0))
            npc_in_center.get_facing_direction()
            npc_in_center.direction.update((0, 0))

            # spread all ingroup npc in half-circle of 2 * SCALED_TILE_SIZE diameter
            # from north to south clockwise or counterclockwise (depends on group)
            # and make them face the player in the center
            if len(npcs) > 0:
                distance = pygame.Vector2(0, -2 * SCALED_TILE_SIZE)
                if len(npcs) == 1:
                    rot_by = 0.0
                    angle = -90.0
                else:
                    rot_by = (180) / (len(npcs) - 1)
                    angle = 0.0
                # the outgroup circle is laid out counterclockwise
                if active_group == StudyGroup.OUTGROUP:
                    rot_by = -rot_by

                for npc in npcs:
                    new_pos = meeting_pos + distance.rotate(angle)
                    npc.direction.update(-distance.rotate(angle))
                    npc.get_facing_direction()
                    npc.direction.update((0, 0))

                    npc.teleport(new_pos)
                    angle += rot_by

            # teleport npc's from study group other than player's to the upper part of the TOWN map,
            # so they don't interrupt in the meeting by the market
            if sequence_type in _DECIDE_SEQUENCE and other_npcs:
                distance = pygame.Vector2(0, -2 * SCALED_TILE_SIZE)
                angle = 0.0
                rot_by = 180 / (len(other_npcs) - 1)
                for npc in other_npcs:
                    new_pos = outgroup_hide_pos + distance.rotate(angle)
                    npc.teleport(new_pos)
                    angle += rot_by

            self.cutscene_animation.reset()
            self.cutscene_animation.start()

            dialog_name = f"scripted_sequence_{sequence_type.value}"
            post_event(DIALOG_SHOW, dial=dialog_name)

    def limit_npcs_amount(self, npcs):
        counter: int = 0
        restricted_npcs = []
        for npc in npcs:
            if counter >= len(npcs) or counter == 4:
                break
            restricted_npcs.append(npc)
            counter += 1
        return restricted_npcs

    def end_scripted_sequence(
        self, sequence_type: ScriptedSequence, npc: NPC | Player
    ) -> bool:
        # prevent the scripted sequence from ending
        if self.player.blocked:
            return False

        if sequence_type == ScriptedSequence.PLAYER_HAT:
            npc.has_hat = True
            self.player.blocked_from_market = False
        elif sequence_type == ScriptedSequence.PLAYER_NECKLACE:
            npc.has_necklace = True
        elif sequence_type == ScriptedSequence.PLAYER_BIRTHDAY:
            pass
        elif sequence_type == ScriptedSequence.INGROUP_NECKLACE:
            npc.has_hat = True
            npc.has_necklace = True
        elif sequence_type == ScriptedSequence.GROUP_MARKET_PASSIVE:
            buy_list = TOMATO_OR_CORN_LIST
            self.end_scripted_sequence_decide(buy_list, is_player_active=False)
            return False
        elif sequence_type == ScriptedSequence.GROUP_MARKET_ACTIVE:
            buy_list = TOMATO_OR_CORN_LIST if self.get_round() < 7 else _YES_OR_NO
            self.end_scripted_sequence_decide(buy_list, is_player_active=True)
            return False

        self.scripted_sequence_cleanup()

        return True

    def end_scripted_sequence_decide(
        self, buy_list: list[str], is_player_active: bool
    ) -> None:
        # just to make linter happy (game_map could be None)
        if not self.game_map:
            return

        # do not proceed with the scripted sequence if the dialog is still opened
        if self.dialogue_manager.showing_dialogue:
            return

        if buy_list[0] not in self.player_emote_manager.emote_wheel._emotes:
            # check if emote was already displayed
            # store current EmoteManager
            self.backup_emote_mgr = self.player.emote_manager
            # create and assign new EmoteManager with only 2 options to select from
            self.player_emote_manager = PlayerEmoteManager(
                self._emotes, buy_list, self.all_sprites
            )
            self.player.emote_manager = self.player_emote_manager
            self.game_map.player_emote_manager = self.player_emote_manager
            self.game_map._setup_emote_interactions()
            # show EmoteWheel
            # self.player.blocked = True
            if is_player_active:
                self.player_emote_manager.toggle_emote_wheel()
            # still block the Scripted Sequence from finishing, until user makes selection
        else:
            if self.player_emote_manager.emote_wheel.visible:
                # EmoteWheel is still displayed, waiting for his vote
                return
            else:
                # Player has voted or is passive
                if is_player_active:
                    # self.player.blocked = False
                    total_votes = 1
                    # how many Characters voted for the first option
                    first_item_votes = 0
                    players_vote = self.player_emote_manager.emote_wheel._current_emote
                    if players_vote == buy_list[0]:
                        first_item_votes += 1

                    payload = {}
                    payload["emote_index"] = (
                        self.player_emote_manager.emote_wheel.emote_index
                    )
                    payload["winner_item"] = (
                        self.player_emote_manager.emote_wheel._emotes[
                            payload["emote_index"]
                        ]
                    )
                    self.send_telemetry("players_decision", payload)
                else:
                    total_votes = 0
                    first_item_votes = 0

                for npc in self.game_map.npcs:
                    if npc.study_group == self.player.study_group and not npc.is_dead:
                        # each NPC needs to vote
                        total_votes += 1
                        buy_item = random.choice(buy_list)
                        if buy_item == buy_list[0]:
                            first_item_votes += 1
                        npc.emote_manager.show_emote(npc, buy_item)
                # check which option has the majority of votes
                # in case of draw, Player vote decides
                if first_item_votes == total_votes / 2:
                    total_votes += 1
                    if is_player_active and players_vote == buy_list[0]:
                        first_item_votes += 1

                winner_item = (
                    buy_list[0] if first_item_votes > total_votes / 2 else buy_list[1]
                )
                if not is_player_active:
                    payload = {}
                    payload["winner_item"] = winner_item
                    self.send_telemetry("groups_decision", payload)

                # restore backup EmoteManager
                self.player_emote_manager = self.backup_emote_mgr
                self.player.emote_manager = self.player_emote_manager
                self.game_map.player_emote_manager = self.player_emote_manager
                self.game_map._setup_emote_interactions()

                # immediately switch to a new dialog with vote results
                dialog_name = f"scripted_sequence_buy_{winner_item}"
                post_event(DIALOG_SHOW, dial=dialog_name)
                # start ending Scripted Sequence with a new end condition
                if self.player.study_group == StudyGroup.INGROUP:
                    animation_name = "ingroup_gathering_end"
                else:
                    animation_name = "outgroup_gathering_end"

                self.cutscene_animation.set_current_animation(animation_name)
                self.cutscene_animation.is_end_condition_met = (
                    self.end_scripted_sequence_decision_result
                )
                self.cutscene_animation.reset()
                self.cutscene_animation.start()

    def end_scripted_sequence_decision_result(self) -> bool:
        # prevent the scripted sequence from ending
        # while dialog is still opened
        if self.player.blocked:
            return False

        self.scripted_sequence_cleanup()

        return True

    def scripted_sequence_cleanup(self):
        # go back to previous map if it wasn't TOWN
        if not self.prev_map == Map.TOWN and self.prev_map:
            self.map_transition.reset = partial(self.switch_to_map, Map(self.prev_map))
            self.start_map_transition()
        else:
            self.player.teleport(self.prev_player_pos)
        self.cutscene_animation.set_current_animation(DEFAULT_ANIMATION_NAME)
        self.cutscene_animation.is_end_condition_met = lambda: True

    def get_camera_pos(self):
        return self.camera.state.topleft

    def start_transition(self):
        self.player.blocked = True
        self.player.direction = pygame.Vector2(0, 0)

    def finish_transition(self):
        self.player.blocked = False
        self.had_slept = True
        if self.prev_map == Map.VOLCANO:
            self.start_volcano_animation = False
            self.volcano_erupt_once = True
            self.prev_map = None

    def start_day_transition(self):
        self.day_transition.activate()
        self.start_transition()

    def start_volcano_map_transition(self):
        self.volcano_map_transition.reset = partial(self.switch_to_map, Map.VOLCANO)
        self.volcano_map_transition.activate()
        self.start_transition()

    # Creating Volcano on volcano map
    def create_volcano(self):
        # self.cutscene_animation.start()
        Sprite(
            VOLCANO_POS,
            self.frames["level"]["animations"]["volcano"][0],
            z=Layer.VOLCANO,
        ).add(self.all_sprites)
        self.volcano_animation()

    def volcano_animation(self):
        # Stopping the game music and playing the volcano eruption sound
        self.sounds["music"].stop()
        pygame.mixer.init(44100, -16, 2, 262144)

        if not pygame.mixer.get_busy() and self.volcano_erupt_count <= 5:
            self.start_volcano_animation = True

            self.quaker.reset()
            self.quaker.start(10000)

            if self.sound_no == 1 and not self.volcano_sprite.alive():
                self.volcano_sprite.add(self.all_sprites)
                self.quaker.reset()
                self.quaker.direction = Direction.UPLEFT
                self.quaker.start(1000)
            else:
                self.volcano_sprite.kill()

            self.volcano_sounds[self.sound_no].set_volume(0.7)
            self.volcano_sounds[self.sound_no].play()

            self.volcano_erupt_count += 1
            self.sound_no += 1

            if self.sound_no > 1:
                self.sound_no = 0

        elif not pygame.mixer.get_busy():
            # Killing the volcano sprite and reseting the quaker
            self.volcano_sprite.kill()
            # self.start_volcano_animation = False
            self.quaker.reset()
            self.volcano_erupt_count = 0
            self.sound_no = 0

            self.activate_music()  # Activating the old music

            if self.volcano_event:
                self.intro_shown.pop(Map.VOLCANO)
            self.current_map = self.prev_map
            self.prev_map = Map.VOLCANO
            self.map_transition.reset = partial(self.switch_to_map, self.current_map)
            self.start_map_transition()

    def volcano(self, event=None):
        if (self.get_round() == 7) and (
            self.get_rnd_timer() >= 30 and not self.volcano_erupt_once
        ):
            self.volcano_erupt_once = True
            if not self.start_volcano_animation:
                self.prev_map = (
                    self.game_map.current_map
                )  # Storing the current map so that player can return
                self.current_map = Map.VOLCANO
                self.start_volcano_map_transition()
                prev_time = self.game_time.get_time()
                self.game_time.set_time(prev_time[0], prev_time[1] + 1)
        elif event and not self.cutscene_animation.active:
            if not self.start_volcano_animation:
                self.volcano_event = event
                self.prev_map = (
                    self.game_map.current_map
                )  # Storing the current map so that player can return
                self.current_map = Map.VOLCANO
            self.start_volcano_map_transition()

    # reset
    def reset(self):
        self.current_day += 1

        # plants + soil
        if self.current_map == Map.NEW_FARM:
            self.soil_manager.update()

        self.raining = random.randint(0, 10) > 7
        self.soil_manager.raining = self.raining

        # apples on the trees

        # No need to iterate using explicit sprites() call.
        # Iterating over a sprite group normally will do the same thing
        for tree in self.tree_sprites:
            for fruit in tree.fruit_sprites:
                fruit.kill()
            if tree.alive:
                tree.create_fruit()
        for bush in self.bush_sprites:
            for fruit in bush.fruit_sprites:
                fruit.kill()
                bush.create_fruit()

        # sky
        self.sky.start_color = [255, 255, 255]
        self.game_time.set_time(6, 0)  # set to 0600 hours upon sleeping

    def start_map_transition(self):
        self.map_transition.activate()
        self.start_transition()

    def check_map_exit(self):
        if not self.map_transition:
            for warp_hitbox in self.player_exit_warps:
                if self.player.hitbox_rect.colliderect(warp_hitbox.rect) and (
                    warp_hitbox.name != "bathhouse"
                    or self.round_config["accessible_bathhouse"]
                ):
                    if (
                        __debug__
                    ):  # Only print debug information if running in debug mode
                        print(f"Player hit warp: {warp_hitbox.name}")

                    self.map_transition.reset = partial(
                        self.warp_to_map, warp_hitbox.name
                    )
                    self.start_map_transition()
                    return

    # draw
    # region debug-overlays
    def draw_hitboxes(self):
        if self.show_hitbox_active:
            offset = pygame.Vector2(self.get_camera_pos())

            for sprite in self.collision_sprites:
                rect = sprite.rect.copy()
                rect.topleft += offset
                FBLITTER.draw_rect("red", rect, 2)
                # pygame.draw.rect(self.display_surface, "red", rect, 2)

                hitbox = sprite.hitbox_rect.copy()
                hitbox.topleft += offset
                FBLITTER.draw_rect("blue", hitbox, 2)
                # pygame.draw.rect(self.display_surface, "blue", hitbox, 2)

                if isinstance(sprite, Character):
                    hitbox = sprite.axe_hitbox.copy()
                    hitbox.topleft += offset
                    FBLITTER.draw_rect("green", hitbox, 2)
                    # pygame.draw.rect(self.display_surface, "green", hitbox, 2)
            for drop in self.drop_sprites:
                FBLITTER.draw_rect("red", drop.rect.move(offset), 2)
                FBLITTER.draw_rect("blue", drop.hitbox_rect.move(offset), 2)
                # pygame.draw.rect(
                #     self.display_surface, "red", drop.rect.move(offset), 2
                # )
                # pygame.draw.rect(
                #     self.display_surface, "blue", drop.hitbox_rect.move(*offset), 2
                # )

    def setup_pf_overlay(self):
        self.pf_overlay_non_walkable = pygame.Surface(
            (SCALED_TILE_SIZE, SCALED_TILE_SIZE), pygame.SRCALPHA
        )
        self.pf_overlay_non_walkable.fill((255, 128, 128))
        pygame.draw.rect(
            self.pf_overlay_non_walkable,
            (0, 0, 0),
            (0, 0, SCALED_TILE_SIZE, SCALED_TILE_SIZE),
            2,
        )
        self.pf_overlay_non_walkable.set_alpha(92)

    def draw_pf_overlay(self):
        if self.show_pf_overlay:
            offset = pygame.Vector2(self.get_camera_pos())

            if AIData.setup:
                for y in range(len(AIData.Matrix)):
                    for x in range(len(AIData.Matrix[y])):
                        if not AIData.Matrix[y][x]:
                            self.display_surface.blit(
                                self.pf_overlay_non_walkable,
                                (
                                    x * SCALED_TILE_SIZE + offset.x,
                                    y * SCALED_TILE_SIZE + offset.y,
                                ),
                            )

            for npe in self.game_map.animals + self.game_map.npcs:
                if npe.pf_path:
                    offset = pygame.Vector2(0, 0)
                    offset.x = -(self.player.rect.centerx - SCREEN_WIDTH / 2)
                    offset.y = -(self.player.rect.centery - SCREEN_HEIGHT / 2)
                    for i in range(len(npe.pf_path)):
                        start_pos = (
                            (npe.pf_path[i][0]) * SCALED_TILE_SIZE + offset.x,
                            (npe.pf_path[i][1]) * SCALED_TILE_SIZE + offset.y,
                        )
                        if i == 0:
                            end_pos = (
                                npe.hitbox_rect.centerx + offset.x,
                                npe.hitbox_rect.centery + offset.y,
                            )
                        else:
                            end_pos = (
                                (npe.pf_path[i - 1][0]) * SCALED_TILE_SIZE + offset.x,
                                (npe.pf_path[i - 1][1]) * SCALED_TILE_SIZE + offset.y,
                            )
                        FBLITTER.draw_aaline((0, 0, 0), start_pos, end_pos)

    # endregion

    def draw_overlay(self):
        self.sky.display(self.get_round(), self.get_rnd_timer())
        # The volcano erupts in round 7, so round 8+ is post-volcano
        post_volcano = self.volcano_erupt_once or self.get_round() >= 8
        self.overlay.display(self.get_round(), post_volcano)

    def draw(self, dt: float, move_things: bool):
        # self.display_surface.fill((130, 168, 132))
        self.all_sprites.draw(self.camera, False, self.player.has_goggles)

        self.draw_pf_overlay()
        self.draw_hitboxes()

        self.zoom_manager.apply_zoom()
        if move_things:
            self.sky.display(self.get_round(), self.get_rnd_timer())

        self.draw_overlay()

        if self.current_minigame and self.current_minigame.running:
            self.current_minigame.draw()

        # transitions
        self.day_transition.draw()
        self.map_transition.draw()
        self.volcano_map_transition.draw()

    # update
    def update_rain(self):
        if self.raining:
            self.rain.update()

    def update_cutscene(self, dt):
        if self.cutscene_animation.active:
            self.cutscene_animation.update(dt)

    def update(self, dt: float, move_things: bool = True):
        # update
        if self.map_transition:
            if not self.bubble_mgr.active:
                self.map_transition.update()
            self.game_time.last_time = pygame.time.get_ticks()

            if self.cutscene_animation.active:
                target = self.cutscene_animation
            elif (
                isinstance(self.current_minigame, CowHerding)
                and self.current_minigame.running
            ):
                target = self.current_minigame.camera_target
            else:
                target = self.player

            self.camera.update(target)

            self.draw(dt, move_things)
            if self.bubble_mgr.active:
                self.bubble_mgr.update(dt)
                self.bubble_mgr.draw()
                if self.bubble_mgr.finished:
                    map_timer = self.map_transition.timer
                    map_timer.start_time = pygame.time.get_ticks()
                    map_timer.now = pygame.time.get_ticks()
            return

        self.handle_controls()

        self.game_time.update()
        self.check_map_exit()
        if move_things:
            # Don't check the outgroup logic if anything ends up interrupting (e.g. goggles notification).
            self.check_outgroup_logic()
        elif self.outgroup_farm_time_entered is not None:
            # If there IS an interruption and the player actually IS in the farm, just reset the timer instead.
            self.outgroup_farm_time_entered = pygame.time.get_ticks()

        # show intro scripted sequence only once
        if not self.intro_shown.get(self.current_map, False):
            if len(self.round_config.get("character_introduction_timestamp", [])) > 0:
                self.intro_shown[self.current_map] = True
                self.cutscene_animation.start()

        if self.current_minigame and self.current_minigame.running:
            self.current_minigame.update(dt)

        self.volcano()
        if self.start_volcano_animation:
            self.volcano_animation()

        self.update_rain()
        self.day_transition.update()
        self.volcano_map_transition.update()
        self.map_transition.update()
        if move_things:
            if self.cutscene_animation.active:
                self.all_sprites.update_blocked(dt)
            else:
                self.all_sprites.update(dt)
            self.update_cutscene(dt)
            self.quaker.update_quake(dt)

            if self.cutscene_animation.active:
                target = self.cutscene_animation
            elif (
                isinstance(self.current_minigame, CowHerding)
                and self.current_minigame.running
            ):
                target = self.current_minigame.camera_target
            else:
                target = self.player

            self.camera.update(target)

            self.zoom_manager.update(
                (
                    self.cutscene_animation
                    if self.cutscene_animation.active
                    else self.player
                ),
                dt,
            )

        self.draw(dt, move_things)

        for control in self.controls:
            control.click = False
