"""
src.gui.interface
The interface submodule of gui groups everything related to the in-game
user-interface.

Apart from the base classes contained in emotes_base, all elements are ready
for use in the game.
"""

from .dialog import DialogueManager, GvtTextBox, TextBox
from .emotes import EmoteBox, NPCEmoteManager, PlayerEmoteManager

__all__ = (
    "EmoteBox",
    "PlayerEmoteManager",
    "NPCEmoteManager",
    "GvtTextBox",
    "DialogueManager",
    "TextBox",
)

