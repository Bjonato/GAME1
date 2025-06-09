import base64
import json
import os
import sys
import random
from io import BytesIO
import pygame

SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
PLAYER_SPEED = 4
RUN_SPEED = 8
SAVE_FILE = "savegame.json"
ENCOUNTER_RATE = 0.4  # 40% chance when stepping in the grass

# Base64-encoded 32x32 placeholder sprite
CHARACTER_IMAGE_B64 = (
    "iVBORw0KGgoAAAANSUhEUgAAACAAAAAgCAIAAAD8GO2jAAAAKElEQVRIie3NMQEAAAjDMMC/"
    "ZzDBvlRA01vZJvwHAAAAAAAAAAAAbx2jxAE/0VKtIwAAAABJRU5ErkJggg=="
)

pygame.init()


class Player(pygame.sprite.Sprite):
    def __init__(self, x, y, image):
        super().__init__()
        self.image = image
        self.rect = self.image.get_rect(topleft=(x, y))
        # battle stats
        self.name = "Hero"
        self.max_hp = 10
        self.hp = 10
        self.strength = 3
        self.defense = 3
        self.speed = 3
        self.moves = ["Slash", "Prepare"]

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


class Enemy:
    """Simple container for enemy stats used in battles."""

    def __init__(self, name, max_hp, strength, defense, speed, moves):
        self.name = name
        self.max_hp = max_hp
        self.hp = max_hp
        self.strength = strength
        self.defense = defense
        self.speed = speed
        self.moves = moves


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
            self.message_timer = 120
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


class Room:
    def __init__(self, color, encounter_rect=None):
        self.color = color
        self.encounter_rect = encounter_rect


class Battle:
    def __init__(self, player, enemy, font, player_img, enemy_img):
        self.player = player
        self.enemy = enemy
        self.font = font
        self.player_img = player_img
        self.enemy_img = enemy_img
        self.menu_opts = ["Fight", "Bag", "Switch", "Run"]
        self.menu_index = 0
        self.move_index = 0
        self.state = "menu"  # menu, moves, message, enemy, victory, defeat, run
        self.message = ""
        self.msg_timer = 0

    def handle_event(self, event):
        if event.type != pygame.KEYDOWN:
            return
        if self.state == "menu":
            if event.key == pygame.K_UP:
                self.menu_index = (self.menu_index - 1) % len(self.menu_opts)
            elif event.key == pygame.K_DOWN:
                self.menu_index = (self.menu_index + 1) % len(self.menu_opts)
            elif event.key == pygame.K_RETURN:
                option = self.menu_opts[self.menu_index]
                if option == "Fight":
                    self.state = "moves"
                    self.move_index = 0
                elif option in {"Bag", "Switch"}:
                    self.message = f"{option} not implemented"
                    self.state = "message"
                    self.msg_timer = 60
                elif option == "Run":
                    self.message = "Got away safely!"
                    self.state = "run"
                    self.msg_timer = 60
        elif self.state == "moves":
            if event.key == pygame.K_UP:
                self.move_index = (self.move_index - 1) % len(self.player.moves)
            elif event.key == pygame.K_DOWN:
                self.move_index = (self.move_index + 1) % len(self.player.moves)
            elif event.key == pygame.K_ESCAPE:
                self.state = "menu"
            elif event.key == pygame.K_RETURN:
                self.player_move(self.player.moves[self.move_index])
        elif self.state == "message":
            if event.key == pygame.K_RETURN:
                if self.enemy.hp <= 0:
                    self.state = "victory"
                elif self.player.hp <= 0:
                    self.state = "defeat"
                else:
                    self.state = "enemy"
        elif self.state in {"victory", "defeat", "run"}:
            if event.key == pygame.K_RETURN:
                self.state = "end"

    def player_move(self, name):
        if name == "Prepare":
            self.player.defense += 1
            self.message = "You used Prepare!"
        else:  # Slash
            dmg = random.randint(4, 6) + self.player.strength - self.enemy.defense
            dmg = max(1, dmg)
            self.enemy.hp -= dmg
            self.message = f"You used Slash! {self.enemy.name} took {dmg} damage."
        self.state = "message"
        self.msg_timer = 60

    def enemy_move(self):
        dmg = random.randint(2, 4) + self.enemy.strength - self.player.defense
        dmg = max(1, dmg)
        self.player.hp -= dmg
        self.message = f"{self.enemy.name} used Scratch! You took {dmg} damage."
        self.state = "message"
        self.msg_timer = 60

    def update(self):
        if self.state == "enemy" and self.msg_timer == 0:
            self.enemy_move()
        if self.msg_timer > 0:
            self.msg_timer -= 1

    def draw(self, surface):
        surface.fill((0, 0, 0))
        # Draw enemy sprite
        enemy_rect = self.enemy_img.get_rect(topright=(SCREEN_WIDTH - 50, 150))
        surface.blit(self.enemy_img, enemy_rect)
        # Draw player sprite
        player_rect = self.player_img.get_rect(bottomleft=(50, SCREEN_HEIGHT - 150))
        surface.blit(self.player_img, player_rect)
        # HP bars
        self.draw_bar(surface, 50, SCREEN_HEIGHT - 170, self.player.hp, self.player.max_hp, self.player.name)
        self.draw_bar(surface, SCREEN_WIDTH - 250, 130, self.enemy.hp, self.enemy.max_hp, self.enemy.name)
        if self.state == "menu":
            self.draw_menu(surface, self.menu_opts, self.menu_index)
        elif self.state == "moves":
            self.draw_menu(surface, self.player.moves, self.move_index)
        if self.message:
            msg = self.font.render(self.message, True, (255, 255, 255))
            rect = msg.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
            surface.blit(msg, rect)

    def draw_menu(self, surface, options, index):
        menu_width = 200
        menu_height = len(options) * 30 + 20
        menu_x = SCREEN_WIDTH - menu_width - 20
        menu_y = SCREEN_HEIGHT - menu_height - 20
        pygame.draw.rect(surface, (50, 50, 50), (menu_x, menu_y, menu_width, menu_height))
        for i, text in enumerate(options):
            color = (255, 255, 255) if i == index else (170, 170, 170)
            render = self.font.render(str(text), True, color)
            surface.blit(render, (menu_x + 10, menu_y + 10 + i * 30))

    def draw_bar(self, surface, x, y, value, max_value, label):
        pygame.draw.rect(surface, (255, 255, 255), (x, y, 200, 20), 2)
        fill = int(196 * value / max_value)
        pygame.draw.rect(surface, (0, 200, 0), (x + 2, y + 2, fill, 16))
        text = self.font.render(f"{label}: {value}/{max_value}", True, (255, 255, 255))
        surface.blit(text, (x, y - 25))


def fade(screen, to_black=True):
    fade_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
    for alpha in range(0, 255, 15):
        fade_surface.set_alpha(alpha if to_black else 255 - alpha)
        fade_surface.fill((0, 0, 0))
        screen.blit(fade_surface, (0, 0))
        pygame.display.flip()
        pygame.time.delay(30)


def main():
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Simple RPG")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont(None, 32)

    img_bytes = base64.b64decode(CHARACTER_IMAGE_B64)
    player_img = pygame.image.load(BytesIO(img_bytes)).convert_alpha()
    enemy_img1 = pygame.Surface((32, 32))
    enemy_img1.fill((200, 0, 0))
    enemy_img2 = pygame.Surface((32, 32))
    enemy_img2.fill((0, 0, 200))

    player = Player(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2, player_img)
    menu = Menu(font)

    rooms = [
        Room((60, 120, 60)),
        Room((80, 100, 140), pygame.Rect(300, 200, 200, 200)),
    ]
    current_room = 0
    prev_pos = player.rect.topleft
    game_state = "map"
    battle = None
    running = True

    while running:
        keys = pygame.key.get_pressed()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE and game_state == "map":
                if menu.visible:
                    menu.hide()
                else:
                    menu.show()
            if game_state == "map" and menu.visible:
                menu.handle_event(event, player)
            elif game_state == "battle" and battle:
                battle.handle_event(event)

        if game_state == "map" and not menu.visible:
            player.handle_input(keys)
            # Room transitions
            if current_room == 0 and player.rect.top < 0:
                current_room = 1
                player.rect.bottom = SCREEN_HEIGHT
            elif current_room == 1 and player.rect.bottom > SCREEN_HEIGHT:
                current_room = 0
                player.rect.top = 0
            # Encounter check
            room = rooms[current_room]
            if room.encounter_rect and room.encounter_rect.colliderect(player.rect):
                if player.rect.topleft != prev_pos:
                    if random.random() < ENCOUNTER_RATE:
                        name = random.choice(["Slime", "Bat"])
                        enemy = Enemy(name, 5, 2, 2, 2, ["Scratch"])
                        enemy_img = enemy_img1 if name == "Slime" else enemy_img2
                        battle = Battle(player, enemy, font, player_img, enemy_img)
                        fade(screen, True)
                        game_state = "battle"
            prev_pos = player.rect.topleft

        if game_state == "battle" and battle:
            battle.update()
            if battle.state == "enemy" and battle.msg_timer == 0:
                battle.enemy_move()
            if battle.state == "end":
                fade(screen, False)
                game_state = "map"
                battle = None
                player.hp = max(1, player.hp)  # ensure not zero

        if game_state == "map":
            menu.update()
            room = rooms[current_room]
            screen.fill(room.color)
            if room.encounter_rect:
                pygame.draw.rect(screen, (40, 80, 40), room.encounter_rect)
            screen.blit(player.image, player.rect)
            menu.draw(screen)
        elif game_state == "battle" and battle:
            battle.draw(screen)

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()


if __name__ == "__main__":
    main()