"""
AI Player


戦略的に考えて行動する強いAIプレイヤー
Claudeが作りました
"""


from tcg.config import fortress_cool, fortress_limit
from tcg.controller import Controller




class ClaudePlayer(Controller):


   # 要塞の重要度（接続数と位置に基づく）
   FORTRESS_IMPORTANCE = {
       0: 3, 1: 4, 2: 3,
       3: 6, 4: 10, 5: 6,
       6: 6, 7: 10, 8: 6,
       9: 3, 10: 4, 11: 3
   }


   def __init__(self):
       super().__init__()
       self.step = 0


   def team_name(self) -> str:
       return "Strategic"


   # -----------------------------------------------------------
   # 攻撃成功予測
   # -----------------------------------------------------------
   def estimate_attack_success(self, atk_troops, def_troops, def_lvl, def_kind, travel_time):
       attacking_force = atk_troops / 2


       prod_rate = fortress_cool[def_kind][def_lvl]
       extra = travel_time / prod_rate if prod_rate > 0 else 0


       total_def = def_troops + extra
       damage = attacking_force * 0.8


       return damage > total_def * 1.2


   def count_enemy_neighbors(self, fort_id, state):
       return sum(1 for n in state[fort_id][5] if state[n][0] == 2)


   # -----------------------------------------------------------
   # main update
   # -----------------------------------------------------------
   def update(self, info):
       # info = [last_move, state]
       last_move = info[0]
       state = info[1]
       return self.on_turn(last_move, state)


   # -----------------------------------------------------------
   # 本体ロジック
   # -----------------------------------------------------------
   def on_turn(self, last_move, state):
       self.step += 1


       # phase 判定
       if self.step < 3000:
           phase = "early"
       elif self.step < 15000:
           phase = "mid"
       else:
           phase = "late"


       actions = []


       my_forts = [i for i in range(12) if state[i][0] == 1]
       enemy_forts = [i for i in range(12) if state[i][0] == 2]
       neutral_forts = [i for i in range(12) if state[i][0] == 0]


       # -----------------------------------------------------------
       # まず "アップグレード優先"
       # -----------------------------------------------------------


       for f in my_forts:
           level = state[f][2]
           troops = state[f][3]


           # 上限の90%超えたら強制アップグレード
           if level < 5 and troops >= fortress_limit[level] * 0.9:
               if state[f][4] == -1:  # アップグレード中でない
                   actions.append((999, 2, f, 0))  # 最優先


       # 中央重要拠点 [4,7] は優先気味
       for f in [4, 7]:
           if state[f][0] == 1:
               level = state[f][2]
               troops = state[f][3]
               if level < 5 and troops >= fortress_limit[level] * 0.7 and state[f][4] == -1:
                   priority = 200 + level * 5
                   actions.append((priority, 2, f, 0))


       # 通常のアップグレード
       for f in my_forts:
           if f in [4, 7]:
               continue
           level = state[f][2]
           troops = state[f][3]
           if level < 5 and troops >= fortress_limit[level] * 0.75 and state[f][4] == -1:
               imp = self.FORTRESS_IMPORTANCE[f]
               enemy_nei = self.count_enemy_neighbors(f, state)
               pr = 150 + imp + enemy_nei * 5
               actions.append((pr, 2, f, 0))


       # -----------------------------------------------------------
       # 送り出し行動（無限循環防止版）
       # -----------------------------------------------------------


       for f in my_forts:
           neighbors = state[f][5]
           my_troops = state[f][3]


           for nb in neighbors:
               nb_team = state[nb][0]
               nb_troops = state[nb][3]


               # (条件1) 自分の軍が圧倒的勝利できるとき
               if nb_team == 0:  # 中立
                   if my_troops >= nb_troops * 2 + 8:
                       pr = 130 + self.FORTRESS_IMPORTANCE[nb]
                       actions.append((pr, 1, f, nb))


               # (条件2) 味方の前線（部隊 15 以下）に援軍
               if nb_team == 1:
                   if nb_troops <= 15 and my_troops > nb_troops + 10:
                       pr = 80 + self.count_enemy_neighbors(nb, state) * 6
                       actions.append((pr, 1, f, nb))


       # -----------------------------------------------------------
       # 敵への攻撃（成功率チェック）
       # -----------------------------------------------------------
       for f in my_forts:
           my_troops = state[f][3]
           if my_troops < 10:
               continue


           for nb in state[f][5]:
               if state[nb][0] == 2:
                   if self.estimate_attack_success(
                       my_troops,
                       state[nb][3],
                       state[nb][2],
                       state[nb][1],
                       150
                   ):
                       imp = self.FORTRESS_IMPORTANCE[nb]
                       weak = max(0, 20 - state[nb][3])
                       pr = 110 + imp * 2 + weak
                       actions.append((pr, 1, f, nb))


       # -----------------------------------------------------------
       # 行動選択
       # -----------------------------------------------------------
       if actions:
           actions.sort(reverse=True, key=lambda x: x[0])
           _, cmd, sub, to = actions[0]
           return cmd, sub, to


       return 0, 0, 0