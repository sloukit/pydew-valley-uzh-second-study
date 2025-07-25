import pygame

from src.fblitter import FBLITTER
from src.support import import_image


class BathInfo:
    def __init__(self):
        self.display_surface = pygame.display.get_surface()
        self.visible = False
        self.enabled = False  # Will be enabled after 30 seconds in round 7+

        # Load placeholder images for now (as mentioned in the issue, only 3 out of 6 images exist)
        # These will be replaced with actual images later
        self.placeholder_image = None
        self._load_placeholder_image()

        # Image pairs for different rounds - adjusted since bath info only starts from round 8
        # The "7-8" image is only shown in round 8, since feature is unavailable in round 7
        self.image_pairs = {
            (8, 8): self.bath_images.get(
                (7, 8), self.placeholder_image
            ),  # round 8 only (using 7-8 image)
            (9, 10): self.bath_images.get(
                (9, 10), self.placeholder_image
            ),  # rounds 9-10
            (11, 12): self.bath_images.get(
                (11, 12), self.placeholder_image
            ),  # rounds 11-12
        }

        # Position and sizing
        self.setup_positioning()

    def _load_placeholder_image(self):
        """Load actual bath info images for different round ranges."""
        # Load the actual German bath info images
        self.bath_images = {}
        try:
            self.bath_images[(7, 8)] = import_image(
                "images/ui/graphs/de_bath_round_78.png"
            )
            self.bath_images[(9, 10)] = import_image(
                "images/ui/graphs/de_bath_round_910.png"
            )
            self.bath_images[(11, 12)] = import_image(
                "images/ui/graphs/de_bath_round_1112.png"
            )

            # Use the first image to determine sizing
            self.bath_images[(7, 8)]
            # Scale images to fit screen better if needed
            max_width = 600
            max_height = 400

            for round_range, image in self.bath_images.items():
                if image.get_width() > max_width or image.get_height() > max_height:
                    # Scale down while maintaining aspect ratio
                    scale_factor = min(
                        max_width / image.get_width(), max_height / image.get_height()
                    )
                    new_width = int(image.get_width() * scale_factor)
                    new_height = int(image.get_height() * scale_factor)
                    self.bath_images[round_range] = pygame.transform.scale(
                        image, (new_width, new_height)
                    )

            # Set placeholder_image to the first one for initial setup
            self.placeholder_image = self.bath_images[(7, 8)]

        except Exception as e:
            print(f"Error loading bath info images: {e}")
            # If images don't exist, create placeholder rectangles
            self.placeholder_image = pygame.Surface((400, 300))
            self.placeholder_image.fill((100, 150, 200))  # Light blue placeholder

            # Create placeholders for each round range
            self.bath_images = {
                (7, 8): self.placeholder_image.copy(),
                (9, 10): self.placeholder_image.copy(),
                (11, 12): self.placeholder_image.copy(),
            }
            # Color them differently for distinction
            self.bath_images[(9, 10)].fill((150, 100, 200))  # Purple
            self.bath_images[(11, 12)].fill((200, 150, 100))  # Orange

    def setup_positioning(self):
        """Setup the positioning for the two images side by side."""
        screen_width = self.display_surface.get_width()
        screen_height = self.display_surface.get_height()

        # Center the image horizontally and vertically
        image_width = self.placeholder_image.get_width()
        image_height = self.placeholder_image.get_height()

        self.image_pos = (
            (screen_width - image_width) // 2,
            (screen_height - image_height) // 2,
        )

        # Background box for the image
        self.background_rect = pygame.Rect(
            self.image_pos[0] - 10,
            self.image_pos[1] - 10,
            image_width + 20,
            image_height + 20,
        )

    def get_current_round_pair(
        self, current_round: int
    ) -> tuple[pygame.Surface, pygame.Surface]:
        """Get the appropriate image pair for the current round."""
        for (start_round, end_round), image_pair in self.image_pairs.items():
            if start_round <= current_round <= end_round:
                return image_pair

        # Default to first pair if round is not in expected range
        return list(self.image_pairs.values())[0]

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
        """Display the bath info image if visible and enabled."""
        if not self.visible or not self.enabled:
            return

        # Get the appropriate image for the current round
        current_image = self.get_current_round_image(current_round)

        # Draw semi-transparent background
        background_surface = pygame.Surface(self.background_rect.size, pygame.SRCALPHA)
        background_surface.fill((0, 0, 0, 128))  # Semi-transparent black
        FBLITTER.schedule_blit(background_surface, self.background_rect.topleft)

        # Draw the bath info image (no border)
        FBLITTER.schedule_blit(current_image, self.image_pos)

    def get_current_round_image(self, current_round: int):
        """Get the appropriate bath info image for the current round."""
        # Determine which round range the current round falls into
        if current_round == 8:
            return self.image_pairs[(8, 8)]  # Show 7-8 image only in round 8
        elif 9 <= current_round <= 10:
            return self.image_pairs[(9, 10)]
        elif 11 <= current_round <= 12:
            return self.image_pairs[(11, 12)]
        else:
            # Default to first image for any other round (shouldn't happen in normal gameplay)
            return self.image_pairs[(8, 8)]
