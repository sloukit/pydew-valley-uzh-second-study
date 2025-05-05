"""Various exceptions and warning categories used in the game."""


class InvalidMapError(Exception):
    """Something is not valid in the given game map."""


class MinigameSetupError(Exception):
    """Something unexpected happened during minigame setup."""


class LoginError(Exception):
    """Something unexpected happened during login request."""


class TooEarlyLoginError(LoginError):
    """The user tried to log into the game too early."""


class DevWarning(Warning):
    """Base warning class for development-related warnings.

    Should be favoured over UserWarning if no subclass fits for a given warning,
    since warnings are more likely to be caused by the dev and not the players."""


class PathfindingWarning(DevWarning):
    """Pathfinding-related warnings."""


class GameMapWarning(DevWarning):
    # NOTE: docstring acts as if we put a pass instruction here,
    # so pass usage is not required
    """Game map-related warning category."""


class CameraWarning(DevWarning):
    """Camera-related warning category."""
