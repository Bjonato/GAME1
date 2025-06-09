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
- **Options**, **Team**, **Bag**: Not implemented yet
- **Save Game**: Saves player position to `savegame.json`
- **Load Game**: Restores position from `savegame.json` if it exists
- **Quit Game**: Exit

### Gameplay
Two rooms are available. Walk up through the top edge of the first area to
enter the second room. The second room contains a darker zone in the middle
where random encounters may happen. The encounter rate defaults to 40% but can
be tweaked via the `ENCOUNTER_RATE` constant in `main.py`.

When an encounter occurs the screen fades to a simple battle screen. The
interface shows the player and enemy HP along with a menu containing **Fight**,
**Bag**, **Switch**, and **Run**. For now only **Fight** (with two moves) and
**Run** work. This is a small foundation for further expansion. The character
sprite is embedded directly in `main.py` using Base64 so no binary assets are
required.
