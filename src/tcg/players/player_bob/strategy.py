"""Bob Player の戦略ロジック."""

from tcg.config import fortress_limit


class Strategy:
    """戦略クラス - 複数ファイル構成の例として戦略を分離."""

    def __init__(self):
        self.step = 0

    def should_upgrade(self, fortress_state) -> bool:
        """
        要塞をアップグレードすべきか判定.

        Args:
            fortress_state: [team, kind, level, pawn_number, upgrade_time, [to_set]]

        Returns:
            bool: アップグレードすべきならTrue
        """
        team, kind, level, pawn_number, upgrade_time, to_set = fortress_state

        # アップグレード条件をチェック
        if upgrade_time != 0:
            return False

        # レベル5は最大なのでアップグレード不要
        if level >= 5:
            return False

        # 必要な部隊数の1.5倍以上あればアップグレード
        required = fortress_limit[level] // 2
        return pawn_number >= required * 1.5

    def find_attack_target(self, state, fortress_id):
        """
        攻撃対象を探す.

        Args:
            state: 全要塞の状態
            fortress_id: 自分の要塞ID

        Returns:
            int or None: 攻撃対象の要塞ID、なければNone
        """
        my_fortress = state[fortress_id]
        neighbors = my_fortress[5]

        # 隣接要塞を評価（敵 > 中立の優先順位）
        enemy_neighbors = []
        neutral_neighbors = []

        for n in neighbors:
            neighbor_team = state[n][0]
            if neighbor_team == 2:  # 敵
                enemy_neighbors.append((n, state[n][3]))  # (ID, 部隊数)
            elif neighbor_team == 0:  # 中立
                neutral_neighbors.append((n, state[n][3]))

        # 敵要塞がある場合、最も弱い敵を狙う
        if enemy_neighbors:
            enemy_neighbors.sort(key=lambda x: x[1])  # 部隊数で昇順ソート
            return enemy_neighbors[0][0]

        # 中立要塞がある場合、最も弱い中立を狙う
        if neutral_neighbors:
            neutral_neighbors.sort(key=lambda x: x[1])
            return neutral_neighbors[0][0]

        return None

    def find_strongest_fortress(self, state):
        """
        自分の要塞の中で最も部隊数が多い要塞を探す.

        Args:
            state: 全要塞の状態

        Returns:
            tuple: (fortress_id, pawn_count) or (None, 0)
        """
        my_fortresses = [(i, state[i][3]) for i in range(12) if state[i][0] == 1]

        if not my_fortresses:
            return None, 0

        strongest = max(my_fortresses, key=lambda x: x[1])
        return strongest

    def evaluate_state(self, state):
        """
        ゲーム状態を評価（デバッグやログ用）.

        Args:
            state: 全要塞の状態

        Returns:
            dict: 評価結果
        """
        my_fortresses = [i for i in range(12) if state[i][0] == 1]
        enemy_fortresses = [i for i in range(12) if state[i][0] == 2]
        neutral_fortresses = [i for i in range(12) if state[i][0] == 0]

        my_total_pawns = sum(state[i][3] for i in my_fortresses)
        enemy_total_pawns = sum(state[i][3] for i in enemy_fortresses)

        return {
            "my_fortress_count": len(my_fortresses),
            "enemy_fortress_count": len(enemy_fortresses),
            "neutral_fortress_count": len(neutral_fortresses),
            "my_total_pawns": my_total_pawns,
            "enemy_total_pawns": enemy_total_pawns,
        }
