import pygame

from tcg.game import Game
from tcg.players.claude_player import RandomPlayer
from tcg.players.taisei import Genalplayermk2ver2

if __name__ == "__main__":
    # ClaudePlayer vs RandomPlayer で対戦
    print("=== ClaudePlayer (Blue) vs RandomPlayer (Red) ===")

    # デフォルト: ウィンドウ表示あり
    Game(Genalplayermk2ver2(), RandomPlayer()).run()

    # ウィンドウ表示なし（高速実行）の場合:
    #Game(ClaudePlayer(), RandomPlayer(), window=False).run()

    pygame.quit()
