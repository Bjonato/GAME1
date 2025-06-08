import base64
import json
import os
import sys
from io import BytesIO
import pygame

SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
PLAYER_SPEED = 4
RUN_SPEED = 8
SAVE_FILE = "savegame.json"

# Base64-encoded 32x32 placeholder sprite
CHARACTER_IMAGE_B64 = (
    "iVBORw0KGgoAAAANSUhEUgAAACAAAAAgCAIAAAD8GO2jAAAAKElEQVRIie3NMQEAAAjDMMC/"
    "ZzDBvlRA01vZJvwHAAAAAAAAAAAAbx2jxAE/0VKtIwAAAABJRU5ErkJggg=="
)

pygame.init()

# Simple Player class
class Player(pygame.sprite.Sprite):
    def __init__(self, x, y, image):
        super().__init__()
        self.image = image
        self.rect = self.image.get_rect(topleft=(x, y))

    def handle_input(self, keys):
        speed = RUN_SPEED if keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT] else PLAYER_SPEED
        dx = dy = 0
        if keys[pygame.K_LEFT]:
            dx -= speed
        if keys[pygame.K_RIGHT]:
            dx += speed
        if keys[pygame.K_UP]:
            dy -= speed
        if keys[pygame.K_DOWN]:
            dy += speed
        self.rect.x += dx
        self.rect.y += dy
        # Keep player on screen
        self.rect.x = max(0, min(self.rect.x, SCREEN_WIDTH - self.rect.width))
        self.rect.y = max(0, min(self.rect.y, SCREEN_HEIGHT - self.rect.height))

# Simple Menu class
class Menu:
    def __init__(self, font):
        self.options = [
            "Return to Game",
            "Options",
            "Team",
            "Bag",
            "Save Game",
            "Load Game",
            "Quit Game",
        ]
        self.font = font
        self.selected = 0
        self.visible = False
        self.message = ""
        self.message_timer = 0

    def show(self):
        self.visible = True
        self.selected = 0

    def hide(self):
        self.visible = False

    def handle_event(self, event, player):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_UP:
                self.selected = (self.selected - 1) % len(self.options)
            elif event.key == pygame.K_DOWN:
                self.selected = (self.selected + 1) % len(self.options)
            elif event.key == pygame.K_RETURN:
                self.activate_option(player)

    def activate_option(self, player):
        option = self.options[self.selected]
        if option == "Return to Game":
            self.hide()
        elif option in {"Options", "Team", "Bag"}:
            self.message = f"{option} not implemented"
            self.message_timer = 120  # frames to show message
        elif option == "Save Game":
            save_game(player)
            self.message = "Game saved"
            self.message_timer = 120
        elif option == "Load Game":
            load_game(player)
            self.message = "Game loaded"
            self.message_timer = 120
        elif option == "Quit Game":
            pygame.quit()
            sys.exit()

    def update(self):
        if self.message_timer > 0:
            self.message_timer -= 1
        else:
            self.message = ""

    def draw(self, surface):
        if not self.visible:
            return
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        overlay.set_alpha(180)
        overlay.fill((0, 0, 0))
        surface.blit(overlay, (0, 0))

        menu_width = 300
        menu_height = len(self.options) * 40 + 20
        menu_x = (SCREEN_WIDTH - menu_width) // 2
        menu_y = (SCREEN_HEIGHT - menu_height) // 2
        pygame.draw.rect(surface, (50, 50, 50), (menu_x, menu_y, menu_width, menu_height))
        for i, text in enumerate(self.options):
            color = (255, 255, 255) if i == self.selected else (170, 170, 170)
            render = self.font.render(text, True, color)
            surface.blit(render, (menu_x + 20, menu_y + 20 + i * 40))
        if self.message:
            msg = self.font.render(self.message, True, (255, 255, 0))
            surface.blit(msg, (menu_x, menu_y - 40))

def save_game(player):
    data = {"x": player.rect.x, "y": player.rect.y}
    with open(SAVE_FILE, "w") as f:
        json.dump(data, f)

def load_game(player):
    if os.path.exists(SAVE_FILE):
        with open(SAVE_FILE, "r") as f:
            data = json.load(f)
            player.rect.x = data.get("x", player.rect.x)
            player.rect.y = data.get("y", player.rect.y)


def main():
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Simple RPG")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont(None, 32)

    # Decode the embedded sprite
    img_bytes = base64.b64decode(CHARACTER_IMAGE_B64)
    player_image = pygame.image.load(BytesIO(img_bytes)).convert_alpha()
    player = Player(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2, player_image)
    menu = Menu(font)

    running = True
    while running:
        keys = pygame.key.get_pressed()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                if menu.visible:
                    menu.hide()
                else:
                    menu.show()
            if menu.visible:
                menu.handle_event(event, player)

        if not menu.visible:
            player.handle_input(keys)

        menu.update()
        screen.fill((60, 120, 60))  # simple background color
        screen.blit(player.image, player.rect)
        menu.draw(screen)
        pygame.display.flip()
        clock.tick(60)

    pygame.quit()


if __name__ == "__main__":
    main()
