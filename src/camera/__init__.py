"""Stuff related to the in-game camera."""

from typing import Final, List

from .camera import Camera
from .camera_target import CameraTarget
from .quaker import Quaker
from .zoom_area import ZoomArea
from .zoom_manager import ZoomManager

__all__: Final[List[str]] = [
    "Camera",
    "CameraTarget",
    "Quaker",
    "ZoomArea",
    "ZoomManager",
]
