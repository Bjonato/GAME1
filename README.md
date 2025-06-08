# GAME1

This is a very basic starting point for an RPG-style game using `pygame`.

## Requirements
- Python 3.12
- `pygame` (install with `pip install pygame`)

## Running the game
Execute the following command:

```bash
python3 main.py
```

Use the arrow keys to move the character. Hold `Shift` to run. Press `Esc` to open or close the menu.

Menu options:
- **Return to Game**: Close the menu
- **Options**: Placeholder
- **Team**: Placeholder
- **Bag**: Placeholder
- **Save Game**: Saves player position to `savegame.json`
- **Load Game**: Loads player position from `savegame.json` if it exists
- **Quit Game**: Exit the game

This setup is intentionally simple so you can expand it with new features.
The character sprite is embedded directly in `main.py` using Base64 so no
binary assets are required.
