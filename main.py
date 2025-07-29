# /// script
# dependencies = [
#  "pygame-ce",
#  "pytmx",
#  "pathfinding",
#  "pygbag",
# ]
# ///

import asyncio
import copy
import gc
import random
import sys
from datetime import datetime, timezone
from functools import partial
from typing import Any

import pygame

import src.utils  # noqa [ to patch utf-8 on top of file without linting errors ]
from src import client, support, xplat
from src.enums import (
    CustomCursor,
    GameState,
    Map,
    ScriptedSequence,
    SelfAssessmentDimension,
    SocialIdentityAssessmentDimension,
)
from src.events import (
    DIALOG_ADVANCE,
    DIALOG_SHOW,
    OPEN_INVENTORY,
    SET_CURSOR,
    SHOW_BATH_INFO,
    SHOW_BOX_KEYBINDINGS,
)
from src.exceptions import TooEarlyLoginError
from src.fblitter import FBLITTER
from src.groups import AllSprites
from src.gui.interface.dialog import DialogueManager
from src.gui.setup import setup_gui
from src.npc.behaviour.context import NPCSharedContext
from src.npc.npc import NPC
from src.npc.npcs_state_registry import NPC_STATE_REGISTRY_UPDATE_EVENT
from src.npc_sickness_mgr import NPCSicknessManager
from src.overlay.fast_forward import FastForward
from src.savefile import SaveFile
from src.screens.inventory import InventoryMenu, prepare_checkmark_for_buttons
from src.screens.level import Level
from src.screens.menu_main import MainMenu
from src.screens.menu_notification import NotificationMenu
from src.screens.menu_pause import PauseMenu
from src.screens.menu_round_end import RoundMenu
from src.screens.menu_settings import SettingsMenu
from src.screens.player_task import PlayerTask
from src.screens.self_assessment_menu import SelfAssessmentMenu
from src.screens.shop import ShopMenu
from src.screens.social_identity_assessment import SocialIdentityAssessmentMenu
from src.screens.switch_to_outgroup_menu import OutgroupMenu
from src.settings import (
    DEBUG_MODE_VERSION,
    EMOTE_SIZE,
    GAME_LANGUAGE,
    GVT_TB_SIZE,
    RANDOM_SEED,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
    TB_SIZE,
    TUTORIAL_TB_LEFT,
    TUTORIAL_TB_TOP,
    USE_SERVER,
    WORLD_TIME_MULTIPLIER,
    AniFrames,
    MapDict,
    SoundDict,
    # SERVER_URL,
)
from src.sickness import SicknessManager
from src.sprites.setup import setup_entity_assets
from src.support import get_translated_string as get_translated_msg
from src.tutorial import Tutorial

# memory cleaning settings
print(f"gc.get_threshold: {gc.get_threshold()}")

print("setting new threshold:")
allocs, g1, g2 = gc.get_threshold()
# gc.set_threshold(50000, g1, g2)
print(f"gc.get_threshold: {gc.get_threshold()}")


# set random seed. It has to be set first before any other random function is called.
random.seed(RANDOM_SEED)
_COSMETICS = frozenset({"goggles", "horn", "necklace", "hat"})
# Due to the unconventional sizes of the cosmetics' icons, different scale factors are needed
_COSMETIC_SCALE_FACTORS = {"goggles": 2, "horn": 4, "necklace": 2, "hat": 3}
_COSMETIC_SUBSURF_AREAS = {
    "goggles": pygame.Rect(0, 0, 27, 16),
    "horn": pygame.Rect(32, 0, 16, 16),
    "necklace": pygame.Rect(0, 16, 21, 22),
    "hat": pygame.Rect(24, 16, 20, 11),
}
_CAMERA_TARGET_TO_TEXT = (
    "character_introduction_text",
    "ingroup_introduction_text",
    "ingroup_hat_necklace_introduction_text",
    "ingroup_hat_introduction_text",
    "outgroup_introduction_text",
    "narrative_text",
)
_CAMERA_TARGET_TO_TEXT_SOLO = (
    "character_introduction_text",
    "ingroup_introduction_text",
    "outgroup_introduction_text",
    "narrative_text",
)
_TARG_SKIP_IDX_SOLO = _CAMERA_TARGET_TO_TEXT_SOLO.index("outgroup_introduction_text")
_GOGGLES_TUT_TSTAMP = 35
_ENABLE_SICKNESS_TSTAMP = 33
_ENABLE_BATH_INFO_TSTAMP = 30  # 30 seconds after volcano eruption
_BLUR_FACTOR = 1


def _get_alloc_text(alloc_id: str):
    potential_alloc_ids = alloc_id.split(";")
    if len(potential_alloc_ids) > 1:
        if GAME_LANGUAGE == "de":
            txt_to_add = get_translated_msg(potential_alloc_ids[1])
        elif potential_alloc_ids[0].startswith("weather_protection"):
            params = potential_alloc_ids[0][
                potential_alloc_ids[0].find("(") : -1
            ].split(",")
            txt_to_add = get_translated_msg("weather_protection").format(
                item=get_translated_msg(params[0]),
                weather=get_translated_msg(params[1]),
            )
        else:
            txt_to_add = get_translated_msg(potential_alloc_ids[0])
    else:
        txt_to_add = get_translated_msg(potential_alloc_ids[0])
    return txt_to_add


def _get_outgroup_income(money: str, in_outgrp: bool = False):
    actual_money = money
    if GAME_LANGUAGE == "en":
        # English currency formatting works like the German one, but with commas instead of colons.
        actual_money = money.replace(".", ",")
    return get_translated_msg(
        f"{'in' if in_outgrp else 'out'}group_income_round_end"
    ).format(money=actual_money)


class Game:
    def __init__(self) -> None:
        # main setup
        pygame.init()

        program_icon = pygame.image.load(
            support.resource_path("images/objects/rabbit.png")
        )
        pygame.display.set_icon(program_icon)

        screen_size = (SCREEN_WIDTH, SCREEN_HEIGHT)
        self.display_surface = pygame.display.set_mode(screen_size)
        pygame.display.set_caption(get_translated_msg("game_title"))

        # frames
        self.level_frames: dict | None = None
        self.item_frames: dict[str, pygame.Surface] | None = None
        self.cosmetic_frames: dict[str, pygame.Surface] = {}
        self.frames: dict[str, dict] | None = None
        self.previous_frame = ""
        self.fast_forward = FastForward()
        # assets
        self.tmx_maps: MapDict | None = None

        self.emotes: AniFrames | None = None

        self.font: pygame.font.Font | None = None
        self.sounds: SoundDict | None = None

        self._available_cursors: list[pygame.Surface] = []
        self._cursor: int = CustomCursor.ARROW
        self._cursor_img: pygame.Surface | None = None

        self.save_file = SaveFile.load()
        # self.save_file.is_tutorial_completed = True

        # main setup
        self.running = True
        self.clock = pygame.time.Clock()
        self.load_assets()

        # config of all game versions and all rounds: rounds_config[game_version][round_no][feature_name] = value
        self.rounds_config: list[list[dict[str, Any]]] = support.load_data(
            "rounds_config.json"
        )
        # config of current game version of a current round: round_config[feature_name] = value
        self.round_config: dict[str, Any] = {}
        # copy first config (for round 1) and use it as a base for the debug version (all features enabled)
        debug_config = copy.deepcopy(self.rounds_config[0])

        for level in debug_config:
            for key, value in level.items():
                # turn on all feature flags
                if type(value) is bool:
                    level[key] = True
        # add debug config to the start of list (DEBUG_MODE_VERSION == 0)

        self.rounds_config.insert(DEBUG_MODE_VERSION, debug_config)

        self.get_round = lambda: self.round
        self.game_version: int = -1
        self.round: int = -1
        # JWT token to use to interact with backend, and send telemetry
        self.jwt: str = ""
        self.round_end_timer: float = 0.0
        self.ROUND_END_TIME_IN_MINUTES: float = 99999999.0
        self.get_rnd_timer = lambda: self.round_end_timer

        # dialog
        self.all_sprites = AllSprites()
        self.dialogue_manager = DialogueManager(
            self.all_sprites, f"data/textboxes/{GAME_LANGUAGE}/dialogues.json"
        )

        self.npc_sickness_mgr = NPCSicknessManager(
            self.get_round, self.get_rnd_timer, self.send_telemetry, False
        )

        # screens
        self.level = Level(
            self.switch_state,
            (self.get_round, self.set_round),
            self.get_rnd_timer,
            self.round_config,
            lambda: self.game_version,
            self.tmx_maps,
            self.frames,
            self.sounds,
            self.save_file,
            self.clock,
            self.get_world_time,
            self.dialogue_manager,
            self.send_telemetry,
            self.add_npc_to_mgr,
        )
        self.player = self.level.player

        # Sickness management
        self.took_bath = False
        self.goggles_delta = 0.0
        NPCSharedContext.get_rnd_timer = self.get_rnd_timer
        NPCSharedContext.get_round = self.get_round
        self.sickness_man = SicknessManager(
            self.get_round,
            self.get_rnd_timer,
            lambda: self.goggles_delta >= 240,
            lambda: self.took_bath,
            lambda: self.player.is_sick,
            self.send_telemetry,
            self.player.get_sick,
            self.player.recover,
            self._reset_goggles_timer,
        )

        self.tutorial = None
        self.inventory_menu = None
        self.shop_menu = None
        self.settings_menu = None
        self.round_menu = None
        self.token_status = False
        self.allocation_task = PlayerTask(
            partial(self.send_telemetry_and_play, "resource_allocation")
        )
        self.main_menu = MainMenu(
            self.switch_state,
            self.set_token,
            self.set_players_name,
        )
        self.pause_menu = PauseMenu(self.switch_state)
        self.settings_menu = SettingsMenu(
            self.switch_state,
            self.sounds,
            self.player.controls,
            lambda: self.game_version,
        )
        self.shop_menu = ShopMenu(
            self.player,
            self.switch_state,
            self.font,
            self.round_config,
            self.frames,
        )
        self.inventory_menu = InventoryMenu(
            self.player,
            self.frames,
            self.switch_state,
            self.player.assign_tool,
            self.player.assign_seed,
            self.round_config,
            partial(self.send_telemetry_and_play, "goggle_status_change"),
        )
        self.round_menu = RoundMenu(
            self.switch_state,
            self.player,
            self.increment_round,
            self.get_round,
            self.round_config,
            self.frames,
            partial(self.send_telemetry, "round_end_content"),
        )
        self.outgroup_menu = OutgroupMenu(
            self.player,
            self.switch_state,
            partial(self.send_telemetry_and_play, "outgroup_switch", {}),
        )

        self.self_assessment_menu = SelfAssessmentMenu(
            partial(self.send_telemetry_and_play, "self_assessment"),
            (
                SelfAssessmentDimension.VALENCE,
                SelfAssessmentDimension.AROUSAL,
                SelfAssessmentDimension.DOMINANCE,
            ),
        )

        self.social_identity_assessment_menu = SocialIdentityAssessmentMenu(
            partial(self.send_telemetry_and_play, "social_identity_assessment"),
            (
                SocialIdentityAssessmentDimension.INGROUP,
                SocialIdentityAssessmentDimension.OUTGROUP,
                SocialIdentityAssessmentDimension.MIKA,
            ),
            self.player,
        )

        self.notification_menu = NotificationMenu(
            self.switch_state,
            "This is a very long Test Message with German characters: üß",
        )

        # dialogue text box positions
        self.msg_left = SCREEN_WIDTH / 2 - TB_SIZE[0] / 2
        self.msg_top = SCREEN_HEIGHT - TB_SIZE[1]
        self.gvt_msg_left = SCREEN_WIDTH / 2 - GVT_TB_SIZE[0] / 2
        self.gvt_msg_top = SCREEN_HEIGHT - GVT_TB_SIZE[1]

        # screens
        self.menus = {
            GameState.MAIN_MENU: self.main_menu,
            GameState.PAUSE: self.pause_menu,
            GameState.SETTINGS: self.settings_menu,
            GameState.SHOP: self.shop_menu,
            GameState.INVENTORY: self.inventory_menu,
            GameState.PLAYER_TASK: self.allocation_task,
            GameState.ROUND_END: self.round_menu,
            GameState.OUTGROUP_MENU: self.outgroup_menu,
            GameState.SELF_ASSESSMENT: self.self_assessment_menu,
            GameState.SOCIAL_IDENTITY_ASSESSMENT: self.social_identity_assessment_menu,
            GameState.NOTIFICATION_MENU: self.notification_menu,
        }
        self.current_state = GameState.MAIN_MENU

        # tutorial
        self.tutorial = Tutorial(
            self.all_sprites, self.player, self.level, self.round_config
        )
        self._has_displayed_initial_gov_statement = False

        # intro to game and in-group msg.
        self.last_intro_txt_rendered = False
        self.switched_to_tutorial = False

    def _reset_goggles_timer(self):
        self.goggles_delta = 0.0

    def add_npc_to_mgr(self, npc_id: int, npc: NPC):
        self.npc_sickness_mgr.add_npc(npc_id, npc)

    def _empty_round_config_notify(self, cfg_id: str):
        self.round_config[f"notify_{cfg_id}_text"] = ""
        tstamp = f"notify_{cfg_id}_timestamp"
        if tstamp in self.round_config:
            self.round_config[tstamp] = []

    # region Notification and event checks
    @property
    def _can_notify_new_crop(self):
        return (
            self.round_config.get("notify_new_crop_text", "")
            and self.round_config["notify_new_crop_timestamp"]
            and self.round_end_timer > self.round_config["notify_new_crop_timestamp"][0]
        )

    @property
    def _can_notify_questionnaire(self):
        return (
            self.round_config.get("notify_questionnaire_text", "")
            and self.round_config["notify_questionnaire_timestamp"]
            and self.round_end_timer
            > self.round_config["notify_questionnaire_timestamp"][0]
        )

    @property
    def _can_notify_outgroup_money_income(self):
        return (
            self.round_config.get("notify_round_end_outgroup_text", "")
            and self.round_config["notify_round_end_outgroup_timestamp"]
            and self.round_end_timer
            > self.round_config["notify_round_end_outgroup_timestamp"][0]
        )

    @property
    def _can_notify_government(self):
        return (
            self.round_config.get("notify_gov_statement_text", "")
            and self.round_config["notify_gov_statement_timestamp"]
            and self.round_end_timer
            > self.round_config["notify_gov_statement_timestamp"][0]
        )

    @property
    def _can_start_self_assessment_sequence(self):
        return (
            len(self.round_config.get("self_assessment_timestamp", [])) > 0
            and self.round_end_timer > self.round_config["self_assessment_timestamp"][0]
        )

    @property
    def _can_start_social_assessment_seq(self):
        return (
            len(self.round_config.get("social_identity_assessment_timestamp", [])) > 0
            and self.round_end_timer
            > self.round_config["social_identity_assessment_timestamp"][0]
        )

    @property
    def _can_start_hat_sequence(self):
        return (
            len(self.round_config.get("player_hat_sequence_timestamp", [])) > 0
            and self.round_end_timer
            > self.round_config["player_hat_sequence_timestamp"][0]
        )

    @property
    def _can_start_npc_necklace_sequence(self):
        return (
            len(self.round_config.get("ingroup_necklace_sequence_timestamp", [])) > 0
            and self.round_end_timer
            > self.round_config["ingroup_necklace_sequence_timestamp"][0]
        )

    @property
    def _can_start_necklace_sequence(self):
        return (
            len(self.round_config.get("player_necklace_sequence_timestamp", [])) > 0
            and self.round_end_timer
            > self.round_config["player_necklace_sequence_timestamp"][0]
        )

    @property
    def _can_start_birthday_sequence(self):
        return (
            len(self.round_config.get("player_birthday_sequence_timestamp", [])) > 0
            and self.round_end_timer
            > self.round_config["player_birthday_sequence_timestamp"][0]
        )

    @property
    def _can_start_market_inactive_seq(self):
        return (
            len(
                self.round_config.get(
                    "group_market_passive_player_sequence_timestamp", []
                )
            )
            > 0
            and self.round_end_timer
            > self.round_config["group_market_passive_player_sequence_timestamp"][0]
        )

    @property
    def _can_start_active_market_seq(self):
        return (
            len(
                self.round_config.get(
                    "group_market_active_player_sequence_timestamp", []
                )
            )
            > 0
            and self.round_end_timer
            > self.round_config["group_market_active_player_sequence_timestamp"][0]
        )

    @property
    def _can_prompt_allocation(self):
        return (
            self.round_config.get("resource_allocation_text", "")
            and self.round_config["resource_allocation_timestamp"]
            and self.round_end_timer
            > self.round_config["resource_allocation_timestamp"][0]
        )

    @property
    def _can_notify_initial_gov_statement(self):
        return (
            self.round == 7
            and not self._has_displayed_initial_gov_statement
            and self.round_end_timer > _GOGGLES_TUT_TSTAMP
        )

    # endregion

    def _notify(self, message: str, id_to_empty: str):
        self.notification_menu.set_message(message)
        self.switch_state(GameState.NOTIFICATION_MENU)
        # set to empty to not repeat
        self._empty_round_config_notify(id_to_empty)

    def check_hat_condition(self):
        if self.round > 2 and 0 < self.game_version < 3:
            self.player.has_hat = True

    def get_world_time(self) -> tuple[int, int]:
        min = round(self.round_end_timer) // 60
        sec = round(self.round_end_timer) % 60
        return (min, sec)

    def send_telemetry(self, event: str, payload: dict[str, int]) -> None:
        if event == "bath_taken":
            self.took_bath = True
        if USE_SERVER:
            telemetry = {
                "event": event,
                "payload": payload,
                "game_version": self.game_version,
                "game_round": self.round,
                "round_timer": round(self.round_end_timer, 2),
            }
            client.send_telemetry(self.jwt, telemetry)

    def send_telemetry_and_play(self, event: str, payload: dict[str, int]) -> None:
        self.send_telemetry(event, payload)

        self.switch_state(GameState.PLAY)

    def set_players_name(self, players_name: str) -> None:
        self.player.name = players_name
        if players_name:
            self.send_telemetry("players_name", {"players_name": players_name})

    def set_token(self, response: dict[str, Any]) -> dict[str, Any]:
        xplat.log("Login successful!")
        xplat.log(f"Response content: {response}")
        # `token` is the play token the player entered
        self.token = response["token"]
        # `jwt` is the creds used to send telemetry to the backend
        self.jwt = response["jwt"]
        # `game_version` is stored in the player database
        self.game_version = response["game_version"]
        xplat.log(f"token: {self.token}")
        xplat.log(f"jwt: {self.jwt}")

        if not USE_SERVER:  # offline dev / debug version
            xplat.log("Not using server!")
            # token 100-379 triggers game version 1,
            # token 380-659 triggers game version 2,
            # token 660-939 triggers game version 3
            # token 0 triggers game in debug mode (all features enabled)
            # last digit determines adherence of ingroup: 0 is non-adherence, >0 is adherence
            try:
                token_int = int(self.token)
            except ValueError:
                raise ValueError("Invalid token value") from None
            if 100 <= token_int < 380:
                self.game_version = 1
            elif 380 <= token_int < 660:
                self.game_version = 2
            elif 660 <= token_int < 940:
                self.game_version = 3
            elif not token_int:
                self.game_version = DEBUG_MODE_VERSION
            else:
                raise ValueError("Invalid token value")

            self.npc_sickness_mgr.adherence = bool(token_int % 10)
            xplat.log(f"NPC adherence is set to {bool(token_int % 10)}")
            self.npc_sickness_mgr._setup_from_returned_data(
                {"data": None}
            )  # workaround fake npc server response
            self.set_round(7)
            self.check_hat_condition()
        else:  # online deployed version with db access
            # here we check whether a person is allowed to login, bec they need to stay away for 12 hours
            day_completions = []
            max_complete_level = 0
            self.npc_sickness_mgr.adherence = response["adherence"]
            if response["status"]:  # has at least 1 completed level
                day_completions = [
                    d for d in response["status"] if d["game_round"] % 2 == 0
                ]  # these are day task completions
                max_complete_level = max(d["game_round"] for d in response["status"])
                xplat.log("Max completed level so far: {}".format(max_complete_level))
                if max_complete_level >= 12:
                    raise ValueError(
                        "All levels are already completed for this player token."
                    )

            else:
                xplat.log("First login ever with this token, start level 1!")

            # this supposedly loads npc status (e.g., previous deaths etc.) but seems to be untested / not implemented server side?
            self.npc_sickness_mgr.get_status_from_server(self.jwt)

            # max_complete_level = 6
            if len(day_completions) > 0:
                timestamps = [
                    datetime.fromisoformat(d["timestamp"]) for d in day_completions
                ]
                most_recent_completion = max(timestamps)
                current_time = datetime.now(timezone.utc)
                if max_complete_level > 12:
                    self.level.npcs_state_registry.restore_registry(
                        dict(
                            filter(
                                lambda d: d["timestamp"] == most_recent_completion,
                                day_completions,
                            )
                        )[NPC_STATE_REGISTRY_UPDATE_EVENT]
                    )

                # Check if the newest timestamp is more than 12 hours ago
                time_difference = (
                    current_time - most_recent_completion
                ).total_seconds() / 3600
                if time_difference <= 12:
                    raise TooEarlyLoginError(
                        "Last daily task completion is less than 12 hours ago."
                    )
                else:
                    xplat.log(
                        f"Login successful: Time since last level completion: {time_difference:.2f} hours"
                    )
            self.set_round(max_complete_level + 1)
            self.check_hat_condition()  # in levels above 2, the player should wear a hat unless it's version 3

        xplat.log(f"Game version {self.game_version}")
        self.send_telemetry("player_login", {"token": self.token})

        return self.round_config

    def set_round(self, round_no: int) -> None:
        self.round = round_no
        self.took_bath = False
        self.goggles_delta = 0.0
        self.level.cow_herding_count = 0
        # if config for given round number not found, use first one as fall back
        if self.game_version < 0:
            self.game_version = DEBUG_MODE_VERSION

        if self.round > 7:
            self.level.npcs_state_registry.enable()

        # round end menu needs to get config from previous round,
        # since when this menu is activated it's already new round
        if self.round_menu:
            self.round_menu.round_config_changed(self.round_config)

        if round_no <= len(self.rounds_config[self.game_version]):
            self.round_config = self.rounds_config[self.game_version][round_no - 1]
        else:
            print(
                f"ERROR: No config found for round {round_no}! Using config for round 1."
            )
            self.round_config = self.rounds_config[self.game_version][0]
        self.level.round_config_changed(self.round_config)
        if self.inventory_menu:
            self.inventory_menu.round_config_changed(self.round_config)
        if self.tutorial:
            self.tutorial.round_config = self.round_config
            self.tutorial.set_game_version(
                self.game_version
            )  # needed for player market blocker
            if self.round > 1:
                self.tutorial.deactivate()
        if self.shop_menu:
            self.shop_menu.round_config_changed(self.round_config)
        if self.settings_menu:
            self.settings_menu.round_config_changed(self.round_config)

        self.round_end_timer = 0.0
        self.ROUND_END_TIME_IN_MINUTES = self.round_config["level_duration"] / 60  # 15
        print(self.round_config["level_name_text"])

    def increment_round(self) -> None:
        if self.round < 13:
            self.set_round(self.round + 1)
            print("incremented round to {}".format(self.round))

    def switch_state(self, state: GameState) -> None:
        self.set_cursor(CustomCursor.ARROW)
        self.current_state = state
        if self.current_state == GameState.SAVE_AND_RESUME:
            self.save_file.set_soil_data(*self.level.soil_manager.all_soil_sprites())
            self.level.player.save()
            self.current_state = GameState.PLAY
        if self.current_state == GameState.INVENTORY:
            self.inventory_menu.refresh_buttons_content()
        if self.current_state == GameState.ROUND_END:
            self.round_menu.reset_menu()
        if self.game_paused():
            self.player.blocked = True
            self.player.direction.update((0, 0))
        else:
            self.player.blocked = False

    def set_cursor(self, cursor: CustomCursor, override: bool = False) -> None:
        if self._cursor != cursor:
            # ensure the cursor does not get switched back to CustomCursor.POINT during
            # click animation
            if (
                self._cursor != CustomCursor.CLICK
                or cursor != CustomCursor.POINT
                or override
            ):
                self._cursor = cursor
                self._cursor_img = self._available_cursors[self._cursor]

    def load_assets(self) -> None:
        self.tmx_maps = support.tmx_importer("data/maps")

        # frames
        self.emotes = support.animation_importer(
            "images/ui/emotes/sprout_lands", frame_size=EMOTE_SIZE, resize=EMOTE_SIZE
        )

        self.level_frames = {
            "animations": support.animation_importer("images", "misc"),
            "soil": support.import_folder_dict("images/tilesets/soil"),
            "soil water": support.import_folder_dict("images/tilesets/soil/soil water"),
            "tomato": support.import_folder("images/tilesets/plants/tomato"),
            "corn": support.import_folder("images/tilesets/plants/corn"),
            "beetroot": support.import_folder("images/tilesets/plants/beetroot"),
            "carrot": support.import_folder("images/tilesets/plants/carrot"),
            "eggplant": support.import_folder("images/tilesets/plants/eggplant"),
            "pumpkin": support.import_folder("images/tilesets/plants/pumpkin"),
            "parsnip": support.import_folder("images/tilesets/plants/parsnip"),
            "cabbage": support.import_folder("images/tilesets/plants/cabbage"),
            "bean": support.import_folder("images/tilesets/plants/bean"),
            "cauliflower": support.import_folder("images/tilesets/plants/cauliflower"),
            "red_cabbage": support.import_folder("images/tilesets/plants/red_cabbage"),
            "wheat": support.import_folder("images/tilesets/plants/wheat"),
            "broccoli": support.import_folder("images/tilesets/plants/broccoli"),
            "rain drops": support.import_folder("images/rain/drops"),
            "rain floor": support.import_folder("images/rain/floor"),
            "objects": support.import_folder_dict("images/objects"),
            "drops": support.import_folder_dict("images/drops"),
        }
        self.item_frames = support.import_folder_dict("images/objects/items")
        cosmetic_surf = pygame.image.load(
            support.resource_path("images/ui/cosmetics.png")
        ).convert_alpha()
        for cosmetic in _COSMETICS:
            self.cosmetic_frames[cosmetic] = pygame.transform.scale_by(
                cosmetic_surf.subsurface(_COSMETIC_SUBSURF_AREAS[cosmetic]),
                _COSMETIC_SCALE_FACTORS[cosmetic],
            )
        self.frames = {
            "emotes": self.emotes,
            "level": self.level_frames,
            "items": self.item_frames,
            "cosmetics": self.cosmetic_frames,
            "checkmark": pygame.transform.scale_by(
                pygame.image.load(
                    support.resource_path("images/ui/checkmark.png")
                ).convert_alpha(),
                4,
            ),
            "cross": pygame.transform.scale_by(
                pygame.image.load(
                    support.resource_path("images/ui/cross.png")
                ).convert_alpha(),
                4,
            ),
        }
        self.frames["emotes"]["checkmark"] = (self.frames["checkmark"],)
        self.frames["emotes"]["cross"] = (self.frames["cross"],)
        prepare_checkmark_for_buttons(self.frames["checkmark"])

        for member in CustomCursor:
            cursor = pygame.image.load(
                support.resource_path(f"images/ui/cursor/{member.value}.png")
            ).convert_alpha()
            cursor = pygame.transform.scale_by(cursor, 4)
            self._available_cursors.append(cursor)

        self._cursor_img = self._available_cursors[CustomCursor.ARROW]

        setup_entity_assets()

        setup_gui()

        # sounds
        self.sounds = support.sound_importer("audio", default_volume=0.25)

        self.font = support.import_font(30, "font/LycheeSoda.ttf")

    def game_paused(self) -> bool:
        return self.current_state != GameState.PLAY

    def show_intro_msg(self) -> None:
        # A Message At The Starting Of The Game Giving Introduction To The Game And The InGroup.
        if not self.last_intro_txt_rendered:
            if not self.game_paused():
                if (
                    self.level.current_map == Map.NEW_FARM
                    # and self.round_config.get("character_introduction_text", "")
                    and self.round_config["character_introduction_timestamp"]
                    and self.round_end_timer
                    > self.round_config["character_introduction_timestamp"][0]
                ):
                    # get previous dialog text
                    intro_text = self.dialogue_manager.dialogues["intro_to_game"][0][1]

                    cam_target_to_text = (
                        _CAMERA_TARGET_TO_TEXT
                        if self.game_version != 3
                        else _CAMERA_TARGET_TO_TEXT_SOLO
                    )
                    cutscene_ani = self.level.cutscene_animation

                    if cutscene_ani.active:
                        # start of intro - camera at home location
                        index = cutscene_ani.current_index
                        if index < len(cam_target_to_text):
                            new_txt_id = cam_target_to_text[index]
                            if self.round_config.get(new_txt_id, ""):
                                intro_text = get_translated_msg(
                                    self.round_config[new_txt_id]
                                )
                            if self.game_version == 3 and index == _TARG_SKIP_IDX_SOLO:
                                # Skip two targets if the game is in control condition.
                                cutscene_ani.current_index += 1
                                cutscene_ani.force_to_next()
                        # end of intro - camera is over the home location
                        elif index == len(cutscene_ani.targets) - 1:
                            if self.dialogue_manager.showing_dialogue:
                                self.dialogue_manager.close_dialogue()

                            self.last_intro_txt_rendered = True

                    intro_text = intro_text.format(initials=self.player.name)

                    current_dialogue = self.dialogue_manager.dialogues["intro_to_game"][
                        0
                    ]
                    if current_dialogue[1] != intro_text:
                        # dialog text has changed -> camera arrived to next intro stage,
                        # set new dialog text
                        current_dialogue[1] = intro_text

                        # if old text is still displayed, reset dialog manager
                        if self.dialogue_manager.showing_dialogue:
                            self.dialogue_manager.close_dialogue()

                        # show dialog with new text in the position the same as tutorial
                        self.dialogue_manager.open_dialogue(
                            "intro_to_game", TUTORIAL_TB_LEFT, TUTORIAL_TB_TOP
                        )
                elif not self.round_config["character_introduction_timestamp"]:
                    self.last_intro_txt_rendered = True
        elif not self.level.cutscene_animation.active and not self.switched_to_tutorial:
            if not self.level.overlay.box_keybindings_label.enabled:
                self.level.overlay.box_keybindings_label.enabled = True
            if (
                not self.player.save_file.is_tutorial_completed
                and self.last_intro_txt_rendered
            ):
                self.switched_to_tutorial = True
                # we no longer need special npc features for the intro
                # assign hat and necklace according to regular logic
                for npc in self.level.game_map.npcs:
                    npc.special_features = None
                    npc.assign_outfit_ingroup(
                        self.round_config.get(
                            "ingroup_40p_hat_necklace_appearance", False
                        )
                    )
                # will be automatically skipped if the level does not have a tutorial (aka is > 1)
                self.tutorial.start()

    # events
    def event_loop(self) -> None:
        for event in pygame.event.get():
            if self.handle_event(event):
                continue

            if self.game_paused():
                if self.menus[self.current_state].handle_event(event):
                    continue

            if self.level.handle_event(event):
                continue

    def handle_event(self, event: pygame.event.Event) -> bool:
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()

        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == pygame.BUTTON_LEFT:
                if self._cursor == CustomCursor.POINT:
                    self.set_cursor(CustomCursor.CLICK)
            return False  # allow UI elements to handle this event as well

        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == pygame.BUTTON_LEFT:
                if self._cursor == CustomCursor.CLICK:
                    self.set_cursor(CustomCursor.POINT, override=True)
            return False

        elif event.type == OPEN_INVENTORY:
            self.switch_state(GameState.INVENTORY)
            return True
        elif event.type == DIALOG_SHOW:
            if self.dialogue_manager.showing_dialogue:
                return True
            else:
                if getattr(event, "is_gvt", False):
                    self.dialogue_manager.open_gvt_dialogue(
                        event.dial, self.gvt_msg_left, self.gvt_msg_top
                    )
                    return True
                self.dialogue_manager.open_dialogue(
                    event.dial, self.msg_left, self.msg_top
                )
                self.player.blocked = True
                self.player.direction.update((0, 0))
            return True
        elif event.type == DIALOG_ADVANCE:
            if self.dialogue_manager.showing_dialogue:
                if not self.last_intro_txt_rendered:
                    if self.dialogue_manager.current_tb_finished_advancing:
                        self.level.cutscene_animation.force_to_next()
                    self.show_intro_msg()
                self.dialogue_manager.advance(self.last_intro_txt_rendered)
                if not self.dialogue_manager.showing_dialogue:
                    self.player.blocked = False
            return True
        elif event.type == SHOW_BOX_KEYBINDINGS:
            if not self.level.cutscene_animation.active:
                self.level.overlay.box_keybindings.toggle_visibility()
            return True
        elif event.type == SHOW_BATH_INFO:
            if not self.level.cutscene_animation.active:
                self.level.overlay.bath_info.toggle_visibility()
            return True
        elif event.type == SET_CURSOR:
            self.set_cursor(event.cursor)
            return True
        return False

    async def run(self) -> None:
        pygame.mouse.set_visible(False)
        is_first_frame = True
        while self.running:
            dt = self.clock.tick() / 1000

            self.event_loop()

            is_game_paused = self.game_paused()

            self.display_surface.fill("#C0D470")

            if not is_game_paused or is_first_frame:
                if self.level.cutscene_animation.active:
                    event = pygame.key.get_pressed()
                    if (
                        event[pygame.K_RSHIFT]
                        and self.game_version == DEBUG_MODE_VERSION
                    ):
                        # fast-forward
                        self.level.update(dt * 5, self.current_state == GameState.PLAY)
                    else:
                        self.level.update(dt, self.current_state == GameState.PLAY)
                else:
                    self.level.update(dt, self.current_state == GameState.PLAY)

            if is_game_paused and not is_first_frame:
                self.display_surface.blit(self.previous_frame, (0, 0))
                self.menus[self.current_state].update(dt)
            else:
                # prevents events to happen during minigame
                if self.level.current_map != Map.VOLCANO and (
                    not self.level.current_minigame
                    or not self.level.current_minigame.running
                ):
                    self.round_end_timer += dt * WORLD_TIME_MULTIPLIER
                    if self.round_end_timer > self.ROUND_END_TIME_IN_MINUTES * 60:
                        self.send_telemetry("round_end", {})
                        self.round_end_timer = 0.0
                        self.switch_state(GameState.ROUND_END)
                    elif self._can_notify_new_crop:
                        msg_id = self.round_config["notify_new_crop_text"]
                        message = get_translated_msg("new_crop").format(
                            crop=get_translated_msg(f"{msg_id}_new_crop")
                        )
                        self.notification_menu.set_message(message)
                        self.switch_state(GameState.NOTIFICATION_MENU)
                        # set to empty to not repeat
                        self._empty_round_config_notify("new_crop")
                    elif (
                        self.round == 7
                        and self.round_end_timer > _ENABLE_SICKNESS_TSTAMP
                        and not self.level.npcs_state_registry.enabled
                    ):
                        self.round_config["healthbar"] = True
                        self.round_config["sickness"] = True
                        self.npc_sickness_mgr.apply_sickness_enable_to_existing_npcs()
                        self.level.npcs_state_registry.enable()
                    elif (
                        self.round >= 8  # Bath info available immediately from round 8
                        and not self.level.overlay.bath_info.enabled
                    ):
                        self.level.overlay.bath_info.enable()
                    elif self._can_notify_initial_gov_statement:
                        self._has_displayed_initial_gov_statement = True
                        self.notification_menu.set_message(
                            get_translated_msg("initial_gov_statement")
                        )
                        self.switch_state(GameState.NOTIFICATION_MENU)
                    elif self._can_notify_government:
                        message = self.round_config["notify_gov_statement_text"]
                        self._notify(message, "gov_statement")
                    elif self._can_notify_questionnaire:
                        message = self.round_config["notify_questionnaire_text"]
                        self._notify(message, "questionnaire")
                    elif self._can_notify_outgroup_money_income:
                        message = _get_outgroup_income(
                            self.round_config["notify_round_end_outgroup_text"],
                            self.player.in_outgroup,
                        )
                        self._notify(message, "round_end_outgroup")
                    elif self._can_start_self_assessment_sequence:
                        # remove first timestamp from list not to repeat infinitely
                        self.round_config["self_assessment_timestamp"] = (
                            self.round_config["self_assessment_timestamp"][1:]
                        )
                        self.switch_state(GameState.SELF_ASSESSMENT)
                    elif self._can_start_social_assessment_seq:
                        # remove first timestamp from list not to repeat infinitely
                        self.round_config["social_identity_assessment_timestamp"] = (
                            self.round_config["social_identity_assessment_timestamp"][
                                1:
                            ]
                        )
                        self.switch_state(GameState.SOCIAL_IDENTITY_ASSESSMENT)
                    elif self._can_start_hat_sequence:
                        # remove first timestamp from list not to repeat infinitely
                        self.round_config["player_hat_sequence_timestamp"] = (
                            self.round_config["player_hat_sequence_timestamp"][1:]
                        )
                        self.level.start_scripted_sequence(ScriptedSequence.PLAYER_HAT)
                    elif self._can_start_npc_necklace_sequence:
                        # remove first timestamp from list not to repeat infinitely
                        self.round_config["ingroup_necklace_sequence_timestamp"] = (
                            self.round_config["ingroup_necklace_sequence_timestamp"][1:]
                        )
                        self.level.start_scripted_sequence(
                            ScriptedSequence.INGROUP_NECKLACE
                        )
                    elif self._can_start_necklace_sequence:
                        # remove first timestamp from list not to repeat infinitely
                        self.round_config["player_necklace_sequence_timestamp"] = (
                            self.round_config["player_necklace_sequence_timestamp"][1:]
                        )
                        self.level.start_scripted_sequence(
                            ScriptedSequence.PLAYER_NECKLACE
                        )
                    elif self._can_start_birthday_sequence:
                        # remove first timestamp from list not to repeat infinitely
                        self.round_config["player_birthday_sequence_timestamp"] = (
                            self.round_config["player_birthday_sequence_timestamp"][1:]
                        )
                        self.level.start_scripted_sequence(
                            ScriptedSequence.PLAYER_BIRTHDAY
                        )
                    elif self._can_start_market_inactive_seq:
                        # remove first timestamp from list after transition to Town ends not to repeat infinitely
                        if self.level.current_map == Map.TOWN:
                            self.round_config[
                                "group_market_passive_player_sequence_timestamp"
                            ] = self.round_config[
                                "group_market_passive_player_sequence_timestamp"
                            ][1:]
                        self.level.start_scripted_sequence(
                            ScriptedSequence.GROUP_MARKET_PASSIVE
                        )
                    elif self._can_start_active_market_seq:
                        # remove first timestamp from list after transition to Town ends not to repeat infinitely
                        if self.level.current_map == Map.TOWN:
                            self.round_config[
                                "group_market_active_player_sequence_timestamp"
                            ] = self.round_config[
                                "group_market_active_player_sequence_timestamp"
                            ][1:]
                        self.level.start_scripted_sequence(
                            ScriptedSequence.GROUP_MARKET_ACTIVE
                        )
                    elif self._can_prompt_allocation:
                        allocations_id = self.round_config["resource_allocation_text"]
                        txt_to_add = _get_alloc_text(allocations_id)
                        self.allocation_task.allocations_text = get_translated_msg(
                            "share"
                        ).format(item_specific=txt_to_add)
                        self.allocation_task.parse_allocation_items(
                            self.round_config["resource_allocation_item_text"]
                        )
                        self.switch_state(GameState.PLAYER_TASK)
                        # set to empty not to repeat infinitely
                        self.round_config["resource_allocation_text"] = ""
                        self.round_config["resource_allocation_timestamp"] = []

            self.sickness_man.update_ply_sickness()
            self.npc_sickness_mgr.update_npc_status()

            if self.level.cutscene_animation.active:
                self.all_sprites.update_blocked(dt)
                if (
                    self.current_state == GameState.PLAY
                    and self.game_version == DEBUG_MODE_VERSION
                ):
                    event = pygame.key.get_pressed()
                    self.fast_forward.draw_option(self.display_surface)
                    if event[pygame.K_RSHIFT]:
                        self.fast_forward.draw_overlay(self.display_surface)
            else:
                self.all_sprites.update(dt)

            if self.player.has_goggles:
                self.goggles_delta += dt
            # this draw duplicates the same call in level.py, but without it, dialog box won't be visible
            self.all_sprites.draw(
                self.level.camera,
                is_game_paused,
            )

            FBLITTER.blit_all()

            # Apply blur effect only if the player has goggles equipped
            if self.player.has_goggles and self.current_state == GameState.PLAY:
                surface = pygame.transform.box_blur(self.display_surface, _BLUR_FACTOR)
                FBLITTER.schedule_blit(surface, (0, 0))

            # Into and Tutorial
            self.show_intro_msg()
            if (
                not self.player.save_file.is_tutorial_completed
                and not self.level.cutscene_animation.active
            ):
                self.tutorial.update(is_game_paused)

            mouse_pos = pygame.mouse.get_pos()
            if not is_game_paused or is_first_frame:
                self.previous_frame = self.display_surface.copy()
            FBLITTER.schedule_blit(self._cursor_img, mouse_pos)
            FBLITTER.blit_all()
            is_first_frame = False
            pygame.display.update()
            await asyncio.sleep(0)


if __name__ == "__main__":
    game = Game()
    asyncio.run(game.run())
