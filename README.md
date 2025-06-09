# GAME1

This is a basic RPG prototype using `pygame`.

## Requirements
- Python 3.12
- `pygame` (install with `pip install pygame`)

## Running the game
Execute:
```bash
python3 main.py
```

Use the arrow keys to move. Hold `Shift` to run. Press `Esc` to open or close
the pause menu.

### Pause menu options
- **Return to Game**: Close the menu
- **Options**: Not implemented yet
- **Bag**: View inventory and use items or equip weapons
- **Team**: View Devon's moves and stats and unequip gear
- **Save Game**: Saves player position to `savegame.json`
- **Load Game**: Restores position from `savegame.json` if it exists
- **Quit Game**: Exit

### Gameplay
Three rooms are available. Walk north from the first area to reach the second
and again to reach the third. Rooms two and three contain darker zones where
random encounters may happen. The encounter rate defaults to 40% but can be
tweaked via the `ENCOUNTER_RATE` constant in `main.py`.

When an encounter occurs the screen fades to a simple battle screen. The
interface shows the player and enemy HP along with a menu containing **Fight**,
**Bag**, **Switch**, and **Run**. Enemies display their level next to their name.
After victory you earn experience and coins based on enemy level. Coins can be
spent at the shop in the starting area (press `Space` while standing on the
yellow square). The Bag screen lets you equip swords or drink health potions.
Items stack up to five in a slot.

### Leveling
Defeating enemies grants experience based on their level. When enough XP is
gained your character levels up, increasing max HP by 1–2 and awarding a stat
point. After each level up a screen will prompt you to raise either Strength,
Defense, or Speed.

At startup you can select **Regular** or **Hardcore** mode. Hardcore boosts all

Coins are displayed in the pause menu. Visit the shop in the first room to
purchase a ShortSword (+1 strength), LongSword (+3 strength, -1 speed) or Health
Potions.
enemies by one level, making battles tougher but yielding more XP.