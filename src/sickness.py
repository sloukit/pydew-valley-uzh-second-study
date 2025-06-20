from random import random
from typing import Callable

from src.settings import GogglesStatus

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
        get_round: Callable[[], int],
        get_round_end_timer: Callable[[], float],
        get_goggles_status: Callable[[], GogglesStatus],
        get_bath_status: Callable[[], bool],
        is_ply_sick: Callable[[], bool],
        send_telemetry: Callable[[str, dict], None],
        make_player_sick: Callable[[], None],
        make_ply_recover: Callable[[], None],
        reset_goggles_delta: Callable[[], None],
    ):
        self.get_round = get_round
        self.get_rend_timer = get_round_end_timer
        self._goggles_status = get_goggles_status
        self._bath_status = get_bath_status
        self._is_ply_sick = is_ply_sick
        self.send_telemetry = send_telemetry
        self._make_ply_sick = make_player_sick
        self._make_ply_recover = make_ply_recover
        self.reset_goggles_delta = reset_goggles_delta
        self.sickness_calc_count = 0

    @property
    def _sickness_likelihood(self) -> float:
        if self.get_round() < 7 or self.get_rend_timer() < 300 or self._is_ply_sick():
            return 0.0
        return _SICKNESS_PROBABILITIES[(self._bath_status(), self._goggles_status())][
            self.get_round() > 9
        ]

    def should_make_player_sick(self):
        return _random_from_probability(self._sickness_likelihood)

    def update_ply_sickness(self):
        current_round = self.get_round()
        if current_round < 7 or self.get_rend_timer() < 300:
            return

        current_timer = self.get_rend_timer()

        if (
            self.get_rend_timer() >= 300
            and not self.sickness_calc_count
            or current_timer >= 600
            and self.sickness_calc_count < 2
        ):
            self.sickness_calc_count += 1
            if self.should_make_player_sick():
                self._make_ply_sick()
            else:
                self._make_ply_recover()
            self.reset_goggles_delta()
