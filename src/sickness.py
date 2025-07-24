from random import random
from typing import Callable
from src.sprites.entities.player import Player
from src.settings import GogglesStatus
from src.settings import (
    SICK_DURATION,
    SICK_DECLINE,
    SICK_INCLINE,
    SICK_MIN_HP,
    MAX_HP,
    SICK_INTERVAL,
)


# Key format: (bath, goggles)
# Value format: (rds 7-9, rds 10-12)
_SICKNESS_PROBABILITIES = {
    (False, False): (0.9, 0.7),
    (True, False): (0.5, 0.3),
    (False, True): (0.7, 0.5),
    (True, True): (0.1, 0.1),
}


def _random_from_probability(prob: float):
    return random() < prob


class SicknessManager:
    def __init__(
        self,
        player: Player,
        get_round: Callable[[], int],
        get_round_end_timer: Callable[[], float],
        get_goggles_status: Callable[[], GogglesStatus],
        get_bath_status: Callable[[], bool],
        reset_goggles_delta: Callable[[], None],
    ):
        self.get_round = get_round
        self.get_rend_timer = get_round_end_timer
        self._goggles_status = get_goggles_status
        self._bath_status = get_bath_status
        self.player = player
        self.reset_goggles_delta = reset_goggles_delta
        self.sickness_calc_count = 0

    @property
    def _sickness_likelihood(self) -> float:
        if self.get_round() < 7 or self.get_rend_timer() < SICK_INTERVAL:
            return 0.0
        return _SICKNESS_PROBABILITIES[(self._bath_status(), self._goggles_status())][
            self.get_round() > 9
        ]

    def should_make_player_sick(self):
        return _random_from_probability(self._sickness_likelihood)

    def update_ply_sickness(self):
        if not self.player.round_config.get("sickness", False):
            return

        current_time = int(self.get_rend_timer()) # need int for modulo at bottom
        # if (
        #     self.get_round() < 7 or current_time < SICK_INTERVAL
        # ):  # cannot get sick before round 7 or 5mins in
        #     return

        # at 5mins and 10mins determine whether a player is sick
        if current_time >= SICK_INTERVAL*(self.sickness_calc_count + 1):
            self.sickness_calc_count += 1
            if self.should_make_player_sick():
                self.player.get_sick()
            self.reset_goggles_delta()

        # at 9mins and 14mins make potentially sick player recover, otherwise change hp
        if self.player.is_sick:
            if current_time>=SICK_INTERVAL*self.sickness_calc_count+SICK_DURATION:
                self.player.recover()
            else: #adjust hp logic
                sick_interval_time = current_time % SICK_INTERVAL
                if sick_interval_time < SICK_DECLINE:  # first decrease health
                    self.player.set_hp(MAX_HP - (MAX_HP-SICK_MIN_HP)*sick_interval_time/SICK_DECLINE)
                else:  # then increase health again
                    self.player.set_hp(SICK_MIN_HP + (MAX_HP-SICK_MIN_HP)*(sick_interval_time-SICK_DECLINE)/SICK_INCLINE)
