from tcg.config import fortress_cool, fortress_limit
from tcg.controller import Controller


class ClaudePlayer(Controller):

    FORTRESS_IMPORTANCE = {
        0: 3, 1: 4, 2: 3,
        3: 6, 4: 10, 5: 6,
        6: 6, 7: 10, 8: 6,
        9: 3, 10: 4, 11: 3
    }

    def __init__(self) -> None:
        super().__init__()
        self.step = 0
        self.side_captured = False

        # 初期位置と両隣（固定）
        self.start_fortress = 10
        self.side_neighbors = [9, 11]

    def team_name(self) -> str:
        return "Strategic_Rebuild"

    def estimate_attack_success(self, atk, df, lvl, kind, travel):
        attacking = atk * 0.8 * 0.5
        prod = fortress_cool[kind][lvl]
        added = travel / prod if prod else 0
        return attacking > (df + added) * 1.2

    # =====================================================================
    #  ★ 修正① choose_best_neighbor を “両隣固定” に制限（side_captured=False）
    # =====================================================================
    def choose_best_neighbor(self, f, state):
        # 両隣取得前は 9,11 以外は絶対に返さない
        if not self.side_captured:
            candidates = [n for n in state[f][5] if n in self.side_neighbors]
        else:
            candidates = state[f][5]

        if not candidates:
            return None

        best, score_best = None, -999
        for n in candidates:
            score = 20 - self.FORTRESS_IMPORTANCE[n] - state[n][3]
            if score > score_best:
                best = n
                score_best = score
        return best

    # ============================================================
    #                         メイン更新
    # ============================================================
    def update(self, info):

        team, state, moving, spawning, done = info
        self.step += 1

        my_forts = [i for i in range(12) if state[i][0] == 1]
        actions = []

        # ============================================================
        # ★ side_captured フラグで攻撃可否を統制
        # ============================================================
        def attack_allowed(target):
            if not self.side_captured:
                return target in self.side_neighbors
            return True

        # ------------------------------------------------------------
        # ① 90%排出（勝てる & 許可されたターゲットのみ）
        # ------------------------------------------------------------
        for f in my_forts:
            lvl = state[f][2]
            troops = state[f][3]
            limit = fortress_limit[lvl]

            if troops >= limit * 0.9:
                best = self.choose_best_neighbor(f, state)
                if best is not None and attack_allowed(best):
                    df = state[best][3]
                    lvl_b = state[best][2]
                    kind_b = state[best][1]
                    if self.estimate_attack_success(troops, df, lvl_b, kind_b, 1):
                        actions.append((200, 1, f, best))

        # ------------------------------------------------------------
        # ② 両隣（9,11）攻略フェーズ
        # ------------------------------------------------------------
        if not self.side_captured:

            side_targets = [
                n for n in self.side_neighbors
                if state[n][0] != 1
            ]

            if not side_targets:
                self.side_captured = True
            else:
                ready = True
                attack_cmds = []

                for n in side_targets:
                    df = state[n][3]
                    lvl = state[n][2]
                    kind = state[n][1]

                    local_ready = False
                    for f in my_forts:
                        if n in state[f][5]:
                            atk = state[f][3]
                            if self.estimate_attack_success(atk, df, lvl, kind, 1):
                                attack_cmds.append((180, 1, f, n))
                                local_ready = True

                    if not local_ready:
                        ready = False

                # 両方 ready → 同時攻撃
                if ready and attack_cmds:
                    self.side_captured = True
                    actions.extend(attack_cmds)
                else:
                    # まだ早い → アップグレード
                    for f in my_forts:
                        lvl = state[f][2]
                        troops = state[f][3]
                        limit = fortress_limit[lvl]
                        if state[f][4] == -1 and lvl <= 4 and troops > limit * 0.7:
                            actions.append((90, 2, f, 0))

                    if actions:
                        actions.sort(reverse=True, key=lambda x: x[0])
                        _, cmd, s, t = actions[0]
                        return cmd, s, t

                    return 0, 0, 0

        # ------------------------------------------------------------
        # ③ 中央（4,7）は side_captured=True の後で解禁
        # ------------------------------------------------------------
        if self.side_captured:
            for target in [4, 7]:
                if state[target][0] != 1:
                    for f in my_forts:
                        if target in state[f][5] and state[f][3] > 15:
                            actions.append((160, 1, f, target))

        # ------------------------------------------------------------
        # ④ アップグレード
        # ------------------------------------------------------------
        for f in my_forts:
            lvl = state[f][2]
            troops = state[f][3]
            limit = fortress_limit[lvl]
            if state[f][4] == -1 and lvl <= 4 and troops > limit * 0.7:
                actions.append((70 + self.FORTRESS_IMPORTANCE[f], 2, f, 0))

        # ------------------------------------------------------------
        # ⑤ 実行
        # ------------------------------------------------------------
        if actions:
            actions.sort(reverse=True, key=lambda x: x[0])
            _, cmd, s, t = actions[0]
            return cmd, s, t

        return 0, 0, 0
