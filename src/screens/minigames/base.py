from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from typing import TypeVar

import pygame


@dataclass
class MinigameState:
    pass


MinigameStateType = TypeVar("MinigameStateType", bound=MinigameState)


class Minigame(ABC):
    _state: MinigameStateType

    running: bool

    __on_start_funcs: list[Callable[[], None]]
    __on_finish_funcs: list[Callable[[], None]]

    def __init__(self, state: MinigameStateType):
        self._state = state

        self._running = False

        self._ctime = 0

        self.__on_start_funcs = []
        self.__on_finish_funcs = []

    @property
    def running(self):
        return self._running

    def on_start(self, func: Callable[[], None]):
        self.__on_start_funcs.append(func)

    def on_finish(self, func: Callable[[], None]):
        self.__on_finish_funcs.append(func)

    def start(self):
        self._running = True
        self._ctime = 0

        for func in self.__on_start_funcs:
            func()

    def finish(self):
        self._running = False

        for func in self.__on_finish_funcs:
            func()

    @abstractmethod
    def handle_event(self, event: pygame.Event):
        pass

    def update(self, dt: float):
        self._ctime += dt

    @abstractmethod
    def draw(self):
        pass
