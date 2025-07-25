from functools import cache
import pygame

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
