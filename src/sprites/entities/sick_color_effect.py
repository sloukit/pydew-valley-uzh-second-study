from functools import cache

import pygame

# using cache
# apply_sick_color_effect took 0.000005 seconds
# apply_sick_color_effect took 0.000006 seconds
# apply_sick_color_effect took 0.000006 seconds
# apply_sick_color_effect took 0.000005 seconds
# apply_sick_color_effect took 0.000006 seconds
# apply_sick_color_effect took 0.000008 seconds
# apply_sick_color_effect took 0.000005 seconds
# apply_sick_color_effect took 0.000004 seconds
# apply_sick_color_effect took 0.000004 seconds
# apply_sick_color_effect took 0.000004 seconds
# apply_sick_color_effect took 0.000004 seconds
# apply_sick_color_effect took 0.000004 seconds
# apply_sick_color_effect took 0.000004 seconds
# apply_sick_color_effect took 0.000005 seconds
# apply_sick_color_effect took 0.000003 seconds
# apply_sick_color_effect took 0.000003 seconds
# apply_sick_color_effect took 0.000003 seconds
# apply_sick_color_effect took 0.000002 seconds


# without the cache
# apply_sick_color_effect took 0.030930 seconds
# apply_sick_color_effect took 0.030964 seconds
# apply_sick_color_effect took 0.032071 seconds
# apply_sick_color_effect took 0.037817 seconds
# apply_sick_color_effect took 0.038521 seconds
# apply_sick_color_effect took 0.033641 seconds
# apply_sick_color_effect took 0.040135 seconds
# apply_sick_color_effect took 0.044454 seconds
# apply_sick_color_effect took 0.044409 seconds
# apply_sick_color_effect took 0.045047 seconds
# apply_sick_color_effect took 0.043131 seconds
# apply_sick_color_effect took 0.032540 seconds
# apply_sick_color_effect took 0.038410 seconds
# apply_sick_color_effect took 0.041751 seconds
# apply_sick_color_effect took 0.042381 seconds
# apply_sick_color_effect took 0.041693 seconds
# apply_sick_color_effect took 0.173787 seconds
# apply_sick_color_effect took 0.075202 seconds
# apply_sick_color_effect took 0.081068 seconds
# apply_sick_color_effect took 0.069109 seconds
# apply_sick_color_effect took 0.149018 seconds
# apply_sick_color_effect took 0.148739 seconds


@cache
def apply_sick_color_effect(surf: pygame.Surface) -> pygame.Surface:
    """Applies a green-ish tint to the player sprite to represent sickness. In a separate due to circular imports (character + player both need this function)"""

    # Create a copy of the surface and ensure it has per-pixel alpha
    sick_surface = surf.convert_alpha()

    # Define color mappings from normal to sick colors
    color_mappings = {
        (243, 242, 192): (103, 131, 92),  # Fur Colour -> Sick Fur Colour
        (220, 212, 220): (103, 131, 92),  # Out-group Fur Colour -> Sick Fur Colour
        (243, 216, 197): (86, 101, 96),  # Cheek Colour -> Sick Cheek Colour
        (92, 78, 146): (86, 101, 96),  # Out-group Cheek Colour -> Sick Cheek Colour
        (221, 213, 222): (
            134,
            81,
            97,
        ),  # Accentuation Colour -> Sick Accentuation Colour
        (152, 167, 212): (
            134,
            81,
            97,
        ),  # Out-group Accentuation Colour -> Sick Accentuation Colour
        (232, 181, 172): (107, 75, 91),  # Ear Colour -> Sick Ear Colour
        (118, 109, 170): (103, 131, 92),  # Out-group Ear Colour -> Sick Ear Colour
        (192, 208, 255): (
            103,
            131,
            92,
        ),  # Slightly Darker Out-group Fur Colour -> Sick Colour
    }

    # Use pixel-by-pixel replacement (slower but more compatible)
    width = sick_surface.get_width()
    height = sick_surface.get_height()

    for x in range(width):
        for y in range(height):
            pixel_color = sick_surface.get_at((x, y))
            rgb = (pixel_color.r, pixel_color.g, pixel_color.b)

            if rgb in color_mappings:
                new_color = color_mappings[rgb]
                sick_surface.set_at((x, y), (*new_color, pixel_color.a))
                # print('colour mapping worked and set a value')

    return sick_surface
