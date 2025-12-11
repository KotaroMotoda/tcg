from collections import deque
from typing import List, Optional, Tuple

from tcg.controller import Controller
from tcg.config import STEPLIMIT, fortress_limit, n_fortress

Action = Tuple[float, int, int, int]


class CreatedPlayer(Controller):
    """Heuristic controller that balances defense, expansion, and upgrades."""

    def __init__(self) -> None:
        super().__init__()
        self.step = 0
        self.my_team = 1
        self.enemy_team = 2
        self.core_targets: Tuple[int, ...] = (10, 9, 11, 7, 8, 6)
        self.home_priority: Tuple[int, ...] = (10, 9, 11)
        self.fill_ratio = 0.95
        self.core_hold_ratio = 0.95
        self.final_push_window = 400
        self.target_goal = len(self.core_targets)
        self.extra_capture_triggered = False

    def team_name(self) -> str:
        return "StrongAI"

    def update(self, info) -> tuple[int, int, int]:
        team_id, state, moving_pawns, spawning_pawns, done = info
        self.step += 1

        projected = self._project_future_counts(state, moving_pawns, spawning_pawns)
        my_nodes = [i for i in range(n_fortress) if state[i][0] == self.my_team]
        if not my_nodes:
            return 0, 0, 0

        phase = self._phase()
        steps_left = self._steps_left()
        core_owned = [i for i in self.core_targets if state[i][0] == self.my_team]
        goal_met = len(core_owned) >= self.target_goal
        if goal_met and len(my_nodes) > self.target_goal:
            self.extra_capture_triggered = True
        endgame_mode = steps_left <= self.final_push_window
        allow_extra = (not goal_met) or (endgame_mode and not self.extra_capture_triggered)

        candidates: List[Action] = []
        candidates.extend(self._core_hold_actions(state, projected, goal_met))
        candidates.extend(self._core_capture_actions(state, projected))
        candidates.extend(self._defense_actions(my_nodes, state, projected))
        candidates.extend(self._counter_attack_actions(state, projected))
        candidates.extend(
            self._expansion_actions(
                my_nodes,
                state,
                projected,
                phase,
                allow_extra=allow_extra,
            )
        )
        candidates.extend(
            self._attack_actions(
                my_nodes,
                state,
                projected,
                phase,
                allow_extra=allow_extra,
            )
        )
        candidates.extend(self._upgrade_actions(my_nodes, state, projected))
        candidates.extend(self._logistics_actions(my_nodes, state, projected, goal_met))
        candidates.extend(self._level5_support_actions(state, projected, allow_extra))
        if endgame_mode:
            candidates.extend(self._endgame_alpha_strike(state, projected, steps_left, goal_met))

        if candidates:
            candidates.sort(key=lambda item: item[0], reverse=True)
            _, command, subject, target = candidates[0]
            return command, subject, target

        return 0, 0, 0

    def _project_future_counts(
        self,
        state,
        moving_pawns,
        spawning_pawns,
    ) -> List[float]:
        projected = [state[i][3] for i in range(n_fortress)]

        def apply(team: int, kind: int, amount: float, target: int) -> None:
            owner = state[target][0]
            if owner != 0 and team == owner:
                projected[target] += amount
            else:
                power = 0.95 if kind == 1 else 0.65
                projected[target] -= amount * power

        for team, kind, _, target, _ in moving_pawns:
            apply(team, kind, 1, target)

        for team, kind, count, _, target, _ in spawning_pawns:
            if count > 0:
                apply(team, kind, count, target)

        return projected

    def _defense_actions(self, my_nodes, state, projected) -> List[Action]:
        actions: List[Action] = []
        for fortress in my_nodes:
            deficit = 3 - projected[fortress]
            if deficit <= 0:
                continue
            for donor in state[fortress][5]:
                if state[donor][0] != self.my_team:
                    continue
                if fortress not in state[donor][5]:
                    continue
                if state[donor][3] < 4:
                    continue
                donor_margin = projected[donor] - 5
                if donor_margin <= 0:
                    continue
                score = 140 + deficit * 15 + donor_margin
                actions.append((score, 1, donor, fortress))
        return actions

    def _counter_attack_actions(self, state, projected) -> List[Action]:
        actions: List[Action] = []
        for fortress in range(n_fortress):
            if state[fortress][0] != self.enemy_team or projected[fortress] > 6:
                continue
            for donor in state[fortress][5]:
                if state[donor][0] != self.my_team:
                    continue
                if fortress not in state[donor][5]:
                    continue
                capacity = self._attack_capacity(state[donor][3], state[donor][1])
                if capacity <= 0:
                    continue
                margin = capacity - (projected[fortress] + 2)
                if margin <= 0:
                    continue
                score = 115 + margin * 5
                actions.append((score, 1, donor, fortress))
        return actions

    def _expansion_actions(
        self,
        my_nodes,
        state,
        projected,
        phase: str,
        allow_extra: bool,
    ) -> List[Action]:
        actions: List[Action] = []
        for base in my_nodes:
            capacity = self._attack_capacity(state[base][3], state[base][1])
            if capacity <= 0:
                continue
            for neighbor in state[base][5]:
                if state[neighbor][0] != 0:
                    continue
                if not allow_extra and neighbor not in self.core_targets:
                    continue
                defense = projected[neighbor]
                margin = capacity - (defense + 1.5)
                if margin <= 0:
                    continue
                score = 90 + margin * 4 - defense
                if neighbor in self.core_targets:
                    score += 25
                if phase == "opening":
                    score += 10
                actions.append((score, 1, base, neighbor))
        return actions

    def _attack_actions(
        self,
        my_nodes,
        state,
        projected,
        phase: str,
        allow_extra: bool,
    ) -> List[Action]:
        actions: List[Action] = []
        for base in my_nodes:
            capacity = self._attack_capacity(state[base][3], state[base][1])
            if capacity <= 0:
                continue
            frontline_bonus = 5 if self._is_frontline(base, state) else 0
            for neighbor in state[base][5]:
                if state[neighbor][0] != self.enemy_team:
                    continue
                if not allow_extra and neighbor not in self.core_targets and not self._threatens_core(neighbor, state):
                    continue
                enemy_strength = projected[neighbor]
                buffer = 5 if phase == "late" else 7
                margin = capacity - (enemy_strength + buffer)
                if margin <= 0:
                    continue
                score = (
                    70
                    + margin * 3
                    + frontline_bonus
                    + state[neighbor][2] * 6
                    - self._distance_to_enemy(base, state)
                )
                actions.append((score, 1, base, neighbor))
        return actions

    def _upgrade_actions(self, my_nodes, state, projected) -> List[Action]:
        actions: List[Action] = []
        for base in my_nodes:
            owner, kind, level, count, upgrade_time, neighbors = state[base]
            if upgrade_time != -1 or level >= 5:
                continue
            limit = fortress_limit[level]
            if count < limit // 2:
                continue
            if projected[base] < limit * 0.6:
                continue
            if self._is_frontline(base, state) and projected[base] < limit * 0.9:
                continue
            pressure = sum(projected[n] for n in neighbors if state[n][0] == self.enemy_team)
            if pressure > 0 and pressure > projected[base] * 0.8:
                continue
            score = 50 + level * 4 - self._distance_to_enemy(base, state) * 3
            actions.append((score, 2, base, 0))
        return actions

    def _logistics_actions(self, my_nodes, state, projected, goal_met: bool) -> List[Action]:
        actions: List[Action] = []
        for base in my_nodes:
            limit = self._effective_limit(state[base][2])
            if state[base][3] <= limit:
                continue
            if not goal_met and base in self.home_priority:
                continue
            target = self._best_logistics_target(base, state, projected, goal_met)
            if target is None:
                continue
            score = 40 + (state[base][3] - limit)
            if self._is_frontline(target, state):
                score += 8
            actions.append((score, 1, base, target))
        return actions

    def _best_logistics_target(
        self,
        base: int,
        state,
        projected,
        goal_met: bool,
    ) -> Optional[int]:
        best_target = None
        best_score = float("-inf")
        for neighbor in state[base][5]:
            if state[neighbor][0] != self.my_team:
                continue
            if not goal_met and neighbor in self.home_priority:
                continue
            neighbor_limit = self._effective_limit(state[neighbor][2])
            if projected[neighbor] >= neighbor_limit - 0.5:
                continue
            deficit = neighbor_limit - projected[neighbor]
            score = deficit * 5 - self._distance_to_enemy(neighbor, state)
            if self._is_frontline(neighbor, state):
                score += 6
            if score > best_score:
                best_score = score
                best_target = neighbor
        return best_target

    def _attack_capacity(self, count: float, kind: int) -> float:
        ready = int(count) // 2
        if ready <= 0:
            return 0.0
        coef = 0.95 if kind == 1 else 0.65
        return ready * coef

    def _is_frontline(self, idx: int, state) -> bool:
        return any(state[n][0] == self.enemy_team for n in state[idx][5])

    def _distance_to_enemy(self, start: int, state) -> int:
        visited = {start}
        queue = deque([(start, 0)])
        while queue:
            node, dist = queue.popleft()
            if node != start and state[node][0] == self.enemy_team:
                return dist
            for nxt in state[node][5]:
                if nxt not in visited:
                    visited.add(nxt)
                    queue.append((nxt, dist + 1))
        return 6

    def _phase(self) -> str:
        if self.step < 800:
            return "opening"
        if self.step < 2800:
            return "mid"
        return "late"

    def _core_hold_actions(self, state, projected, goal_met: bool) -> List[Action]:
        actions: List[Action] = []
        for fortress in self.core_targets:
            if state[fortress][0] != self.my_team:
                continue
            if not goal_met and fortress in self.home_priority:
                continue
            limit = self._effective_limit(state[fortress][2])
            hold_target = limit
            deficit = hold_target - projected[fortress]
            if deficit <= 0:
                continue
            for donor in state[fortress][5]:
                if state[donor][0] != self.my_team:
                    continue
                if fortress not in state[donor][5]:
                    continue
                if not goal_met and donor in self.home_priority:
                    continue
                donor_limit = self._effective_limit(state[donor][2])
                if state[donor][3] < donor_limit * 0.8:
                    continue
                score = 220 + deficit * 12
                actions.append((score, 1, donor, fortress))
        return actions

    def _core_capture_actions(self, state, projected) -> List[Action]:
        actions: List[Action] = []
        for target in self.core_targets:
            if state[target][0] == self.my_team:
                continue
            required_margin = 2 if state[target][0] == 0 else 4
            for donor in state[target][5]:
                if state[donor][0] != self.my_team:
                    continue
                if target not in state[donor][5]:
                    continue
                capacity = self._attack_capacity(state[donor][3], state[donor][1])
                if capacity <= 0:
                    continue
                margin = capacity - (projected[target] + required_margin)
                if margin <= 0:
                    continue
                score = 200 + margin * 5 - projected[target]
                actions.append((score, 1, donor, target))
        return actions

    def _threatens_core(self, fortress: int, state) -> bool:
        return any(neighbor in self.core_targets for neighbor in state[fortress][5])

    def _endgame_alpha_strike(
        self,
        state,
        projected,
        steps_left: int,
        goal_met: bool,
    ) -> List[Action]:
        actions: List[Action] = []
        urgency = max(0, self.final_push_window - steps_left)
        for base in range(n_fortress):
            if state[base][0] != self.my_team:
                continue
            capacity = self._attack_capacity(state[base][3], state[base][1])
            if capacity <= 0:
                continue
            for neighbor in state[base][5]:
                if state[neighbor][0] == self.my_team or neighbor not in self.core_targets:
                    continue
                enemy_strength = projected[neighbor]
                margin = capacity - (enemy_strength + 1)
                if margin <= 0:
                    continue
                score = 230 + urgency / 6 + margin * 7
                actions.append((score, 1, base, neighbor))
        return actions

    def _steps_left(self) -> int:
        return max(0, STEPLIMIT - self.step)

    def _level5_support_actions(self, state, projected, allow_extra: bool) -> List[Action]:
        actions: List[Action] = []
        for base in range(n_fortress):
            if state[base][0] != self.my_team:
                continue
            if state[base][2] < 5:
                continue
            limit = self._effective_limit(state[base][2])
            if state[base][3] < limit * 0.8:
                continue
            target = self._neighbor_need_upgrade(base, state)
            if target is not None:
                deficit = max(0.0, self._effective_limit(state[target][2]) - projected[target])
                score = 250 + deficit * 3
                actions.append((score, 1, base, target))
                continue
            if not allow_extra:
                continue
            capacity = self._attack_capacity(state[base][3], state[base][1])
            if capacity <= 0:
                continue
            for neighbor in state[base][5]:
                if state[neighbor][0] == self.my_team:
                    continue
                enemy_strength = projected[neighbor]
                margin = capacity - (enemy_strength + 2)
                if margin <= 0:
                    continue
                bias = 20 if neighbor in self.core_targets else 0
                score = 240 + bias + margin * 4
                actions.append((score, 1, base, neighbor))
        return actions

    def _effective_limit(self, level: int) -> float:
        return fortress_limit[level] * self.fill_ratio

    def _neighbor_need_upgrade(self, base: int, state) -> Optional[int]:
        best_target: Optional[int] = None
        best_score = 0.0
        for neighbor in state[base][5]:
            if state[neighbor][0] != self.my_team:
                continue
            if state[neighbor][2] >= 5:
                continue
            limit = self._effective_limit(state[neighbor][2])
            deficit = max(0.0, limit - state[neighbor][3])
            score = deficit + (5 - state[neighbor][2]) * 3
            if score > best_score:
                best_score = score
                best_target = neighbor
        return best_target

