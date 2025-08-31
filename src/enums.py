from enum import Enum, IntEnum, StrEnum, nonmember, auto  # noqa
from random import randint


class SicknessGravity(IntEnum):
    SEVERE = 0
    RECOVER = auto()


class NPCSicknessStatusChange(IntEnum):
    SICKNESS = 0
    SWITCH_TO_RECOVERY = auto()
    DIE = auto()
    GO_TO_BATHHOUSE = auto()


class ZoomState(IntEnum):
    NOT_ZOOMING = 0
    ZOOMING_IN = auto()
    ZOOMING_OUT = auto()
    ZOOM = auto()


class PlayerState(IntEnum):
    IDLE = 0
    WALK = 1


class ItemToUse(IntEnum):
    """Both available options for Player.use_tool. If any more have to be added, put them as members of this enum."""

    REGULAR_TOOL = 0
    SEED = 1


class GameState(IntEnum):
    MAIN_MENU = 0
    PLAY = 1
    PAUSE = 2
    SETTINGS = 3
    SHOP = 4
    EXIT = 5
    GAME_OVER = 6
    WIN = 7
    CREDITS = 8
    # Special value: when switched to this value, the game
    # saves and then sets its current state back to PLAY
    SAVE_AND_RESUME = 9
    INVENTORY = 10
    ROUND_END = 11
    OUTGROUP_MENU = 12
    PLAYER_TASK = 13
    SELF_ASSESSMENT = 14
    NOTIFICATION_MENU = 15
    SOCIAL_IDENTITY_ASSESSMENT = 16


# NOTE : DO NOT pay attention to anything the IDE might complain about in this class, as the enum generation mechanisms
# will ensure _SERIALISABLE_STRINGS is actually treated like a tuple of strings instead of an integer.
class _SerialisableEnum(IntEnum):
    _SERIALISABLE_STRINGS = nonmember(())  # This will be overridden in derived enums.

    def as_serialised_string(self):
        # We keep that method separate from the actual str dunder, so we can still get the original repr when debugging
        return self._SERIALISABLE_STRINGS[self]  # noqa

    @classmethod
    def from_serialised_string(cls, val: str):
        """Return an enum member from a serialised string.

        :param val: The serialised string.
        :return: The corresponding enum member.
        :raise LookupError: if no enum member matches this string."""
        try:
            return cls(cls._SERIALISABLE_STRINGS.index(val))  # noqa
        except IndexError as exc:
            raise LookupError(
                f"serialised string '{val}' does not match any member in enum '{cls.__name__}'"
            ) from exc


class InventoryResource(_SerialisableEnum):
    """All stored items in the inventory."""

    _SERIALISABLE_STRINGS = nonmember(
        (
            "wood",
            "apple",
            "blackberry",
            "blueberry",
            "raspberry",
            "orange",
            "peach",
            "pear",
            "corn",
            "tomato",
            "beetroot",
            "carrot",
            "eggplant",
            "pumpkin",
            "parsnip",
            "cabbage",
            "bean",
            "cauliflower",
            "red_cabbage",
            "wheat",
            "broccoli",
            "corn_seed",
            "tomato_seed",
            "beetroot_seed",
            "carrot_seed",
            "eggplant_seed",
            "pumpkin_seed",
            "parsnip_seed",
            "cabbage_seed",
            "cauliflower_seed",
            "red_cabbage_seed",
            "wheat_seed",
            "broccoli_seed",
        )
    )
    # All item worths in the game. When traders buy things off you, they pay you for half the worth.
    # If YOU buy something from THEM, then you have to pay the FULL worth, though.
    _ITEM_WORTHS = nonmember(
        (
            8,  # WOOD
            4,  # APPLE
            5,  # BLACKBERRY
            5,  # BLUEBERRY
            5,  # RASPBERRY
            20,  # ORANGE
            15,  # PEACH
            10,  # PEAR
            8,  # CORN
            10,  # TOMATO
            12,  # BEETROOT
            8,  # CARROT
            14,  # EGGPLANT
            20,  # PUMPKIN
            32,  # PARSNIP
            10,  # CABBAGE
            8,  # BEAN
            11,  # CAULIFLOWER
            16,  # RED_CABBAGE
            6,  # WHEAT
            20,  # BROCCOLI
            4,  # CORN_SEED
            5,  # TOMATO_SEED
            6,  # BEETROOT_SEED
            3,  # CARROT_SEED
            6,  # EGGPLANT_SEED
            7,  # PUMPKIN_SEED
            10,  # PARSNIP_SEED
            10,  # CABBAGE_SEED
            10,  # CAULIFLOWER_SEED
            10,  # RED_CABBAGE_SEED
            10,  # WHEAT_SEED
            10,  # BROCCOLI_SEED
        )
    )

    WOOD = 0
    APPLE = 1
    BLACKBERRY = 2
    BLUEBERRY = 3
    RASPBERRY = 4
    ORANGE = 5
    PEACH = 6
    PEAR = 7
    CORN = 8
    TOMATO = 9

    BEETROOT = 10
    CARROT = 11
    EGGPLANT = 12
    PUMPKIN = 13
    PARSNIP = 14
    CABBAGE = 15
    BEAN = 16
    CAULIFLOWER = 17
    RED_CABBAGE = 18
    WHEAT = 19
    BROCCOLI = 20

    CORN_SEED = 21
    TOMATO_SEED = 22

    BEETROOT_SEED = 23
    CARROT_SEED = 24
    EGGPLANT_SEED = 25
    PUMPKIN_SEED = 26
    PARSNIP_SEED = 27
    CABBAGE_SEED = 28
    CAULIFLOWER_SEED = 29
    RED_CABBAGE_SEED = 30
    WHEAT_SEED = 31
    BROCCOLI_SEED = 32

    def get_worth(self):
        return self._ITEM_WORTHS[self]  # noqa

    def is_seed(self):
        # Beans can also be used as seeds, and thus do not need their own seed type.
        return self >= self.CORN_SEED or self == self.BEAN

    def is_fruit(self):
        return self.APPLE <= self <= self.PEAR


class FarmingTool(_SerialisableEnum):
    """Notably used to distinguish the different farming tools (including seeds) in-code."""

    _SERIALISABLE_STRINGS = nonmember(
        (
            "none",
            "axe",
            "hoe",
            "water",
            "corn_seed",
            "tomato_seed",
            "beetroot_seed",
            "carrot_seed",
            "eggplant_seed",
            "pumpkin_seed",
            "parsnip_seed",
            "cabbage_seed",
            "bean",
            "cauliflower_seed",
            "red_cabbage_seed",
            "wheat_seed",
            "broccoli_seed",
        )
    )

    NONE = 0  # Possible placeholder value if needed somewhere
    AXE = 1
    HOE = 2
    WATERING_CAN = 3
    CORN_SEED = 4
    TOMATO_SEED = 5

    BEETROOT_SEED = 6
    CARROT_SEED = 7
    EGGPLANT_SEED = 8
    PUMPKIN_SEED = 9
    PARSNIP_SEED = 10
    CABBAGE_SEED = 11
    BEAN = 12
    CAULIFLOWER_SEED = 13
    RED_CABBAGE_SEED = 14
    WHEAT_SEED = 15
    BROCCOLI_SEED = 16

    _AS_IRS = nonmember(
        {
            CORN_SEED: InventoryResource.CORN_SEED,
            TOMATO_SEED: InventoryResource.TOMATO_SEED,
            BEETROOT_SEED: InventoryResource.BEETROOT_SEED,
            CARROT_SEED: InventoryResource.CARROT_SEED,
            EGGPLANT_SEED: InventoryResource.EGGPLANT_SEED,
            PUMPKIN_SEED: InventoryResource.PUMPKIN_SEED,
            PARSNIP_SEED: InventoryResource.PARSNIP_SEED,
            CABBAGE_SEED: InventoryResource.CABBAGE_SEED,
            BEAN: InventoryResource.BEAN,
            CAULIFLOWER_SEED: InventoryResource.CAULIFLOWER_SEED,
            RED_CABBAGE_SEED: InventoryResource.RED_CABBAGE_SEED,
            WHEAT_SEED: InventoryResource.WHEAT_SEED,
            BROCCOLI_SEED: InventoryResource.BROCCOLI_SEED,
        }
    )

    _AS_NS_IRS = nonmember(
        {
            CORN_SEED: InventoryResource.CORN,
            TOMATO_SEED: InventoryResource.TOMATO,
            BEETROOT_SEED: InventoryResource.BEETROOT,
            CARROT_SEED: InventoryResource.CARROT,
            EGGPLANT_SEED: InventoryResource.EGGPLANT,
            PUMPKIN_SEED: InventoryResource.PUMPKIN,
            PARSNIP_SEED: InventoryResource.PARSNIP,
            CABBAGE_SEED: InventoryResource.CABBAGE,
            BEAN: InventoryResource.BEAN,
            CAULIFLOWER_SEED: InventoryResource.CAULIFLOWER,
            RED_CABBAGE_SEED: InventoryResource.RED_CABBAGE,
            WHEAT_SEED: InventoryResource.WHEAT,
            BROCCOLI_SEED: InventoryResource.BROCCOLI,
        }
    )

    # Using frozenset to ensure this cannot change
    _swinging_tools = nonmember(frozenset({HOE, AXE}))

    def is_swinging_tool(self):
        return self in self._swinging_tools

    def is_seed(self):
        return self >= self.get_first_seed_id()

    @classmethod
    def get_first_tool_id(cls):
        """Return the first tool ID. This might change in the course of development."""
        return cls.AXE

    @classmethod
    def get_tool_count(cls):
        return cls.get_first_seed_id() - cls.get_first_tool_id()

    @classmethod
    def get_seed_count(cls):
        return len(cls) - cls.get_first_seed_id()

    @classmethod
    def get_first_seed_id(cls):
        """Same as get_first_tool_id, but for the seeds. Duh."""
        return cls.CORN_SEED

    def as_inventory_resource(self):
        """Converts self to InventoryResource type if possible.
        (Conversion is possible if self is considered a seed.)"""
        return self._AS_IRS.get(self, self)  # noqa

    def as_nonseed_inventory_resource(self):
        """Converts self to non-seed InventoryResource type if possible.
        (Conversion is possible if self is considered a seed.)"""
        return self._AS_NS_IRS.get(self, self)  # noqa


class SeedType(IntEnum):
    _AS_FTS = nonmember(
        (
            FarmingTool.CORN_SEED,
            FarmingTool.TOMATO_SEED,
            FarmingTool.BEETROOT_SEED,
            FarmingTool.CARROT_SEED,
            FarmingTool.EGGPLANT_SEED,
            FarmingTool.PUMPKIN_SEED,
            FarmingTool.PARSNIP_SEED,
            FarmingTool.CABBAGE_SEED,
            FarmingTool.BEAN,
            FarmingTool.CAULIFLOWER_SEED,
            FarmingTool.RED_CABBAGE_SEED,
            FarmingTool.WHEAT_SEED,
            FarmingTool.BROCCOLI_SEED,
        )
    )

    _AS_IRS = nonmember(
        (
            InventoryResource.CORN_SEED,
            InventoryResource.TOMATO_SEED,
            InventoryResource.BEETROOT_SEED,
            InventoryResource.CARROT_SEED,
            InventoryResource.EGGPLANT_SEED,
            InventoryResource.PUMPKIN_SEED,
            InventoryResource.PARSNIP_SEED,
            InventoryResource.CABBAGE_SEED,
            InventoryResource.BEAN,
            InventoryResource.CAULIFLOWER_SEED,
            InventoryResource.RED_CABBAGE_SEED,
            InventoryResource.WHEAT_SEED,
            InventoryResource.BROCCOLI_SEED,
        )
    )

    _AS_NS_IRS = nonmember(
        (
            InventoryResource.CORN,
            InventoryResource.TOMATO,
            InventoryResource.BEETROOT,
            InventoryResource.CARROT,
            InventoryResource.EGGPLANT,
            InventoryResource.PUMPKIN,
            InventoryResource.PARSNIP,
            InventoryResource.CABBAGE,
            InventoryResource.BEAN,
            InventoryResource.CAULIFLOWER,
            InventoryResource.RED_CABBAGE,
            InventoryResource.WHEAT,
            InventoryResource.BROCCOLI,
        )
    )

    CORN = 0
    TOMATO = 1
    BEETROOT = 2
    CARROT = 3
    EGGPLANT = 4
    PUMPKIN = 5
    PARSNIP = 6
    CABBAGE = 7
    BEAN = 8
    CAULIFLOWER = 9
    RED_CABBAGE = 10
    WHEAT = 11
    BROCCOLI = 12

    @classmethod
    def from_farming_tool(cls, val: FarmingTool):
        return cls(cls._AS_FTS.index(val))  # noqa

    @classmethod
    def from_inventory_resource(cls, val: InventoryResource):
        return cls(cls._AS_IRS.index(val))  # noqa

    def as_fts(self):
        return self._AS_FTS[self]  # noqa

    def as_ir(self):
        return self._AS_IRS[self]  # noqa

    def as_nonseed_ir(self):
        return self._AS_NS_IRS[self]  # noqa

    def as_plant_name(self):
        return self._AS_FTS[self].as_serialised_string().removesuffix("_seed")  # noqa


class Direction(IntEnum):
    UP = 0
    RIGHT = auto()
    DOWN = auto()
    LEFT = auto()
    UPLEFT = auto()
    UPRIGHT = auto()
    DOWNRIGHT = auto()
    DOWNLEFT = auto()

    @classmethod
    def random(cls):
        return Direction(randint(0, Direction.DOWNLEFT.value))

    def get_opposite(self):
        return _OPPOSITES[self]  # noqa


_OPPOSITES = (
    Direction.DOWN,
    Direction.LEFT,
    Direction.UP,
    Direction.RIGHT,
    Direction.DOWNRIGHT,
    Direction.DOWNLEFT,
    Direction.UPLEFT,
    Direction.UPRIGHT,
)


class EntityState(StrEnum):
    IDLE = "idle"
    WALK = "walk"

    AXE = "axe"
    HOE = "hoe"
    WATER = "water"

    # Special values for equipment rendering

    GOGGLES_AXE = "goggles_axe"
    GOGGLES_HOE = "goggles_hoe"
    GOGGLES_IDLE = "goggles_idle"
    GOGGLES_WALK = "goggles_walk"
    GOGGLES_WATER = "goggles_water"

    OUTGROUP_AXE = "outgroup_axe"
    OUTGROUP_HOE = "outgroup_hoe"
    OUTGROUP_IDLE = "outgroup_idle"
    OUTGROUP_WALK = "outgroup_walk"
    OUTGROUP_WATER = "outgroup_water"

    HAT_AXE = "hat_axe"
    HAT_HOE = "hat_hoe"
    HAT_IDLE = "hat_idle"
    HAT_WALK = "hat_walk"
    HAT_WATER = "hat_water"

    HORN_AXE = "horn_axe"
    HORN_HOE = "horn_hoe"
    HORN_IDLE = "horn_idle"
    HORN_WALK = "horn_walk"
    HORN_WATER = "horn_water"

    NECKLACE_AXE = "necklace_axe"
    NECKLACE_HOE = "necklace_hoe"
    NECKLACE_IDLE = "necklace_idle"
    NECKLACE_WALK = "necklace_walk"
    NECKLACE_WATER = "necklace_water"


# TODO: Refactor AIState usages to use EntityState
class AIState(IntEnum):
    IDLE = 0
    MOVING = 1


class Layer(IntEnum):
    WATER = 0
    GROUND = auto()
    GROUND_OBJECTS = auto()
    SOIL = auto()
    SOIL_WATER = auto()
    RAIN_FLOOR = auto()
    PLANT = auto()
    MAIN = auto()
    FRUIT = auto()
    BORDER = auto()
    RAIN_DROPS = auto()
    PARTICLES = auto()
    EMOTES = auto()
    TEXT_BOX = auto()
    VOLCANO = auto()


class SpecialObjectLayer(StrEnum):
    LOCK_MINIGAME = "lock_minigame"
    INTERACTIONS = "Interactions"
    COLLISIONS = "Collisions"
    TREES = "Trees"
    PLAYER = "Player"
    NPCS = "NPCs"
    ANIMALS = "Animals"
    CAMERA_TARGETS = "Camera Targets"
    ZOOM_AREAS = "Zoom Areas"
    MINIGAME = "Minigame"


class Map(StrEnum):
    FARM = "farm"
    NEW_FARM = "farm_new"
    FOREST = "forest"
    TOWN = "town"
    MINIGAME = "minigame"
    VOLCANO = "volcano"


class StudyGroup(IntEnum):
    """The group in which a certain character belongs to."""

    NO_GROUP = 0  # Set at the beginning of the game.
    INGROUP = auto()
    OUTGROUP = auto()


class ClockVersion(IntEnum):
    ANALOG = 0
    DIGITAL = auto()


class ScriptedSequence(StrEnum):
    PLAYER_HAT = "player_hat_sequence"
    PLAYER_NECKLACE = "player_necklace_sequence"
    PLAYER_BIRTHDAY = "player_birthday_sequence"
    INGROUP_NECKLACE = "ingroup_necklace_sequence"
    GROUP_MARKET_PASSIVE = "group_market_passive_player_sequence"
    GROUP_MARKET_ACTIVE = "group_market_active_player_sequence"


class CustomCursor(IntEnum):
    ARROW = 0
    POINT = 1
    CLICK = 2


class SelfAssessmentDimension(IntEnum):
    AROUSAL = 0
    DOMINANCE = auto()
    VALENCE = auto()


class SocialIdentityAssessmentDimension(IntEnum):
    INGROUP = 0
    OUTGROUP = 1
    MIKA = 2
