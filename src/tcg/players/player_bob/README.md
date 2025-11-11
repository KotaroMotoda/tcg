# Bob Player - 複数ファイル構成の例

このディレクトリは、複数ファイルで構成されたプレイヤーの実装例です。

## ファイル構成

```
player_bob/
├── __init__.py       # BobPlayerをエクスポート
├── player.py         # メインのプレイヤークラス
├── strategy.py       # 戦略ロジック
└── README.md         # このファイル
```

## 使い方

### インポート方法

```python
from tcg.players.player_bob import BobPlayer

# ゲームで使用
from tcg.game import Game
from tcg.players.sample_random import RandomPlayer

Game(BobPlayer(), RandomPlayer()).run()
```

### トーナメントでの使用

`src/tournament.py`は自動的にこのプレイヤーを検出します。

## 複数ファイル構成の利点

### 1. コードの整理

戦略ロジックを別ファイルに分離することで、コードが読みやすく、メンテナンスしやすくなります。

### 2. 機械学習モデルの統合

学習済みモデルを配置できます：

```
player_alice/
├── __init__.py
├── player.py
├── model.py           # モデル定義
├── model.pth          # PyTorchの学習済みモデル
└── config.json        # ハイパーパラメータなど
```

```python
# model.pyの例
import torch
import torch.nn as nn

class PolicyNetwork(nn.Module):
    def __init__(self):
        super().__init__()
        # ネットワーク定義
        ...

# player.pyでの使用
import torch
from .model import PolicyNetwork

class AlicePlayer(Controller):
    def __init__(self):
        super().__init__()
        self.model = PolicyNetwork()
        self.model.load_state_dict(torch.load("path/to/model.pth"))
        self.model.eval()

    def update(self, info):
        # モデルを使って行動決定
        with torch.no_grad():
            action = self.model(state_tensor)
        return action
```

### 3. ユーティリティの共有

複数の戦略やヘルパー関数を整理できます：

```
player_alice/
├── __init__.py
├── player.py
├── strategies/
│   ├── __init__.py
│   ├── offensive.py   # 攻撃的な戦略
│   ├── defensive.py   # 防御的な戦略
│   └── balanced.py    # バランス型戦略
└── utils/
    ├── __init__.py
    ├── graph.py       # グラフ解析
    └── evaluator.py   # 状態評価
```

### 4. テストの分離

各モジュールごとにテストを書けます：

```
player_alice/
├── __init__.py
├── player.py
├── strategy.py
└── tests/
    ├── test_player.py
    └── test_strategy.py
```

## Bob Playerの戦略

1. **アップグレード優先**: 部隊が十分溜まった要塞を優先的にアップグレード
2. **弱点狙い**: 最も弱い敵要塞を優先的に攻撃
3. **中立拡大**: 敵がいない場合は中立要塞を占領

## カスタマイズ例

### 1. 戦略の変更

`strategy.py`の各メソッドをカスタマイズ：

```python
def should_upgrade(self, fortress_state) -> bool:
    # より保守的なアップグレード戦略
    required = fortress_limit[level] // 2
    return pawn_number >= required * 2.0  # 2倍の部隊が必要
```

### 2. 新しい戦略の追加

`strategy.py`に新しいメソッドを追加：

```python
def should_retreat(self, state, fortress_id) -> tuple[bool, int]:
    """敵の攻勢時に撤退すべきか判定."""
    # 撤退ロジック
    ...
```

### 3. 複数の戦略を切り替え

```python
class BobPlayer(Controller):
    def __init__(self):
        super().__init__()
        self.aggressive_strategy = AggressiveStrategy()
        self.defensive_strategy = DefensiveStrategy()
        self.current_strategy = self.aggressive_strategy

    def update(self, info):
        # 状況に応じて戦略を切り替え
        if self.under_pressure(info):
            self.current_strategy = self.defensive_strategy
        else:
            self.current_strategy = self.aggressive_strategy

        return self.current_strategy.decide_action(info)
```

## 学習済みモデルの使用例

PyTorchを使った例：

```python
# model.py
import torch
import torch.nn as nn

class FortressNet(nn.Module):
    def __init__(self):
        super().__init__()
        self.fc1 = nn.Linear(12 * 5, 128)  # 12要塞 × 5特徴量
        self.fc2 = nn.Linear(128, 64)
        self.fc3 = nn.Linear(64, 64)  # 64コマンド

    def forward(self, x):
        x = torch.relu(self.fc1(x))
        x = torch.relu(self.fc2(x))
        return self.fc3(x)

# player.py
import torch
import os
from .model import FortressNet

class MLPlayer(Controller):
    def __init__(self):
        super().__init__()
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model = FortressNet().to(self.device)

        # モデルをロード
        model_path = os.path.join(os.path.dirname(__file__), "model.pth")
        if os.path.exists(model_path):
            self.model.load_state_dict(torch.load(model_path, map_location=self.device))
        self.model.eval()

    def state_to_tensor(self, state):
        """ゲーム状態をテンソルに変換."""
        features = []
        for fortress in state:
            # [team, kind, level, pawn_number, upgrade_time]
            features.extend(fortress[:5])
        return torch.tensor(features, dtype=torch.float32).unsqueeze(0).to(self.device)

    def update(self, info):
        team, state, pawn, SpawnPoint, done = info

        # 状態をテンソルに変換
        state_tensor = self.state_to_tensor(state)

        # モデルで予測
        with torch.no_grad():
            action_logits = self.model(state_tensor)
            action_idx = torch.argmax(action_logits).item()

        # action_idxをコマンドに変換（実装は省略）
        command = self.idx_to_command(action_idx)

        return command
```

## まとめ

複数ファイル構成にすることで：
- コードの可読性とメンテナンス性が向上
- 機械学習モデルやデータファイルを統合しやすい
- チーム開発がしやすい
- テストやデバッグが容易

シンプルなAIは1ファイルで、複雑なAIは複数ファイル構成で実装しましょう！
