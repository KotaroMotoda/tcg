"""Bob Player - 複数ファイル構成のプレイヤー実装例."""

from tcg.controller import Controller

from .strategy import Strategy


class BobPlayer(Controller):
    """
    複数ファイル構成のプレイヤー例.

    戦略ロジックを別ファイル(strategy.py)に分離することで、
    コードの整理や、機械学習モデルの統合などがしやすくなります。
    """

    def __init__(self):
        super().__init__()
        self.strategy = Strategy()
        self.step = 0

    def team_name(self) -> str:
        return "Bob"

    def update(self, info) -> tuple[int, int, int]:
        """
        ゲーム状態を受け取り、コマンドを返す.

        Args:
            info: [team_id, state, pawn, SpawnPoint, done]

        Returns:
            (command, subject, to): 実行するコマンド
        """
        team, state, pawn, SpawnPoint, done = info
        self.step += 1

        # デバッグ用: 100ステップごとに状態を評価
        if self.step % 100 == 0:
            evaluation = self.strategy.evaluate_state(state)
            # print(f"Step {self.step}: {evaluation}")

        # 1. アップグレード可能な要塞を探す
        for i in range(12):
            if state[i][0] == 1:  # 自分の要塞
                if self.strategy.should_upgrade(state[i]):
                    return 2, i, 0

        # 2. 最も強い要塞から攻撃
        fortress_id, pawn_count = self.strategy.find_strongest_fortress(state)

        if fortress_id is not None and pawn_count > 10:
            target = self.strategy.find_attack_target(state, fortress_id)
            if target is not None:
                return 1, fortress_id, target

        # 3. 何もできない場合
        return 0, 0, 0
