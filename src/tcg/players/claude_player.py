"""
AI Player

戦略的に考えて行動する強いAIプレイヤー
Claudeが作りました
"""

from tcg.config import fortress_cool, fortress_limit
from tcg.controller import Controller


class RandomPlayer(Controller):
    """
    戦略的AIプレイヤー

    作戦優先順位:
    1. アップグレード
    2. 両端を取る（要塞 0,1,2,9,10,11）
    3. 真ん中を取る（要塞 4,7）- ただし両端を全て取得後のみ

    条件ルール:
    - 上限値の90%を超えたら絶対送り出す
    - 自分の拠点の値が15を切ったら送り出して支援する
    """

    FORTRESS_IMPORTANCE = {
        0: 3, 1: 4, 2: 3,      # 両端
        3: 6, 4: 10, 5: 6,     # 中央上
        6: 6, 7: 10, 8: 6,     # 中央下
        9: 3, 10: 4, 11: 3     # 両端
    }

    END_FORTRESSES = {0, 1, 2, 9, 10, 11}      # 両端の要塞
    MIDDLE_FORTRESSES = {4, 7}                  # 真ん中の要塞

    def __init__(self) -> None:
        super().__init__()
        self.step = 0

    def team_name(self) -> str:
        return "Strategic"

    def estimate_attack_success(self, attacker_troops: float, defender_troops: float,
                                defender_level: int, defender_kind: int, travel_time: int) -> bool:
        """攻撃が成功するか予測"""
        attacking_force = attacker_troops / 2
        production_rate = fortress_cool[defender_kind][defender_level]
        
        if production_rate > 0:
            additional_troops = travel_time / production_rate
        else:
            additional_troops = 0

        total_defense = defender_troops + additional_troops
        damage = attacking_force * 0.8

        return damage > total_defense * 1.2

    def are_all_ends_captured(self, state) -> bool:
        """両端の要塞がすべて自分の領土か確認"""
        return all(state[fort][0] == 1 for fort in self.END_FORTRESSES)

    def update(self, info) -> tuple[int, int, int]:
        """戦略的な判断でコマンドを選択"""
        team, state, moving_pawns, spawning_pawns, done = info
        self.step += 1

        my_fortresses = [i for i in range(12) if state[i][0] == 1]
        actions = []

        all_ends_captured = self.are_all_ends_captured(state)

        # === ルール1: 上限値の99%を超えたら絶対送り出す（レベル3,4,5） ===
        for my_fort in my_fortresses:
            level = state[my_fort][2]
            troops = state[my_fort][3]
            limit = fortress_limit[level]

            # レベル3,4,5のときのみ適用
            if level >= 3 and troops >= limit * 0.99:
                neighbors = state[my_fort][5]
                # 敵 > 中立の優先順で探す
                enemy_neighbors = [n for n in neighbors if state[n][0] == 2]
                neutral_neighbors = [n for n in neighbors if state[n][0] == 0]
                
                targets = enemy_neighbors + neutral_neighbors
                if targets:
                    priority = 300  # 最優先
                    actions.append((priority, 1, my_fort, targets[0]))

        # === ルール1.5: 上限値に達したら隣接の味方要塞へ送り出す ===
        for my_fort in my_fortresses:
            level = state[my_fort][2]
            troops = state[my_fort][3]
            limit = fortress_limit[level]

            if troops >= limit:  # 上限値に達した
                neighbors = state[my_fort][5]
                # 隣接している味方要塞で上限に達していないところを探す
                support_targets = [n for n in neighbors 
                                  if state[n][0] == 1 and state[n][3] < fortress_limit[state[n][2]]]
                
                if support_targets:
                    priority = 290
                    actions.append((priority, 1, my_fort, support_targets[0]))

        # === 優先度1: アップグレード ===
        for my_fort in my_fortresses:
            level = state[my_fort][2]
            troops = state[my_fort][3]
            limit = fortress_limit[level]

            if state[my_fort][4] == -1 and level <= 4:
                if troops >= limit * 0.7:
                    priority = 250
                    actions.append((priority, 2, my_fort, 0))

        # === ルール2: 自分の拠点の値が15を切ったら支援する ===
        # 敵に隣接していて部隊が15未満の要塞のみ支援対象
        for my_fort in my_fortresses:
            neighbors = state[my_fort][5]
            is_under_threat = any(state[n][0] == 2 for n in neighbors)
            
            if state[my_fort][3] < 15 and is_under_threat:
                # 隣接している強い味方要塞から支援を送る
                # 支援元は送出後も20以上残る必要がある
                support_sources = [n for n in neighbors 
                                  if state[n][0] == 1 and state[n][3] >= 25]
                
                for source in support_sources:
                    priority = 220
                    actions.append((priority, 1, source, my_fort))

        # === 優先度2: 両端を取る ===
        for my_fort in my_fortresses:
            neighbors = state[my_fort][5]
            for neighbor in neighbors:
                if neighbor in self.END_FORTRESSES and state[neighbor][0] != 1:
                    if self.estimate_attack_success(
                        state[my_fort][3],
                        state[neighbor][3],
                        state[neighbor][2],
                        state[neighbor][1],
                        100
                    ):
                        priority = 200
                        actions.append((priority, 1, my_fort, neighbor))

        # === 優先度3: 真ん中を取る（両端を全て取得後のみ） ===
        if all_ends_captured:
            for my_fort in my_fortresses:
                neighbors = state[my_fort][5]
                for neighbor in neighbors:
                    if neighbor in self.MIDDLE_FORTRESSES and state[neighbor][0] != 1:
                        if self.estimate_attack_success(
                            state[my_fort][3],
                            state[neighbor][3],
                            state[neighbor][2],
                            state[neighbor][1],
                            100
                        ):
                            priority = 180
                            actions.append((priority, 1, my_fort, neighbor))

        # === その他の中立要塞を取る（両端取得後） ===
        if all_ends_captured:
            for my_fort in my_fortresses:
                neighbors = state[my_fort][5]
                for neighbor in neighbors:
                    if state[neighbor][0] == 0 and state[neighbor][3] <= 20:
                        if self.estimate_attack_success(
                            state[my_fort][3],
                            state[neighbor][3],
                            state[neighbor][2],
                            state[neighbor][1],
                            100
                        ):
                            priority = 170
                            actions.append((priority, 1, my_fort, neighbor))

        if actions:
            actions.sort(reverse=True, key=lambda x: x[0])
            _, command, subject, to = actions[0]
            return command, subject, to

        return 0, 0, 0
