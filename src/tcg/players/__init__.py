"""
AI Players Module

This module automatically discovers and imports all player classes
from Python files in this directory.

To add a new player:
1. Create a new file (e.g., player_yourname.py)
2. Define a class that inherits from Controller
3. Implement team_name() and update() methods
4. Your player will be automatically discovered
"""

import importlib
import inspect
from pathlib import Path

from ..controller import Controller


def discover_players() -> list[type[Controller]]:
    """
    Automatically discover all Controller subclasses in this directory.

    Supports both single-file players (player_*.py) and directory-based players (player_*/).

    Returns:
        List of Controller subclass types found in player files
    """
    players = []
    current_dir = Path(__file__).parent

    # 1. Find all Python files except __init__.py and template
    for file_path in current_dir.glob("*.py"):
        if file_path.name in ["__init__.py", "template_player.py"]:
            continue

        # Import the module
        module_name = f"tcg.players.{file_path.stem}"
        try:
            module = importlib.import_module(module_name)

            # Find all Controller subclasses in the module
            for name, obj in inspect.getmembers(module, inspect.isclass):
                if issubclass(obj, Controller) and obj is not Controller:
                    players.append(obj)
        except Exception as e:
            print(f"Warning: Failed to load {file_path.name}: {e}")

    # 2. Find all directories starting with "player_"
    for dir_path in current_dir.iterdir():
        if not dir_path.is_dir():
            continue
        if not dir_path.name.startswith("player_"):
            continue
        if dir_path.name == "__pycache__":
            continue

        # Check if __init__.py exists
        init_file = dir_path / "__init__.py"
        if not init_file.exists():
            print(f"Warning: {dir_path.name}/ has no __init__.py, skipping")
            continue

        # Import the package
        module_name = f"tcg.players.{dir_path.name}"
        try:
            module = importlib.import_module(module_name)

            # Find all Controller subclasses in the module
            for name, obj in inspect.getmembers(module, inspect.isclass):
                if issubclass(obj, Controller) and obj is not Controller:
                    players.append(obj)
        except Exception as e:
            print(f"Warning: Failed to load {dir_path.name}/: {e}")

    return players


# Export the discovery function
__all__ = ["discover_players"]
