"""
学習済みAIプレイヤー（遺伝的アルゴリズムで最適化）


このファイルは final_best_ai.json から自動生成されました。
適応度: 83.00
"""


from tcg.config import fortress_cool, fortress_limit
from tcg.controller import Controller




class Genalplayermk2ver2(Controller):
    """
    遺伝的アルゴリズムで最適化されたAIプレイヤー
   
    遺伝子パラメータ:
    - attack_min_troops: 9.316910
    - attack_success_margin: 1.231083
    - enemy_attack_priority_base: 107.895067
    - neutral_attack_ratio: 2.034091
    - support_priority_base: 83.124458
    - support_threshold: 17.362682
    - upgrade_priority_base: 188.421728
    - upgrade_threshold_center: 0.620656
    - upgrade_threshold_force: 0.873998
    - upgrade_threshold_normal: 0.889851
    """
   
    # 要塞の重要度（固定）
    FORTRESS_IMPORTANCE = {
        0: 3, 1: 4, 2: 3,
        3: 6, 4: 10, 5: 6,
        6: 6, 7: 10, 8: 6,
        9: 3, 10: 4, 11: 3
    }
   
    def __init__(self):
        super().__init__()
        self.step = 0
       
        # 遺伝子パラメータ（学習済み）
        self.genes = {
            "attack_min_troops": 9.3169099159,
            "attack_success_margin": 1.2310832715,
            "enemy_attack_priority_base": 107.8950665194,
            "neutral_attack_ratio": 2.0340905124,
            "support_priority_base": 83.1244582342,
            "support_threshold": 17.3626821899,
            "upgrade_priority_base": 188.4217280369,
            "upgrade_threshold_center": 0.6206564041,
            "upgrade_threshold_force": 0.8739981715,
            "upgrade_threshold_normal": 0.8898505338,
        }
   
    def team_name(self) -> str:
        return "Genalplayermk2Ver2"
   
    def estimate_attack_success(self, atk_troops, def_troops, def_lvl, def_kind, travel_time):
        """攻撃成功予測"""
        attacking_force = atk_troops / 2
       
        prod_rate = fortress_cool[def_kind][def_lvl]
        extra = travel_time / prod_rate if prod_rate > 0 else 0
       
        total_def = def_troops + extra
        damage = attacking_force * 0.8
       
        margin = self.genes["attack_success_margin"]
        return damage > total_def * margin
   
    def count_enemy_neighbors(self, fort_id, state):
        """敵隣接数をカウント"""
        neighbors = state[fort_id][5]
        return sum(1 for n in neighbors if state[n][0] == 2)
   
    def update(self, info):
        """メインの更新関数"""
        team, state, moving_pawns, spawning_pawns, done = info
        self.step += 1
       
        actions = []
        my_forts = [i for i in range(12) if state[i][0] == 1]
       
        # ==========================================
        # アップグレード判定
        # ==========================================
        for f in my_forts:
            level = state[f][2]
            troops = state[f][3]
           
            # 強制アップグレード（上限に近い場合）
            if level < 5 and troops >= fortress_limit[level] * self.genes["upgrade_threshold_force"]:
                if state[f][4] == -1:  # アップグレード中でない
                    actions.append((999, 2, f, 0))  # 最優先
       
        # 中央拠点のアップグレード
        for f in [4, 7]:
            if state[f][0] == 1:
                level = state[f][2]
                troops = state[f][3]
                if (level < 5 and
                    troops >= fortress_limit[level] * self.genes["upgrade_threshold_center"] and
                    state[f][4] == -1):
                    priority = self.genes["upgrade_priority_base"] + level * 5
                    actions.append((priority, 2, f, 0))
       
        # 通常のアップグレード
        for f in my_forts:
            if f in [4, 7]:
                continue
            level = state[f][2]
            troops = state[f][3]
            if (level < 5 and
                troops >= fortress_limit[level] * self.genes["upgrade_threshold_normal"] and
                state[f][4] == -1):
                imp = self.FORTRESS_IMPORTANCE[f]
                enemy_nei = self.count_enemy_neighbors(f, state)
                priority = self.genes["upgrade_priority_base"] + imp + enemy_nei * 5
                actions.append((priority, 2, f, 0))
       
        # ==========================================
        # 移動・攻撃判定
        # ==========================================
        for f in my_forts:
            neighbors = state[f][5]
            my_troops = state[f][3]
           
            if my_troops < self.genes["attack_min_troops"]:
                continue
           
            for nb in neighbors:
                nb_team = state[nb][0]
                nb_troops = state[nb][3]
               
                # 中立への攻撃
                if nb_team == 0:
                    if my_troops >= nb_troops * self.genes["neutral_attack_ratio"] + 8:
                        pr = 130 + self.FORTRESS_IMPORTANCE[nb]
                        actions.append((pr, 1, f, nb))
               
                # 味方への支援
                if nb_team == 1:
                    if nb_troops <= self.genes["support_threshold"] and my_troops > nb_troops + 10:
                        pr = self.genes["support_priority_base"] + self.count_enemy_neighbors(nb, state) * 6
                        actions.append((pr, 1, f, nb))
               
                # 敵への攻撃
                if nb_team == 2:
                    if self.estimate_attack_success(my_troops, nb_troops, state[nb][2], state[nb][1], 150):
                        imp = self.FORTRESS_IMPORTANCE[nb]
                        weak = max(0, 20 - nb_troops)
                        pr = self.genes["enemy_attack_priority_base"] + imp * 2 + weak
                        actions.append((pr, 1, f, nb))
       
        # 最優先アクションを選択
        if actions:
            actions.sort(reverse=True, key=lambda x: x[0])
            _, cmd, sub, to = actions[0]
            return cmd, sub, to
       
        return 0, 0, 0