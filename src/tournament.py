"""
Tournament Script

src/tcg/players/ ディレクトリ内の全AIプレイヤーを自動検出してトーナメントを実行します。

実行方法:
    cd src
    uv run python tournament.py

オプション:
    - トーナメント形式: TOURNAMENT_MODE = "swiss" または "round_robin"
    - ウィンドウ表示: ENABLE_WINDOW を True/False に設定
    - スイス式ラウンド数: SWISS_ROUNDS を変更
"""

from collections import defaultdict
from itertools import combinations
import random

import pygame

from tcg.controller import Controller
from tcg.game import Game
from tcg.players import discover_players

# トーナメント設定
TOURNAMENT_MODE = "swiss"  # "swiss" または "round_robin"
SWISS_ROUNDS = None  # None の場合は自動計算（ceil(log2(player_count)) * 2）
MATCHES_PER_PAIR = 2  # 各対戦カードで実行する試合数（round_robin用）
ENABLE_WINDOW = False  # ウィンドウ表示の有効/無効


def run_match(
    player1: Controller, player2: Controller, match_id: int = 1, window: bool = True
) -> dict:
    """
    1試合を実行して結果を返す

    Args:
        player1: プレイヤー1（青/下側）
        player2: プレイヤー2（赤/上側）
        match_id: 試合番号
        window: ウィンドウ表示の有効/無効

    Returns:
        dict: 試合結果
            - winner: "Blue" | "Red" | "Both"
            - blue_fortresses: 青チームの要塞数
            - red_fortresses: 赤チームの要塞数
            - steps: 総ステップ数
    """
    game = Game(player1, player2, window=window)
    game.run()

    result = {
        "winner": game.win_team,
        "blue_fortresses": game.Blue_fortress,
        "red_fortresses": game.Red_fortress,
        "steps": game.step,
    }

    if not window:
        print(
            f"  Match {match_id}: {game.win_team} Win! "
            f"(Blue: {game.Blue_fortress}, Red: {game.Red_fortress}, Steps: {game.step})"
        )

    return result


def calculate_swiss_rounds(player_count: int) -> int:
    """スイス式トーナメントのラウンド数を計算"""
    import math
    return max(3, math.ceil(math.log2(player_count)) * 2)


def pair_swiss_round(
    players_with_scores: list[dict], round_num: int, played_pairs: set
) -> list[tuple]:
    """
    スイス式のペアリング を実行

    Args:
        players_with_scores: プレイヤーと現在のスコアのリスト
        round_num: ラウンド番号
        played_pairs: 既に対戦した(player_i, player_j)のセット

    Returns:
        list[tuple]: (player_idx_1, player_idx_2)のペアリストのリスト
    """
    # スコアでソート（降順）
    sorted_players = sorted(
        players_with_scores,
        key=lambda x: (x["score"], x["wins"], x["avg_fortresses"]),
        reverse=True,
    )

    # プレイヤーインデックスを保持
    player_indices = [p["original_idx"] for p in sorted_players]

    pairs = []
    used = set()

    for i, player_idx in enumerate(player_indices):
        if player_idx in used:
            continue

        # 同じスコア帯のプレイヤーを探す
        current_score = sorted_players[i]["score"]
        for j in range(i + 1, len(player_indices)):
            opponent_idx = player_indices[j]
            if opponent_idx in used:
                continue

            opponent_score = sorted_players[j]["score"]

            # スコア差が大きすぎない、かつまだ対戦していない場合
            if abs(current_score - opponent_score) <= 3:
                pair = tuple(sorted([player_idx, opponent_idx]))
                if pair not in played_pairs:
                    pairs.append((player_idx, opponent_idx))
                    used.add(player_idx)
                    used.add(opponent_idx)
                    break

        # マッチングできなかった場合、最初の未使用プレイヤーと対戦
        if player_idx not in used:
            for j in range(i + 1, len(player_indices)):
                opponent_idx = player_indices[j]
                if opponent_idx not in used:
                    pair = tuple(sorted([player_idx, opponent_idx]))
                    if pair not in played_pairs:
                        pairs.append((player_idx, opponent_idx))
                        used.add(player_idx)
                        used.add(opponent_idx)
                        break

    return pairs


def run_swiss_tournament(
    players: list[type[Controller]], rounds: int = None, window: bool = True
):
    """
    スイス式トーナメントを実行

    Args:
        players: プレイヤークラスのリスト
        rounds: ラウンド数（Noneの場合は自動計算）
        window: ウィンドウ表示の有効/無効
    """
    if len(players) < 2:
        print("エラー: 最低2人のプレイヤーが必要です")
        return

    if rounds is None:
        rounds = calculate_swiss_rounds(len(players))

    print("=" * 70)
    print("要塞征服ゲーム スイス式トーナメント")
    print("=" * 70)
    print(f"\n参加プレイヤー: {len(players)}人")
    for i, player_class in enumerate(players, 1):
        player = player_class()
        print(f"  {i}. {player.team_name()} ({player_class.__name__})")

    print(f"\nラウンド数: {rounds}")
    expected_matches = rounds * (len(players) // 2)
    print(f"予定試合数（約）: {expected_matches}試合")
    print(f"ビジュアライゼーション: {'ON' if window else 'OFF'}")
    print("=" * 70)

    # プレイヤー情報の初期化
    player_stats = {}
    player_classes = {}
    for idx, player_class in enumerate(players):
        player = player_class()
        player_name = player.team_name()
        player_stats[player_name] = {
            "wins": 0,
            "draws": 0,
            "losses": 0,
            "matches": 0,
            "total_fortresses": 0,
            "original_idx": idx,
        }
        player_classes[player_name] = player_class

    played_pairs = set()
    match_count = 0

    # 各ラウンドを実行
    for round_num in range(1, rounds + 1):
        print(f"\n【ラウンド {round_num}】")

        # スコア計算
        players_with_scores = []
        for player_name, stats in player_stats.items():
            score = stats["wins"] * 3 + stats["draws"]
            avg_fortresses = (
                stats["total_fortresses"] / stats["matches"]
                if stats["matches"] > 0
                else 0
            )
            players_with_scores.append(
                {
                    "name": player_name,
                    "score": score,
                    "wins": stats["wins"],
                    "avg_fortresses": avg_fortresses,
                    "original_idx": stats["original_idx"],
                }
            )

        # ペアリング
        pairs = pair_swiss_round(players_with_scores, round_num, played_pairs)

        if not pairs:
            print("  対戦ペアが見つかりません")
            break

        # 各ペアの対戦を実行
        for player1_name_idx, player2_name_idx in pairs:
            # インデックスからプレイヤーを取得
            player1_name = next(
                name
                for name, stats in player_stats.items()
                if stats["original_idx"] == player1_name_idx
            )
            player2_name = next(
                name
                for name, stats in player_stats.items()
                if stats["original_idx"] == player2_name_idx
            )

            print(f"  {player1_name} vs {player2_name}")

            # 対戦実行
            result = run_match(
                player_classes[player1_name](),
                player_classes[player2_name](),
                match_count + 1,
                window=window,
            )
            match_count += 1

            # 統計更新
            player_stats[player1_name]["matches"] += 1
            player_stats[player2_name]["matches"] += 1
            player_stats[player1_name]["total_fortresses"] += result["blue_fortresses"]
            player_stats[player2_name]["total_fortresses"] += result["red_fortresses"]

            if result["winner"] == "Blue":
                player_stats[player1_name]["wins"] += 1
                player_stats[player2_name]["losses"] += 1
            elif result["winner"] == "Red":
                player_stats[player2_name]["wins"] += 1
                player_stats[player1_name]["losses"] += 1
            else:
                player_stats[player1_name]["draws"] += 1
                player_stats[player2_name]["draws"] += 1

            # 既に対戦したペアを記録
            played_pairs.add(
                tuple(sorted([player_stats[player1_name]["original_idx"],
                             player_stats[player2_name]["original_idx"]]))
            )

    # 最終結果表示
    print("\n" + "=" * 70)
    print("トーナメント結果")
    print("=" * 70)

    rankings = []
    for player_name, stats in player_stats.items():
        score = stats["wins"] * 3 + stats["draws"]
        win_rate = stats["wins"] / stats["matches"] * 100 if stats["matches"] > 0 else 0
        avg_fortresses = (
            stats["total_fortresses"] / stats["matches"] if stats["matches"] > 0 else 0
        )
        rankings.append(
            {
                "name": player_name,
                "score": score,
                "wins": stats["wins"],
                "draws": stats["draws"],
                "losses": stats["losses"],
                "matches": stats["matches"],
                "win_rate": win_rate,
                "avg_fortresses": avg_fortresses,
            }
        )

    rankings.sort(key=lambda x: (x["score"], x["wins"], x["avg_fortresses"]), reverse=True)

    print(
        f"\n{'順位':<4} {'プレイヤー名':<20} {'スコア':<6} {'勝':<4} {'分':<4} {'敗':<4} "
        f"{'勝率':<8} {'平均要塞数':<10}"
    )
    print("-" * 70)
    for rank, player in enumerate(rankings, 1):
        print(
            f"{rank:<4} "
            f"{player['name']:<20} "
            f"{player['score']:<6} "
            f"{player['wins']:<4} "
            f"{player['draws']:<4} "
            f"{player['losses']:<4} "
            f"{player['win_rate']:>6.1f}% "
            f"{player['avg_fortresses']:>10.2f}"
        )

    print("\n" + "=" * 70)
    print(f"総試合数: {match_count}試合")
    print("=" * 70)


def run_round_robin_tournament(
    players: list[type[Controller]], matches_per_pair: int = 2, window: bool = True
):
    """
    総当たり戦トーナメントを実行

    Args:
        players: プレイヤークラスのリスト
        matches_per_pair: 各対戦で実行する試合数
        window: ウィンドウ表示の有効/無効
    """
    if len(players) < 2:
        print("エラー: 最低2人のプレイヤーが必要です")
        print(f"現在のプレイヤー数: {len(players)}")
        return

    print("=" * 70)
    print("要塞征服ゲーム 総当たり戦トーナメント")
    print("=" * 70)
    print(f"\n参加プレイヤー: {len(players)}人")
    for i, player_class in enumerate(players, 1):
        player = player_class()
        print(f"  {i}. {player.team_name()} ({player_class.__name__})")

    print(f"\n各対戦: {matches_per_pair}試合")
    print(f"総試合数: {len(list(combinations(range(len(players)), 2))) * matches_per_pair}試合")
    print(f"ビジュアライゼーション: {'ON' if window else 'OFF'}")
    print("=" * 70)

    # 統計情報を記録
    stats = defaultdict(
        lambda: {"wins": 0, "losses": 0, "draws": 0, "total_fortresses": 0, "matches": 0}
    )

    # 総当たり戦
    match_count = 0
    for i, j in combinations(range(len(players)), 2):
        player1_class = players[i]
        player2_class = players[j]

        player1_name = player1_class().team_name()
        player2_name = player2_class().team_name()

        print(f"\n【{player1_name} vs {player2_name}】")

        # 複数回対戦
        for round_num in range(1, matches_per_pair + 1):
            print(f"  Match {round_num}: {player1_name} vs {player2_name}")
            result = run_match(player1_class(), player2_class(), match_count + 1, window=window)
            match_count += 1

            # 統計更新
            stats[player1_name]["matches"] += 1
            stats[player2_name]["matches"] += 1
            stats[player1_name]["total_fortresses"] += result["blue_fortresses"]
            stats[player2_name]["total_fortresses"] += result["red_fortresses"]

            if result["winner"] == "Blue":
                stats[player1_name]["wins"] += 1
                stats[player2_name]["losses"] += 1
            elif result["winner"] == "Red":
                stats[player2_name]["wins"] += 1
                stats[player1_name]["losses"] += 1
            else:
                stats[player1_name]["draws"] += 1
                stats[player2_name]["draws"] += 1

    # 結果表示
    print("\n" + "=" * 70)
    print("トーナメント結果")
    print("=" * 70)

    # スコア計算（勝ち=3点、引き分け=1点、負け=0点）
    rankings = []
    for player_name, data in stats.items():
        score = data["wins"] * 3 + data["draws"] * 1
        win_rate = data["wins"] / data["matches"] * 100 if data["matches"] > 0 else 0
        avg_fortresses = data["total_fortresses"] / data["matches"] if data["matches"] > 0 else 0
        rankings.append(
            {
                "name": player_name,
                "score": score,
                "wins": data["wins"],
                "draws": data["draws"],
                "losses": data["losses"],
                "matches": data["matches"],
                "win_rate": win_rate,
                "avg_fortresses": avg_fortresses,
            }
        )

    # スコア順にソート
    rankings.sort(key=lambda x: (x["score"], x["wins"], x["avg_fortresses"]), reverse=True)

    # ランキング表示
    print(
        f"\n{'順位':<4} {'プレイヤー名':<20} {'スコア':<6} {'勝':<4} {'分':<4} {'敗':<4} "
        f"{'勝率':<8} {'平均要塞数':<10}"
    )
    print("-" * 70)
    for rank, player in enumerate(rankings, 1):
        print(
            f"{rank:<4} "
            f"{player['name']:<20} "
            f"{player['score']:<6} "
            f"{player['wins']:<4} "
            f"{player['draws']:<4} "
            f"{player['losses']:<4} "
            f"{player['win_rate']:>6.1f}% "
            f"{player['avg_fortresses']:>10.2f}"
        )

    print("\n" + "=" * 70)
    print(f"総試合数: {match_count}試合")
    print("=" * 70)


def main():
    """メイン関数"""
    # プレイヤーを収集
    players = []

    # src/tcg/players/ から自動検出
    discovered_players = discover_players()
    players.extend(discovered_players)
    print(f"発見したプレイヤー: {len(discovered_players)}人")

    if len(players) == 0:
        print("\nエラー: プレイヤーが見つかりませんでした")
        print("src/tcg/players/ ディレクトリに player_*.py ファイルを作成してください")
        print("詳細は src/tcg/players/README.md を参照")
        return

    # トーナメント実行
    if TOURNAMENT_MODE == "swiss":
        run_swiss_tournament(players, rounds=SWISS_ROUNDS, window=ENABLE_WINDOW)
    elif TOURNAMENT_MODE == "round_robin":
        run_round_robin_tournament(players, matches_per_pair=MATCHES_PER_PAIR, window=ENABLE_WINDOW)
    else:
        print(f"エラー: 不明なトーナメント形式: {TOURNAMENT_MODE}")
        return

    # Pygameの終了処理
    if ENABLE_WINDOW:
        pygame.quit()


if __name__ == "__main__":
    main()
