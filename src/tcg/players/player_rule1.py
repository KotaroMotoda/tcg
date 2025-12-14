from tcg.controller import Controller
from tcg.config import fortress_limit
from typing import Dict, List, Tuple, Optional, Any  # 追加


class Rule1Player(Controller):
    """
    ルール概要:
    - 絶対ルール: レベル5未満の砦から送兵禁止。アップグレードは可能なら優先。
    - A: 最初に所持した砦がLv5かつ兵≥42、かつ自陣砦が1個の間のみ隣接（中立優先→敵）へ送兵。
         「反対側」は最初の砦から繋がる任意の砦だが、最初に獲得した1つ目の砦は除外対象。
    - B: 最初の砦以外（最初の砦も両隣確保後はBへ合流）
      a. 自陣数≤5、A/Bから共通に到達可能な中立/敵砦Cがあるなら、A/Bが両方兵≥42まで待機し、連続2手でCへ共同攻撃。
         共通源が3砦以上一致する場合は連続3手運用も可能。
      b. a不成立、兵≥45、かつ自陣数≤5なら、Aから接続するLv5未満の砦へ送兵（自陣Lv5未満優先→なければ中立/敵Lv5未満）。
      c. b不可（周囲がすべてLv5）、かつ自陣数≤5なら、直接接続の自陣のうち最小兵力へ送兵。
      d. 自陣が6砦になったら7砦目取得禁止。敵隣接がある砦は送兵せず兵を維持。敵隣接がない砦は自陣の最弱へ支援送兵。
    """

    def __init__(self) -> None:
        super().__init__()
        self.step = 0
        # 最初に単独保持した砦ID
        self.first_fortress: Optional[int] = None
        # 最初の砦から初めて獲得した砦（Aの「反対側」からは除外）
        self.first_captured_from_first: Optional[int] = None
        # 共同攻撃プラン（連続2手/3手運用）
        # 例: {"target": int, "sources": [int,int,...], "remaining": [int,int,...]}
        self.coordination_plan: Optional[Dict[str, Any]] = None
        self.labels: Dict[int, str] | None = None  # 遅延初期化に変更

    def team_name(self) -> str:
        return "Rule1Only"

    # 砦ラベル取得
    def fortress_label(self, fortress_id: int) -> str:
        if self.labels is None:
            # ゲーム開始後（update初回）に遅延初期化
            self.labels = {i: f"F{i}" for i in range(12)}
        return self.labels.get(fortress_id, f"F{fortress_id}")

    # 状態を分類してスナップショット化
    def _snapshot(self, state) -> Tuple[List[int], List[int], List[int], Dict[int, Dict[str, List[int]]]]:
        my = [i for i in range(12) if state[i][0] == 1]
        neutral = [i for i in range(12) if state[i][0] == 0]
        enemy = [i for i in range(12) if state[i][0] == 2]
        neighbors_by: Dict[int, Dict[str, List[int]]] = {}
        for i in range(12):
            nbs = state[i][5]
            neighbors_by[i] = {
                "mine": [n for n in nbs if state[n][0] == 1],
                "neutral": [n for n in nbs if state[n][0] == 0],
                "enemy": [n for n in nbs if state[n][0] == 2],
                "all": list(nbs),
            }
        return my, neutral, enemy, neighbors_by

    def _can_upgrade_at_capacity(self, s) -> bool:
        """最大収容兵数に到達したら即アップグレード（Lv5未満・待ち時間0）"""
        level = s[2]
        return s[4] == 0 and level < 5 and s[3] >= fortress_limit[level]

    def _can_upgrade(self, s) -> bool:
        """従来のアップグレード条件（半分以上）"""
        level = s[2]
        return s[4] == 0 and level < 5 and s[3] >= fortress_limit[level] // 2

    def _is_lv5(self, s) -> bool:
        return s[2] == 5

    def _pawns(self, s) -> int:
        return s[3]

    def _commit_coordination_if_any(self, state) -> Optional[Tuple[int, int, int]]:
        """
        共同攻撃プランが存在する場合、残手があれば次の送兵を実行。
        """
        if not self.coordination_plan:
            return None
        target = self.coordination_plan["target"]  # type: ignore[index]
        sources: List[int] = self.coordination_plan["sources"]  # type: ignore[assignment]
        remaining: List[int] = self.coordination_plan["remaining"]  # type: ignore[assignment]

        # 既にターゲットが自陣になっている、または共同元が消失した場合は破棄
        if state[target][0] == 1 or len(sources) != len(remaining):
            self.coordination_plan = None
            return None

        # 次に送るべきsourceのインデックスを探す（remaining[i] > 0 かつ Lv5かつ兵>=42）
        for idx, src in enumerate(sources):
            if remaining[idx] > 0 and state[src][0] == 1 and self._is_lv5(state[src]) and self._pawns(state[src]) >= 42:
                # 禁止ガード：7砦目取得禁止が成立する場合、ターゲットが中立/敵であれば送兵しない
                # ただし共同攻撃は自陣数<=5でのみ作成されるため、ここでは自陣数チェック不要
                remaining[idx] -= 1
                # 更新書き戻し
                self.coordination_plan["remaining"] = remaining  # type: ignore[index]
                # 最後の送兵が終わったらプラン破棄
                if sum(remaining) == 0:
                    self.coordination_plan = None
                return 1, src, target

        # 条件を満たすsourceがない（兵が足りない/失陥等）は何もしない
        return None

    def update(self, info) -> tuple[int, int, int]:
        team, state, moving_pawns, spawning_pawns, done = info
        self.step += 1

        if done:
            return 0, 0, 0

        my_forts, neutral_forts, enemy_forts, neighbors_by = self._snapshot(state)

        # 「最初の砦」の確定
        if self.first_fortress is None and len(my_forts) == 1:
            self.first_fortress = my_forts[0]

        # 絶対ルール: 容量到達アップグレードを最優先
        for i in my_forts:
            if self._can_upgrade_at_capacity(state[i]):
                return 2, i, 0

        # 絶対ルール: 次に従来条件（半分以上）でアップグレード
        for i in my_forts:
            if self._can_upgrade(state[i]):
                return 2, i, 0

        # 共同攻撃プランの継続実行（最優先でコミット）
        commit = self._commit_coordination_if_any(state)
        if commit:
            return commit

        # Guard: 自陣が6砦維持（7砦取得禁止）
        if len(my_forts) == 6:
            # 中立/敵への送兵は絶対禁止
            # 敵隣接がある砦は送兵せず保持
            safe_sources = [
                i for i in my_forts
                if len(neighbors_by[i]["enemy"]) == 0 and self._is_lv5(state[i])
            ]
            if safe_sources:
                source = max(safe_sources, key=lambda x: self._pawns(state[x]))  # 兵が多い砦を送源に
                ally_nbs = neighbors_by[source]["mine"]
                if ally_nbs:
                    target = min(ally_nbs, key=lambda x: self._pawns(state[x]))
                    # 送先が自陣であることを保証（7砦目取得禁止）
                    if state[target][0] == 1:
                        return 1, source, target
            return 0, 0, 0

        # Rule2-A: 自軍砦が1個、最初の砦がLv5かつ兵42以上なら隣接へ送兵
        if len(my_forts) == 1 and self.first_fortress is not None:
            src = self.first_fortress
            if state[src][0] == 1 and self._is_lv5(state[src]) and self._pawns(state[src]) >= 42:
                # 隣接の中立を優先、なければ敵へ。ただし「最初に獲得した1つ目の砦」は除外
                def valid_target(t: int) -> bool:
                    if t == self.first_captured_from_first:
                        return False
                    return True
                neutral_targets = [n for n in neighbors_by[src]["neutral"] if valid_target(n)]
                enemy_targets = [n for n in neighbors_by[src]["enemy"] if valid_target(n)]
                if neutral_targets:
                    # 最初に獲得した砦の記録（Aでのみ設定）
                    if self.first_captured_from_first is None:
                        self.first_captured_from_first = neutral_targets[0]
                    return 1, src, neutral_targets[0]
                if enemy_targets:
                    if self.first_captured_from_first is None:
                        self.first_captured_from_first = enemy_targets[0]
                    return 1, src, enemy_targets[0]

        # 以降はBロジック（自陣数≤5のみ許可）
        if len(my_forts) <= 5:
            # B-a: 共同攻撃ターゲット探索
            # 候補ソースはLv5かつ兵≥42の自砦
            sources = [i for i in my_forts if self._is_lv5(state[i]) and self._pawns(state[i]) >= 42]
            if len(sources) >= 2:
                # 各sourceの到達可能な中立/敵集合
                reachables_per_src: Dict[int, set] = {
                    s: set(neighbors_by[s]["neutral"] + neighbors_by[s]["enemy"])
                    for s in sources
                }
                # 2者以上で共通になるターゲット集合
                # 3者以上の共通も許容
                all_targets: Dict[int, int] = {}  # target -> count of sources that can reach
                for s, reach in reachables_per_src.items():
                    for t in reach:
                        all_targets[t] = all_targets.get(t, 0) + 1
                # 共通ターゲット（到達数>=2）を抽出
                common_targets = [t for t, cnt in all_targets.items() if cnt >= 2]
                if common_targets:
                    # 可能なら3者以上の共同攻撃を優先
                    best_target = None
                    best_count = 0
                    for t in common_targets:
                        count = sum(1 for s in sources if t in reachables_per_src[s])
                        if count > best_count:
                            best_target = t
                            best_count = count
                    if best_target is not None and best_count >= 2:
                        # 共同攻撃プラン生成（連続best_count手）
                        selected_sources = [s for s in sources if best_target in reachables_per_src[s]]
                        # 最大3手までに制限（仕様上3手対応）
                        selected_sources = selected_sources[:3]
                        self.coordination_plan = {
                            "target": best_target,
                            "sources": selected_sources,
                            "remaining": [1] * len(selected_sources),
                        }
                        # 直ちに1手目をコミット
                        return self._commit_coordination_if_any(state) or (0, 0, 0)

            # B-b: a不成立、兵≥45ならLv5未満へ送兵（支援優先→中立/敵Lv5未満）
            # ソースはLv5かつ兵≥45
            for src in sorted(my_forts, key=lambda x: self._pawns(state[x]), reverse=True):
                if not self._is_lv5(state[src]) or self._pawns(state[src]) < 45:
                    continue
                # 自陣Lv5未満を優先支援
                ally_low = [n for n in neighbors_by[src]["mine"] if state[n][2] < 5]
                if ally_low:
                    target = min(ally_low, key=lambda x: state[x][2])  # 低レベル優先
                    return 1, src, target
                # 次に中立/敵のLv5未満へ攻撃
                neutral_low = [n for n in neighbors_by[src]["neutral"] if state[n][2] < 5]
                enemy_low = [n for n in neighbors_by[src]["enemy"] if state[n][2] < 5]
                if neutral_low:
                    return 1, src, neutral_low[0]
                if enemy_low:
                    return 1, src, enemy_low[0]

            # B-c: 周囲がすべてLv5なら、自陣の最小兵力へ送兵
            for src in sorted(my_forts, key=lambda x: self._pawns(state[x]), reverse=True):
                if not self._is_lv5(state[src]):
                    continue
                nbs_all = neighbors_by[src]["all"]
                # 周囲がすべてLv5か判定（自陣/中立/敵問わず）
                if all(state[n][2] == 5 for n in nbs_all):
                    # 自陣に限って最小兵力へ送る
                    allies = neighbors_by[src]["mine"]
                    if allies:
                        target = min(allies, key=lambda x: self._pawns(state[x]))
                        return 1, src, target

        # ここまででアクションが決まらない場合は何もしない
        return 0, 0, 0