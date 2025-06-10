import base64
import json
import os
import sys
import random
from io import BytesIO

# Avoid audio initialization errors on systems without sound hardware
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("XDG_RUNTIME_DIR", "/tmp")

import pygame

SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
PLAYER_SPEED = 4
RUN_SPEED = 8
SAVE_FILE = "savegame.json"
ENCOUNTER_RATE = 0.4  # Chance when stepping in the encounter zone
ENCOUNTER_DELAY_RANGE = (120, 300)  # frames (2-5 seconds)
COIN_DROP = {
    1: (1, 3),
    2: (2, 4),
    3: (3, 5),
}

# Item drop chances per room
ITEM_DROP = {
    0: [
        ("Health Potion", 0.15),
        ("Elite Scraps", 0.05),
        ("Good Scraps", 0.10),
        ("Scraps", 0.20),
    ],
    1: [
        ("Health Potion", 0.15),
        ("Elite Scraps", 0.05),
        ("Good Scraps", 0.10),
        ("Scraps", 0.20),
        ("Slime", 0.10),
    ],
}

# Item definitions used for the shop and inventory
ITEMS = {
    "ShortSword": {
        "type": "weapon",
        "strength": 1,
        "price": 5,
    },
    "LongSword": {
        "type": "weapon",
        "strength": 3,
        "speed": -1,
        "price": 10,
    },
    "Health Potion": {
        "type": "potion",
        "heal": 5,
        "price": 3,
        "stack": 5,
    },
    "Scraps": {
        "type": "craft",
        "price": 1,
        "stack": 25,
    },
    "Good Scraps": {
        "type": "craft",
        "price": 2,
        "stack": 25,
    },
    "Elite Scraps": {
        "type": "craft",
        "price": 3,
        "stack": 25,
    },
    "Slime": {
        "type": "craft",
        "price": 2,
        "stack": 5,
    },
}

# Base64-encoded 32x32 knight sprite with two walking frames
CHARACTER_FRAMES_B64 = [
    "iVBORw0KGgoAAAANSUhEUgAAACAAAAAgCAYAAABzenr0AAAAkklEQVR4nO2VsQ3AIAwESZQ5GIKJXFAxEBWFh6FmpdCHIDBB+iL+0sLm9Jb8xqhUqr/rkDYw8z16Q0TTc08pwG7BAa7VRiJqaswsngN3AA6wvIIVu98EdwAOIF5BznkrwPBixRiby1dK6b53zjW1EEL3H/gKFAAOII5j7/0wjlNKGscKoADTEofRMwestZ8A4A5UY8UZJparjTMAAAAASUVORK5CYII=",
    "iVBORw0KGgoAAAANSUhEUgAAACAAAAAgCAYAAABzenr0AAAApUlEQVR4nO2WsQ3EIAxFk9NN5IlcUDEQFYWHofYQ1OyQ1BGnxEaRfnH+HcjA07eF/raFQqF/1+49ICLHUw0zm+/9eAHeFhzgu3qQmac9EXHfA3cADrDcghW7fwnuABzA3YLW2qsAcAfgAKY/u5Qy/f+qOtUR0bSXc759A+5AAMAB3IEkpfQYSGqtEUgCwKylPDDGuKx775c1ER2qahpEtwOeCbfoBGOcIaGV2JaWAAAAAElFTkSuQmCC",
]

pygame.init()


class Player(pygame.sprite.Sprite):
    def __init__(self, x, y, images):
        super().__init__()
        self.images = images
        self.image = images[0]
        self.rect = self.image.get_rect(topleft=(x, y))
        self.anim_index = 0
        self.anim_timer = 0
        # battle stats
        self.name = "Devon"
        self.level = 1
        self.weapon = None
        self.weapon_bonus = 0
        self.inventory = [None] * 25  # 5x5 grid
        self.coins = 0
        self.max_hp = 10
        self.hp = 10
        self.base_strength = 3
        self.base_defense = 3
        self.base_speed = 3
        self.strength = self.base_strength
        self.defense = self.base_defense
        self.speed = self.base_speed
        self.moves = ["Slash", "Prepare"]
        self.xp = 0
        self.stat_points = 0

    def recalc_stats(self):
        self.strength = self.base_strength
        self.defense = self.base_defense
        self.speed = self.base_speed
        if self.weapon:
            data = ITEMS.get(self.weapon, {})
            self.strength += data.get("strength", 0)
            self.speed += data.get("speed", 0)
        self.strength += self.weapon_bonus

    def add_item(self, name):
        for i, slot in enumerate(self.inventory):
            if not slot:
                self.inventory[i] = {"name": name, "qty": 1}
                return True
            if slot["name"] == name and ITEMS.get(name, {}).get("stack"):
                if slot["qty"] < ITEMS[name]["stack"]:
                    self.inventory[i]["qty"] += 1
                    return True
        return False

    def remove_item(self, index):
        item = self.inventory[index]
        if not item:
            return None
        item["qty"] -= 1
        if item["qty"] <= 0:
            self.inventory[index] = None
        return item["name"]

    def take_item(self, name):
        """Remove one of the given item from inventory."""
        for i, slot in enumerate(self.inventory):
            if slot and slot["name"] == name:
                self.remove_item(i)
                return True
        return False

    def count_item(self, name):
        total = 0
        for slot in self.inventory:
            if slot and slot["name"] == name:
                total += slot["qty"]
        return total

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
        if dx or dy:
            self.anim_timer += 1
            if self.anim_timer >= 10:
                self.anim_timer = 0
                self.anim_index = (self.anim_index + 1) % len(self.images)
            self.image = self.images[self.anim_index]
        else:
            self.anim_timer = 0
            self.anim_index = 0
            self.image = self.images[0]

    def xp_to_next(self):
        return 5 + (self.level - 1) * 2

    def gain_xp(self, amount):
        self.xp += amount
        leveled = False
        while self.xp >= self.xp_to_next():
            self.xp -= self.xp_to_next()
            self.level += 1
            inc = random.randint(1, 2)
            self.max_hp += inc
            self.hp += inc
            self.stat_points += 1
            leveled = True
        return leveled


class Enemy:
    """Simple container for enemy stats used in battles."""

    def __init__(self, name, level, max_hp, strength, defense, speed, moves):
        self.name = name
        self.level = level
        self.max_hp = max_hp
        self.hp = max_hp
        self.strength = strength
        self.defense = defense
        self.speed = speed
        self.moves = moves
        self.xp = level


def create_enemy(name, level):
    """Create an enemy with stats scaled by level."""
    hp = 5 + (level - 1) * 2
    stat = 2 + (level - 1)
    moves = ["Scratch"]
    if name == "Gremlin":
        moves.append("Slime")
    return Enemy(name, level, hp, stat, stat, stat, moves)


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
                return self.activate_option(player)

    def activate_option(self, player):
        option = self.options[self.selected]
        if option == "Return to Game":
            self.hide()
        elif option == "Team":
            self.hide()
            return "team"
        elif option == "Bag":
            self.hide()
            return "bag"
        elif option == "Options":
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

    def draw(self, surface, player):
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
        coin_txt = self.font.render(f"Coins: {player.coins}", True, (255, 255, 255))
        surface.blit(coin_txt, (menu_x, menu_y - 40))
        for i, text in enumerate(self.options):
            color = (255, 255, 255) if i == self.selected else (170, 170, 170)
            render = self.font.render(text, True, color)
            surface.blit(render, (menu_x + 20, menu_y + 20 + i * 40))
        if self.message:
            msg = self.font.render(self.message, True, (255, 255, 0))
            surface.blit(msg, (menu_x, menu_y - 70))


def save_game(player):
    data = {
        "x": player.rect.x,
        "y": player.rect.y,
        "coins": player.coins,
        "inventory": player.inventory,
        "weapon": player.weapon,
        "weapon_bonus": player.weapon_bonus,
    }
    with open(SAVE_FILE, "w") as f:
        json.dump(data, f)


def load_game(player):
    if os.path.exists(SAVE_FILE):
        with open(SAVE_FILE, "r") as f:
            data = json.load(f)
            player.rect.x = data.get("x", player.rect.x)
            player.rect.y = data.get("y", player.rect.y)
            player.coins = data.get("coins", 0)
            player.inventory = data.get("inventory", [None] * 25)
            player.weapon = data.get("weapon")
            player.weapon_bonus = data.get("weapon_bonus", 0)
            player.recalc_stats()


class TeamView:
    """Simple screen showing the player's moves and stats."""

    def __init__(self, font):
        self.font = font
        self.page = 0  # 0=moves, 1=stats

    def handle_event(self, event, player):
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_LEFT, pygame.K_RIGHT):
                self.page = 1 - self.page
            elif event.key in (pygame.K_RETURN, pygame.K_ESCAPE):
                return "close"
            elif event.key == pygame.K_u and self.page == 1:
                if player.weapon:
                    player.add_item(player.weapon)
                    player.weapon = None
                    player.weapon_bonus = 0
                    player.recalc_stats()
        return None

    def draw(self, surface, player):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        overlay.set_alpha(200)
        overlay.fill((0, 0, 0))
        surface.blit(overlay, (0, 0))
        if self.page == 0:
            title = self.font.render(f"{player.name}'s Moves", True, (255, 255, 255))
            surface.blit(title, (50, 50))
            lines = [
                "Slash - deal 4-6 damage",
                "Prepare - raise defense by 1",
            ]
            for i, txt in enumerate(lines):
                render = self.font.render(txt, True, (255, 255, 255))
                surface.blit(render, (50, 100 + i * 30))
            hint = self.font.render("Left/Right: Stats  Enter/Esc: Back", True, (200, 200, 200))
            surface.blit(hint, (50, SCREEN_HEIGHT - 50))
        else:
            title = self.font.render(f"{player.name} Lv.{player.level} Stats", True, (255, 255, 255))
            surface.blit(title, (50, 50))
            stats = [
                f"HP: {player.hp}/{player.max_hp}",
                f"XP: {player.xp}/{player.xp_to_next()}",
                f"Strength: {player.strength}",
                f"Defense: {player.defense}",
                f"Speed: {player.speed}",
            ]
            for i, line in enumerate(stats):
                render = self.font.render(line, True, (255, 255, 255))
                surface.blit(render, (50, 100 + i * 30))
            weapon = player.weapon if player.weapon else "-"
            wtxt = self.font.render(f"Weapon: {weapon}", True, (255, 255, 255))
            surface.blit(wtxt, (50, 250))
            hint = self.font.render("Left/Right: Moves  U: Unequip  Enter/Esc: Back", True, (200, 200, 200))
            surface.blit(hint, (50, SCREEN_HEIGHT - 50))


class LevelUpView:
    """Screen to allocate stat points after leveling."""

    def __init__(self, font):
        self.font = font
        self.options = ["Strength", "Defense", "Speed"]
        self.index = 0
        self.active = False

    def start(self):
        self.index = 0
        self.active = True

    def handle_event(self, event, player):
        if not self.active:
            return None
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_UP:
                self.index = (self.index - 1) % len(self.options)
            elif event.key == pygame.K_DOWN:
                self.index = (self.index + 1) % len(self.options)
            elif event.key == pygame.K_RETURN:
                stat = self.options[self.index].lower()
                if stat == "strength":
                    player.base_strength += 1
                elif stat == "defense":
                    player.base_defense += 1
                else:
                    player.base_speed += 1
                player.recalc_stats()
                player.stat_points -= 1
                self.active = False
                return "done"
        return None

    def draw(self, surface):
        if not self.active:
            return
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        overlay.set_alpha(200)
        overlay.fill((0, 0, 0))
        surface.blit(overlay, (0, 0))
        title = self.font.render("Level up! Choose a stat", True, (255, 255, 255))
        rect = title.get_rect(center=(SCREEN_WIDTH // 2, 150))
        surface.blit(title, rect)
        for i, opt in enumerate(self.options):
            color = (255, 255, 255) if i == self.index else (170, 170, 170)
            txt = self.font.render(opt, True, color)
            r = txt.get_rect(center=(SCREEN_WIDTH // 2, 220 + i * 40))
            surface.blit(txt, r)
        hint = self.font.render("Up/Down choose, Enter confirm", True, (200, 200, 200))
        hr = hint.get_rect(center=(SCREEN_WIDTH // 2, 380))
        surface.blit(hint, hr)


class BagView:
    """Inventory grid allowing item use or equip."""

    def __init__(self, font):
        self.font = font
        self.active = False
        self.index = 0

    def open(self):
        self.active = True
        self.index = 0

    def handle_event(self, event, player):
        if not self.active:
            return None
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.active = False
                return "close"
            elif event.key == pygame.K_LEFT:
                self.index = (self.index - 1) % 25
            elif event.key == pygame.K_RIGHT:
                self.index = (self.index + 1) % 25
            elif event.key == pygame.K_UP:
                self.index = (self.index - 5) % 25
            elif event.key == pygame.K_DOWN:
                self.index = (self.index + 5) % 25
            elif event.key == pygame.K_RETURN:
                item = player.inventory[self.index]
                if not item:
                    return None
                name = item["name"]
                itype = ITEMS[name]["type"]
                if itype == "weapon":
                    if player.weapon:
                        player.add_item(player.weapon)
                    player.weapon = name
                    player.weapon_bonus = 0
                    player.recalc_stats()
                    player.remove_item(self.index)
                elif itype == "potion":
                    if player.hp < player.max_hp:
                        player.hp = min(player.max_hp, player.hp + ITEMS[name]["heal"])
                        player.remove_item(self.index)
        return None

    def draw(self, surface, player):
        if not self.active:
            return
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        overlay.set_alpha(200)
        overlay.fill((0, 0, 0))
        surface.blit(overlay, (0, 0))
        def abbrev(name):
            if " " in name:
                return "".join(w[0] for w in name.split()).upper()
            caps = [c for c in name if c.isupper()]
            if len(caps) >= 2:
                return "".join(caps[:2])
            return name[:2].upper()
        start_x = 100
        start_y = 80
        for idx in range(25):
            x = start_x + (idx % 5) * 100
            y = start_y + (idx // 5) * 60
            rect = pygame.Rect(x, y, 90, 50)
            pygame.draw.rect(surface, (80, 80, 80), rect, 2)
            item = player.inventory[idx]
            if item:
                ab = abbrev(item['name'])
                txt = f"{ab}x{item['qty']}" if ITEMS[item['name']].get('stack') else ab
                render = self.font.render(txt, True, (255, 255, 255))
                surface.blit(render, (x + 5, y + 15))
            if idx == self.index:
                pygame.draw.rect(surface, (255, 255, 0), rect, 3)
        selected = player.inventory[self.index]
        if selected:
            full = f"{selected['name']} x{selected['qty']}" if ITEMS[selected['name']].get('stack') else selected['name']
            top = self.font.render(full, True, (255, 255, 255))
            surface.blit(top, (50, 30))
        hint = self.font.render("Arrows: move  Enter: use/equip  Esc: back", True, (200, 200, 200))
        surface.blit(hint, (50, SCREEN_HEIGHT - 40))


class ShopView:
    """Simple shop interface for buying items."""

    def __init__(self, font):
        self.font = font
        self.active = False
        self.index = 0
        self.items = ["ShortSword", "LongSword", "Health Potion"]

    def open(self):
        self.active = True
        self.index = 0

    def handle_event(self, event, player):
        if not self.active:
            return None
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.active = False
                return "close"
            elif event.key in (pygame.K_UP, pygame.K_DOWN):
                self.index = (self.index + (1 if event.key == pygame.K_DOWN else -1)) % len(self.items)
            elif event.key == pygame.K_RETURN:
                name = self.items[self.index]
                price = ITEMS[name]["price"]
                if player.coins >= price and player.add_item(name):
                    player.coins -= price
        return None

    def draw(self, surface, player):
        if not self.active:
            return
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        overlay.set_alpha(200)
        overlay.fill((0, 0, 0))
        surface.blit(overlay, (0, 0))
        title = self.font.render("Shop", True, (255, 255, 255))
        surface.blit(title, (50, 50))
        for i, name in enumerate(self.items):
            price = ITEMS[name]["price"]
            txt = f"{name} - {price}c"
            color = (255, 255, 255) if i == self.index else (170, 170, 170)
            render = self.font.render(txt, True, color)
            surface.blit(render, (50, 100 + i * 40))
        wallet = self.font.render(f"Coins: {player.coins}", True, (255, 255, 0))
        surface.blit(wallet, (50, SCREEN_HEIGHT - 60))
        hint = self.font.render("Up/Down select  Enter buy  Esc exit", True, (200, 200, 200))
        surface.blit(hint, (50, SCREEN_HEIGHT - 30))


class AnvilView:
    """Upgrade scraps or weapons."""

    def __init__(self, font):
        self.font = font
        self.active = False
        self.tab = 0  # 0 = scraps, 1 = smithing
        self.index = 0
        self.row = 1  # 0 = scrap counts, 1 = slots
        self.slots = [None] * 5
        self.scrap_type = None
        self.weapon_slots = []

    def open(self, player):
        self.active = True
        self.tab = 0
        self.index = 0
        self.row = 1
        self.slots = [None] * 5
        self.scrap_type = None
        self.weapon_slots = [None] * (3 if player.weapon == "LongSword" else 2)

    def handle_event(self, event, player):
        if not self.active:
            return None
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.return_items(player)
                self.active = False
                return "close"
            elif event.key in (pygame.K_TAB, pygame.K_LEFT, pygame.K_RIGHT):
                if event.key == pygame.K_TAB:
                    self.tab = 1 - self.tab
                    self.index = 0
                    self.row = 1
                elif event.key == pygame.K_LEFT:
                    if self.row == 0:
                        self.index = (self.index - 1) % 3
                    else:
                        self.index = (self.index - 1) % self.slot_count()
                elif event.key == pygame.K_RIGHT:
                    if self.row == 0:
                        self.index = (self.index + 1) % 3
                    else:
                        self.index = (self.index + 1) % self.slot_count()
            elif event.key in (pygame.K_UP, pygame.K_DOWN) and self.tab == 0:
                if event.key == pygame.K_UP and self.row == 1:
                    self.row = 0
                    self.index = 0
                elif event.key == pygame.K_DOWN and self.row == 0:
                    self.row = 1
                    self.index = 0
            elif event.key == pygame.K_RETURN and event.mod & pygame.KMOD_SHIFT:
                if self.tab == 0 and self.row == 0:
                    self.add_from_count(player, all=True)
                else:
                    self.shift_add(player)
            elif event.key == pygame.K_RETURN:
                if self.tab == 0 and self.row == 0:
                    self.add_from_count(player, all=False)
                else:
                    self.upgrade(player)
            elif event.key == pygame.K_BACKSPACE and self.row == 1:
                self.remove_slot(player)
        return None

    def slot_count(self):
        return 5 if self.tab == 0 else len(self.weapon_slots)

    def return_items(self, player):
        for i, item in enumerate(self.slots):
            if item:
                player.add_item(item)
                self.slots[i] = None
        for i, item in enumerate(self.weapon_slots):
            if item:
                player.add_item(item)
                self.weapon_slots[i] = None
        self.scrap_type = None

    def add_from_count(self, player, all=False):
        names = ["Scraps", "Good Scraps", "Elite Scraps"]
        scrap = names[self.index]
        added = False
        while True:
            if not player.take_item(scrap):
                break
            for i in range(5):
                if self.slots[i] is None:
                    self.slots[i] = scrap
                    self.scrap_type = scrap if self.scrap_type is None else self.scrap_type
                    added = True
                    break
            else:
                player.add_item(scrap)
                break
            if not all:
                break
        if not added:
            return

    def shift_add(self, player):
        if self.tab == 0:
            if self.scrap_type is None:
                for name in ("Scraps", "Good Scraps"):
                    if player.take_item(name):
                        self.scrap_type = name
                        for i in range(5):
                            if self.slots[i] is None:
                                self.slots[i] = name
                                return
                        player.add_item(name)
                        return
            else:
                if player.take_item(self.scrap_type):
                    for i in range(5):
                        if self.slots[i] is None:
                            self.slots[i] = self.scrap_type
                            return
                    player.add_item(self.scrap_type)
        else:
            for scrap in ("Elite Scraps", "Good Scraps", "Scraps"):
                if player.take_item(scrap):
                    for i in range(len(self.weapon_slots)):
                        if self.weapon_slots[i] is None:
                            self.weapon_slots[i] = scrap
                            return
                    player.add_item(scrap)
                    return

    def remove_slot(self, player):
        if self.tab == 0:
            if self.slots[self.index]:
                player.add_item(self.slots[self.index])
                self.slots[self.index] = None
                if not any(self.slots):
                    self.scrap_type = None
        else:
            if self.weapon_slots[self.index]:
                player.add_item(self.weapon_slots[self.index])
                self.weapon_slots[self.index] = None

    def upgrade(self, player):
        if self.tab == 0:
            if self.scrap_type and all(self.slots):
                result = "Good Scraps" if self.scrap_type == "Scraps" else "Elite Scraps"
                player.add_item(result)
                self.slots = [None] * 5
                self.scrap_type = None
        else:
            bonus = 0
            for scrap in self.weapon_slots:
                if scrap == "Scraps":
                    bonus += 1
                elif scrap == "Good Scraps":
                    bonus += 2
                elif scrap == "Elite Scraps":
                    bonus += 3
            if bonus:
                player.weapon_bonus += bonus
                player.recalc_stats()
                self.weapon_slots = [None] * len(self.weapon_slots)

    def draw(self, surface, player):
        if not self.active:
            return
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        overlay.set_alpha(200)
        overlay.fill((0, 0, 0))
        surface.blit(overlay, (0, 0))
        tabs = ["Scraps", "Smithing"]
        for i, name in enumerate(tabs):
            color = (255, 255, 255) if i == self.tab else (170, 170, 170)
            txt = self.font.render(name, True, color)
            surface.blit(txt, (50 + i * 120, 40))
        if self.tab == 0:
            counts = [
                player.count_item("Scraps"),
                player.count_item("Good Scraps"),
                player.count_item("Elite Scraps"),
            ]
            labels = ["Scraps", "Good", "Elite"]
            for i, lbl in enumerate(labels):
                clr = (255, 255, 0) if self.row == 0 and self.index == i else (255, 255, 255)
                txt = self.font.render(f"{lbl}: {counts[i]}", True, clr)
                surface.blit(txt, (SCREEN_WIDTH - 180, 80 + i * 30))
            for i in range(5):
                x = SCREEN_WIDTH // 2 - 110 + i * 55
                y = SCREEN_HEIGHT // 2
                rect = pygame.Rect(x, y, 40, 40)
                pygame.draw.rect(surface, (80, 80, 80), rect, 2)
                if self.slots[i]:
                    txt = self.font.render("S", True, (255, 255, 255))
                    rect2 = txt.get_rect(center=rect.center)
                    surface.blit(txt, rect2)
                if self.row == 1 and i == self.index:
                    pygame.draw.rect(surface, (255, 255, 0), rect, 2)
            if self.row == 0:
                hint = "Enter add  Shift+Enter fill  Up/Down switch"
            else:
                hint = "Enter upgrade  Backspace remove  Up/Down switch"
        else:
            start_x = SCREEN_WIDTH // 2 - len(self.weapon_slots) * 30
            for i in range(len(self.weapon_slots)):
                rect = pygame.Rect(start_x + i * 60, SCREEN_HEIGHT // 2, 40, 40)
                pygame.draw.rect(surface, (80, 80, 80), rect, 2)
                scrap = self.weapon_slots[i]
                if scrap:
                    txt = self.font.render("S", True, (255, 255, 255))
                    rect2 = txt.get_rect(center=rect.center)
                    surface.blit(txt, rect2)
                if i == self.index:
                    pygame.draw.rect(surface, (255, 255, 0), rect, 2)
            wtxt = self.font.render(f"Weapon: {player.weapon} +{player.weapon_bonus}", True, (255, 255, 255))
            surface.blit(wtxt, (50, 90))
            hint = "Shift+Enter add  Enter apply  Backspace remove"
        h = self.font.render(hint, True, (200, 200, 200))
        surface.blit(h, (50, SCREEN_HEIGHT - 40))


class Sign:
    def __init__(self, rect, text):
        self.rect = rect
        self.text = text


class Room:
    def __init__(self, color, encounter_rect=None, enemy_level=1, sign=None):
        self.color = color
        self.encounter_rect = encounter_rect
        self.enemy_level = enemy_level
        self.sign = sign


class Battle:
    def __init__(self, player, enemy, font, player_img, enemy_img, room_idx):
        self.player = player
        self.enemy = enemy
        self.font = font
        self.player_img = player_img
        self.enemy_img = enemy_img
        self.room_idx = room_idx
        self.menu_opts = ["Fight", "Bag", "Switch", "Run"]
        self.menu_index = 0
        self.move_index = 0
        self.state = "menu"  # menu, moves, message, enemy, victory, defeat, run
        self.next_state = "menu"
        self.message = ""
        self.msg_timer = 0
        self.victory_xp = 0
        self.victory_coins = 0
        self.victory_item = None
        self.orig_speed = player.speed
        self.slow_turns = 0

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
                self.state = self.next_state
                if self.state == "victory":
                    self.message = f"You won! Gained {self.victory_xp} XP and {self.victory_coins} coins."
                elif self.state == "defeat":
                    self.message = "You were defeated..."
        elif self.state in {"victory", "defeat", "run"}:
            if event.key == pygame.K_RETURN:
                if self.state == "victory" and self.victory_xp:
                    msg = f"You won! Gained {self.victory_xp} XP and {self.victory_coins} coins."
                    self.player.gain_xp(self.victory_xp)
                    self.player.coins += self.victory_coins
                    if self.victory_item:
                        if self.player.add_item(self.victory_item):
                            msg += f" Found {self.victory_item}!"
                        else:
                            msg += f" Couldn't carry {self.victory_item}."
                    self.message = msg
                    self.victory_xp = 0
                    self.victory_coins = 0
                    self.victory_item = None
                    self.state = "message"
                    self.msg_timer = 60
                    self.next_state = "end"
                    return
                self.state = "end"

    def player_move(self, name):
        if self.slow_turns > 0:
            self.slow_turns -= 1
            if self.slow_turns == 0:
                self.player.speed = self.orig_speed
        if name == "Prepare":
            self.player.defense += 1
            self.message = "You used Prepare!"
        else:  # Slash
            dmg = random.randint(4, 6) + self.player.strength - self.enemy.defense
            dmg = max(1, dmg)
            self.enemy.hp -= dmg
            self.message = f"You used Slash! {self.enemy.name} took {dmg} damage."
        if self.enemy.hp <= 0:
            self.next_state = "victory"
            self.victory_xp = self.enemy.xp
            drop = COIN_DROP.get(self.enemy.level, (self.enemy.level, self.enemy.level + 2))
            self.victory_coins = random.randint(*drop)
            self.victory_item = self.roll_drop()
        else:
            self.next_state = "enemy"
        self.state = "message"
        self.msg_timer = 60

    def enemy_move(self):
        move = random.choice(self.enemy.moves)
        if move == "Slime":
            dmg = random.randint(1, 2) + self.enemy.strength - self.player.defense
            dmg = max(1, dmg)
            self.player.hp -= dmg
            self.message = f"{self.enemy.name} used Slime! You took {dmg} damage."
            if self.slow_turns == 0:
                self.player.speed -= 1
            self.slow_turns = 2
        else:  # Scratch
            dmg = random.randint(2, 4) + self.enemy.strength - self.player.defense
            dmg = max(1, dmg)
            self.player.hp -= dmg
            self.message = f"{self.enemy.name} used Scratch! You took {dmg} damage."
        self.next_state = "defeat" if self.player.hp <= 0 else "menu"
        self.state = "message"
        self.msg_timer = 60

    def roll_drop(self):
        drops = ITEM_DROP.get(self.room_idx, [])
        for name, chance in drops:
            if random.random() < chance:
                return name
        return None

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
        label = f"{self.enemy.name} Lv.{self.enemy.level}"
        self.draw_bar(surface, SCREEN_WIDTH - 250, 130, self.enemy.hp, self.enemy.max_hp, label)
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


def select_mode(screen, font):
    """Ask the player to choose Regular or Hardcore mode."""
    options = ["Regular", "Hardcore"]
    idx = 0
    clock = pygame.time.Clock()
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_UP, pygame.K_DOWN):
                    idx = (idx + 1) % 2
                elif event.key == pygame.K_RETURN:
                    return idx == 1
        screen.fill((0, 0, 0))
        title = font.render("Select Mode", True, (255, 255, 255))
        trect = title.get_rect(center=(SCREEN_WIDTH // 2, 200))
        screen.blit(title, trect)
        for i, opt in enumerate(options):
            color = (255, 255, 255) if i == idx else (170, 170, 170)
            txt = font.render(opt, True, color)
            rect = txt.get_rect(center=(SCREEN_WIDTH // 2, 260 + i * 40))
            screen.blit(txt, rect)
        pygame.display.flip()
        clock.tick(60)


def main():
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Simple RPG")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont(None, 32)

    hardcore = select_mode(screen, font)

    player_imgs = []
    for data in CHARACTER_FRAMES_B64:
        img_bytes = base64.b64decode(data)
        player_imgs.append(pygame.image.load(BytesIO(img_bytes)).convert_alpha())
    player_img = player_imgs[0]
    enemy_img1 = pygame.Surface((32, 32))
    enemy_img1.fill((200, 0, 0))
    enemy_img2 = pygame.Surface((32, 32))
    enemy_img2.fill((0, 0, 200))
    enemy_img3 = pygame.Surface((32, 32))
    enemy_img3.fill((0, 200, 0))

    player = Player(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2, player_imgs)
    menu = Menu(font)
    team_view = TeamView(font)
    bag_view = BagView(font)
    shop_view = ShopView(font)
    anvil_view = AnvilView(font)
    levelup_view = LevelUpView(font)
    team_active = False
    bag_active = False
    shop_active = False
    anvil_active = False

    shop_rect = pygame.Rect(SCREEN_WIDTH // 2 - 40, SCREEN_HEIGHT - 120, 80, 80)
    anvil_rect = pygame.Rect(SCREEN_WIDTH // 2 + 60, SCREEN_HEIGHT - 120, 40, 40)
    rooms = [
        Room(
            (60, 120, 60),
            enemy_level=1,
            sign=Sign(pygame.Rect(SCREEN_WIDTH // 2 - 20, 40, 40, 30), "Route 1"),
        ),
        Room(
            (80, 100, 140),
            pygame.Rect(300, 200, 200, 200),
            enemy_level=1,
            sign=Sign(pygame.Rect(SCREEN_WIDTH // 2 - 60, 40, 120, 30), "Sewer Entrance"),
        ),
        Room(
            (100, 80, 120),
            pygame.Rect(250, 150, 300, 200),
            enemy_level=2,
        ),
    ]
    current_room = 0
    prev_pos = player.rect.topleft
    encounter_timer = 0
    encounter_threshold = random.randint(*ENCOUNTER_DELAY_RANGE)
    game_state = "map"
    battle = None
    running = True

    while running:
        keys = pygame.key.get_pressed()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE and game_state == "map":
                if team_active:
                    team_active = False
                    menu.show()
                elif menu.visible:
                    menu.hide()
                else:
                    menu.show()
            if levelup_view.active:
                levelup_view.handle_event(event, player)
                continue
            if game_state == "map" and not menu.visible and not team_active and not bag_active and not shop_active and not anvil_active:
                if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE and current_room == 0 and player.rect.colliderect(shop_rect):
                    shop_active = True
                    shop_view.open()
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE and current_room == 0 and player.rect.colliderect(anvil_rect):
                    anvil_active = True
                    anvil_view.open(player)
            if game_state == "map" and menu.visible and not team_active and not bag_active and not shop_active:
                action = menu.handle_event(event, player)
                if action == "team":
                    team_active = True
                elif action == "bag":
                    bag_active = True
                    bag_view.open()
            elif game_state == "map" and team_active:
                result = team_view.handle_event(event, player)
                if result == "close":
                    team_active = False
                    menu.show()
            elif game_state == "map" and bag_active:
                result = bag_view.handle_event(event, player)
                if result == "close":
                    bag_active = False
                    menu.show()
            elif game_state == "map" and shop_active:
                result = shop_view.handle_event(event, player)
                if result == "close":
                    shop_active = False
            elif game_state == "map" and anvil_active:
                result = anvil_view.handle_event(event, player)
                if result == "close":
                    anvil_active = False
            elif game_state == "battle" and battle:
                battle.handle_event(event)

        if game_state == "map" and not menu.visible and not team_active and not bag_active and not shop_active and not anvil_active:
            player.handle_input(keys)
            # Room transitions
            if current_room == 0 and player.rect.top < 0:
                current_room = 1
                player.rect.bottom = SCREEN_HEIGHT
            elif current_room == 1 and player.rect.bottom > SCREEN_HEIGHT:
                current_room = 0
                player.rect.top = 0
            elif current_room == 1 and player.rect.top < 0:
                current_room = 2
                player.rect.bottom = SCREEN_HEIGHT
            elif current_room == 2 and player.rect.bottom > SCREEN_HEIGHT:
                current_room = 1
                player.rect.top = 0
            # Encounter check
            room = rooms[current_room]
            if room.encounter_rect and room.encounter_rect.colliderect(player.rect):
                if player.rect.topleft != prev_pos:
                    encounter_timer += 1
                    if encounter_timer >= encounter_threshold and random.random() < ENCOUNTER_RATE:
                        if current_room == 2:
                            name = "Gremlin"
                        else:
                            name = random.choice(["Slime", "Bat"])
                        lvl = room.enemy_level + (1 if hardcore else 0)
                        enemy = create_enemy(name, lvl)
                        if name == "Slime":
                            enemy_img = enemy_img1
                        elif name == "Bat":
                            enemy_img = enemy_img2
                        else:
                            enemy_img = enemy_img3
                        battle = Battle(player, enemy, font, player_img, enemy_img, current_room)
                        fade(screen, True)
                        game_state = "battle"
                        encounter_timer = 0
                        encounter_threshold = random.randint(*ENCOUNTER_DELAY_RANGE)
            else:
                encounter_timer = 0
                encounter_threshold = random.randint(*ENCOUNTER_DELAY_RANGE)
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
                player.recalc_stats()
                if player.stat_points > 0:
                    levelup_view.start()

        if game_state == "map":
            menu.update()
            room = rooms[current_room]
            screen.fill(room.color)
            if room.encounter_rect:
                pygame.draw.rect(screen, (40, 80, 40), room.encounter_rect)
            if current_room == 0:
                pygame.draw.rect(screen, (200, 200, 50), shop_rect)
                pygame.draw.rect(screen, (120, 120, 120), anvil_rect)
            if room.sign:
                pygame.draw.rect(screen, (150, 100, 50), room.sign.rect)
                if player.rect.colliderect(room.sign.rect):
                    txt = font.render(room.sign.text, True, (255, 255, 255))
                    rect = txt.get_rect(center=(room.sign.rect.centerx, room.sign.rect.top - 10))
                    pygame.draw.rect(screen, (0, 0, 0), rect.inflate(8, 8))
                    screen.blit(txt, rect)
            screen.blit(player.image, player.rect)
            menu.draw(screen, player)
            if team_active:
                team_view.draw(screen, player)
            if bag_active:
                bag_view.draw(screen, player)
            if shop_active:
                shop_view.draw(screen, player)
            if anvil_active:
                anvil_view.draw(screen, player)
            if levelup_view.active:
                levelup_view.draw(screen)
        elif game_state == "battle" and battle:
            battle.draw(screen)

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()


if __name__ == "__main__":
    main()
