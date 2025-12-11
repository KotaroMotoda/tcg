import pygame

from tcg.game import Game
from tcg.players.sample_random import RandomPlayer
from tcg.players.claude_player import ClaudePlayer
from tcg.players.created_player import CreatedPlayer

if __name__ == "__main__":
    # CreatedPlayer vs RandomPlayer で対戦
    print("=== CreatedPlayer (Blue) vs RandomPlayer (Red) ===")

    # デフォルト: ウィンドウ表示あり
    Game(CreatedPlayer(), RandomPlayer()).run()

    # ウィンドウ表示なし（高速実行）の場合:
    #Game(CreatedPlayer(), RandomPlayer(), window=False).run()

    pygame.quit()
