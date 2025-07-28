import pygame

from src.fblitter import FBLITTER
from src.support import import_image


class BathInfo:
    def __init__(self):
        self.display_surface = pygame.display.get_surface()
        self.visible = False
        self.enabled = False  # Will be enabled in round 8.

        # Load bath and goggles images separately
        self.bath_images = {}
        self.goggles_images = {}
        self._load_images()

        # Position and sizing for side-by-side display
        self.setup_positioning()

    def _load_images(self):
        """Load actual bath and goggles images for different round ranges."""
        try:
            # Load bath images
            self.bath_images[8] = import_image("images/ui/graphs/de_bath_round_8.png")
            self.bath_images[(9, 10)] = import_image(
                "images/ui/graphs/de_bath_round_910.png"
            )
            self.bath_images[(11, 12)] = import_image(
                "images/ui/graphs/de_bath_round_1112.png"
            )

            # Load goggles images
            self.goggles_images[8] = import_image(
                "images/ui/graphs/de_goggles_round_8.png"
            )
            self.goggles_images[(9, 10)] = import_image(
                "images/ui/graphs/de_goggles_round_910.png"
            )
            self.goggles_images[(11, 12)] = import_image(
                "images/ui/graphs/de_goggles_round_1112.png"
            )

            # Scale images to fit screen better if needed
            max_width = 400  # Reduced since we're showing two side by side
            max_height = 400

            # Scale bath images
            for round_key, image in self.bath_images.items():
                if image.get_width() > max_width or image.get_height() > max_height:
                    scale_factor = min(
                        max_width / image.get_width(), max_height / image.get_height()
                    )
                    new_width = int(image.get_width() * scale_factor)
                    new_height = int(image.get_height() * scale_factor)
                    self.bath_images[round_key] = pygame.transform.scale(
                        image, (new_width, new_height)
                    )

            # Scale goggles images
            for round_key, image in self.goggles_images.items():
                if image.get_width() > max_width or image.get_height() > max_height:
                    scale_factor = min(
                        max_width / image.get_width(), max_height / image.get_height()
                    )
                    new_width = int(image.get_width() * scale_factor)
                    new_height = int(image.get_height() * scale_factor)
                    self.goggles_images[round_key] = pygame.transform.scale(
                        image, (new_width, new_height)
                    )

        except Exception as e:
            print(f"Error loading bath/goggles images: {e}")
            # If images don't exist, create placeholder rectangles
            placeholder_bath = pygame.Surface((300, 250))
            placeholder_bath.fill((100, 150, 200))  # Light blue for bath
            placeholder_goggles = pygame.Surface((300, 250))
            placeholder_goggles.fill((200, 150, 100))  # Orange for goggles

            # Create placeholders for each round range
            self.bath_images = {
                8: placeholder_bath.copy(),
                (9, 10): placeholder_bath.copy(),
                (11, 12): placeholder_bath.copy(),
            }
            self.goggles_images = {
                8: placeholder_goggles.copy(),
                (9, 10): placeholder_goggles.copy(),
                (11, 12): placeholder_goggles.copy(),
            }

    def setup_positioning(self):
        """Setup the positioning for bath and goggles images side by side."""
        screen_width = self.display_surface.get_width()
        screen_height = self.display_surface.get_height()

        # Get sample images to determine size (use round 8 as default)
        bath_image = self.bath_images[8]
        goggles_image = self.goggles_images[8]

        # Calculate spacing and positions
        spacing = 20  # Space between the two images
        total_width = bath_image.get_width() + spacing + goggles_image.get_width()
        max_height = max(bath_image.get_height(), goggles_image.get_height())

        # Center the combined images horizontally and vertically
        start_x = (screen_width - total_width) // 2
        center_y = (screen_height - max_height) // 2

        # Position bath image on the left
        self.bath_pos = (start_x, center_y)

        # Position goggles image on the right
        self.goggles_pos = (start_x + bath_image.get_width() + spacing, center_y)

        # Background rect encompassing both images
        self.background_rect = pygame.Rect(
            start_x - 10, center_y - 10, total_width + 20, max_height + 20
        )

    def get_current_images(
        self, current_round: int
    ) -> tuple[pygame.Surface, pygame.Surface]:
        """Get the appropriate bath and goggles images for the current round."""
        # Determine which round range the current round falls into
        if current_round == 8:
            return self.bath_images[8], self.goggles_images[8]
        elif 9 <= current_round <= 10:
            return self.bath_images[(9, 10)], self.goggles_images[(9, 10)]
        elif 11 <= current_round <= 12:
            return self.bath_images[(11, 12)], self.goggles_images[(11, 12)]
        else:
            # Default to round 8 images for any other round (shouldn't happen in normal gameplay)
            return self.bath_images[8], self.goggles_images[8]

    def toggle_visibility(self):
        """Toggle the visibility of the bath info display."""
        if self.enabled:
            self.visible = not self.visible

    def show(self):
        """Show the bath info display."""
        if self.enabled:
            self.visible = True

    def hide(self):
        """Hide the bath info display."""
        self.visible = False

    def enable(self):
        """Enable the bath info functionality."""
        self.enabled = True

    def disable(self):
        """Disable the bath info functionality."""
        self.enabled = False
        self.visible = False

    def display(self, current_round: int):
        """Display the bath and goggles images side by side if visible and enabled."""
        if not self.visible or not self.enabled:
            return

        # Get the appropriate images for the current round
        bath_image, goggles_image = self.get_current_images(current_round)

        # Draw transparent black rounded background with outline
        background_surface = pygame.Surface(self.background_rect.size, pygame.SRCALPHA)

        # Draw filled rounded rectangle (transparent black background)
        pygame.draw.rect(
            background_surface,
            (0, 0, 0, 128),  # Semi-transparent black background
            (0, 0, self.background_rect.width, self.background_rect.height),
            0,  # Fill the rectangle
            10,  # Border radius for rounded corners
        )

        # Draw rounded rectangle outline (semi-transparent white border)
        pygame.draw.rect(
            background_surface,
            (255, 255, 255, 100),  # Semi-transparent white outline
            (0, 0, self.background_rect.width, self.background_rect.height),
            3,  # Border width
            10,  # Border radius for rounded corners
        )

        FBLITTER.schedule_blit(background_surface, self.background_rect.topleft)

        # Draw the bath image on the left (opaque)
        FBLITTER.schedule_blit(bath_image, self.bath_pos)

        # Draw the goggles image on the right (opaque)
        FBLITTER.schedule_blit(goggles_image, self.goggles_pos)
