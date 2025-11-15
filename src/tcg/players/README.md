# AI Player 実装ガイド

このディレクトリに自分のAIプレイヤーを実装して、トーナメントに参加できます！

## クイックスタート

### オプション1: シンプルな1ファイル構成（初心者向け）

1. `template_player.py` をコピーして新しいファイルを作成
   ```bash
   cp template_player.py player_yourname.py
   ```

2. クラス名とプレイヤー名を変更

3. `update()` メソッドに戦略を実装

4. ゲームを実行
    main.pyを変更して、作成したプレーヤーで戦うように変更
   ```bash
   uv run python src/main.py
   ```

### オプション2: 複数ファイル構成（機械学習/複雑なAI向け）

1. `player_bob/` ディレクトリを参考に新しいディレクトリを作成
   ```bash
   mkdir player_yourname
   cd player_yourname
   ```

2. `__init__.py`、`player.py`、`strategy.py`などを作成

3. トーナメントで自動検出される

詳細は `player_bob/README.md` を参照してください。

## ファイル命名規則

### 1ファイル構成
- `player_<あなたの名前>.py` の形式を推奨
- 例: `player_alice.py`, `player_bob.py`

### 複数ファイル構成（ディレクトリ）
- `player_<あなたの名前>/` の形式を推奨
- 例: `player_alice/`, `player_bob/`
- 必ず `__init__.py` にプレイヤークラスをエクスポート
- 学習済みモデル、データファイル、複数のモジュールを配置可能

## 基本構造

```python
from tcg.controller import Controller

class YourPlayerName(Controller):
    def __init__(self) -> None:
        super().__init__()
        # 必要に応じて初期化

    def team_name(self) -> str:
        return "YourName"  # プレイヤー名（結果表示に使用）

    def update(self, info) -> tuple[int, int, int]:
        """
        毎ステップ呼ばれる。ゲーム状態を受け取り、コマンドを返す。

        Args:
            info: [team_id, state, pawn, SpawnPoint, done]

        Returns:
            (command, subject, to): 実行するコマンド
        """
        team, state, pawn, SpawnPoint, done = info

        # ここに戦略を実装
        command = 0  # 0: なにもしない, 1: 部隊移動, 2: アップグレード
        subject = 0  # 対象の要塞ID (0-11)
        to = 0       # 移動先の要塞ID (subjectの隣接要塞のいずれか)

        return command, subject, to
```

## ゲーム情報の詳細

### info の内容

```python
team, state, pawn, SpawnPoint, done = info
```

- **team** (int): 自分のチームID (1 または 2)
  - 注意: `state` は常に自分視点に変換されている（自分が下側プレイヤーとして見える）

- **state** (list): 12個の要塞の状態
  ```python
  state[fortress_id] = [team, kind, level, pawn_number, upgrade_time, [to_set]]
  ```
  - `team`: 0=中立, 1=自分, 2=相手
  - `kind`: 0=速い部隊生成, 1=強い部隊生成
  - `level`: 1-5（レベルが高いほど速く部隊を生成）
  - `pawn_number`: 現在の部隊数
  - `upgrade_time`: アップグレード中の残り時間（0=アップグレード可能）
  - `to_set`: この要塞から部隊を送れる隣接要塞のリスト

- **pawn** (list): 移動中の部隊情報
  ```python
  pawn[i] = [team, kind, pawn_number, position_x, position_y, to_fortress_id]
  ```

- **SpawnPoint** (list): 出発待ちの部隊
  ```python
  SpawnPoint[fortress_id] = [[kind, number], ...]
  ```

- **done** (bool): ゲーム終了フラグ

### コマンドフォーマット

返却値: `(command, subject, to)`

1. **何もしない**
   ```python
   return (0, 0, 0)
   ```

2. **部隊を移動**
   ```python
   return (1, from_fortress, to_fortress)
   ```
   - `from_fortress` の部隊の半分を `to_fortress` へ送る
   - `to_fortress` は `state[from_fortress][5]` に含まれる必要がある
   - 自分のチーム（team=1）の要塞からのみ移動可能

3. **要塞をアップグレード**
   ```python
   return (2, fortress_id, 0)
   ```
   - 条件:
     - 自分のチーム（team=1）の要塞
     - `upgrade_time == 0`
     - 部隊数 >= `fortress_limit[level] // 2`
   - アップグレード中は部隊を生成しない

### 重要な定数（`tcg.config` からインポート可能）

```python
from tcg.config import fortress_limit, fortress_cool

# 要塞レベルごとの最大部隊数
fortress_limit = [10, 10, 20, 30, 40, 50]  # インデックス0は未使用

# 部隊生成のクールダウン（ステップ数）
# fortress_cool[level][kind]
fortress_cool = [
    [0, 0],      # レベル0（未使用）
    [250, 400],  # レベル1
    [200, 300],  # レベル2
    [150, 240],  # レベル3
    [100, 200],  # レベル4
    [80, 160],   # レベル5
]
```

### 要塞の配置

```
    [0]     [1]
     |  \ /  |
     |   X   |
     |  / \  |
    [3]     [4]
     |       |
    [5]     [6]
     |  \ /  |
     |   X   |
     |  / \  |
    [7]     [8]
     |       |
    [9]-----[10]
       \   /
        [11]
```

各要塞の隣接関係は `state[fortress_id][5]` で確認できます。

## 戦略のヒント

### 基本戦略
- **領土拡大**: 中立要塞を早期に占領
- **防御**: 相手の侵攻を察知して部隊を集める
- **攻撃**: 相手の弱い要塞を集中攻撃
- **アップグレード**: 部隊生成速度を上げる

### サンプルコード例

#### 1. 最も部隊が多い自分の要塞から攻撃

```python
def update(self, info):
    team, state, pawn, SpawnPoint, done = info

    # 自分の要塞で最も部隊数が多いものを探す
    my_fortresses = [(i, state[i][3]) for i in range(12) if state[i][0] == 1]

    if not my_fortresses:
        return 0, 0, 0

    strongest = max(my_fortresses, key=lambda x: x[1])
    fortress_id = strongest[0]

    # 隣接する敵要塞を探す
    neighbors = state[fortress_id][5]
    enemy_neighbors = [n for n in neighbors if state[n][0] == 2]

    if enemy_neighbors and state[fortress_id][3] > 5:
        target = enemy_neighbors[0]
        return 1, fortress_id, target

    return 0, 0, 0
```

#### 2. 部隊が溜まったらアップグレード

```python
from tcg.config import fortress_limit

def update(self, info):
    team, state, pawn, SpawnPoint, done = info

    # 自分の要塞を調べる
    for i in range(12):
        if state[i][0] != 1:  # 自分の要塞でない
            continue

        level = state[i][2]
        pawn_count = state[i][3]
        upgrade_time = state[i][4]

        # アップグレード可能かチェック
        if upgrade_time == 0 and pawn_count >= fortress_limit[level] // 2:
            return 2, i, 0

    return 0, 0, 0
```

#### 3. 条件分岐による複合戦略

```python
from tcg.config import fortress_limit

def update(self, info):
    team, state, pawn, SpawnPoint, done = info

    # 1. まずアップグレード可能な要塞を探す
    for i in range(12):
        if state[i][0] == 1 and state[i][4] == 0:
            level = state[i][2]
            if state[i][3] >= fortress_limit[level] // 2:
                return 2, i, 0

    # 2. 次に攻撃可能な要塞を探す
    for i in range(12):
        if state[i][0] == 1 and state[i][3] > 10:
            neighbors = state[i][5]
            enemy = [n for n in neighbors if state[n][0] == 2]
            if enemy:
                return 1, i, enemy[0]

    # 3. 中立要塞への進出
    for i in range(12):
        if state[i][0] == 1 and state[i][3] > 5:
            neighbors = state[i][5]
            neutral = [n for n in neighbors if state[n][0] == 0]
            if neutral:
                return 1, i, neutral[0]

    return 0, 0, 0
```

## デバッグ方法

### 1. プリントデバッグ
```python
def update(self, info):
    team, state, pawn, SpawnPoint, done = info

    # 自分の要塞の状態を表示
    my_fortresses = [(i, state[i]) for i in range(12) if state[i][0] == 1]
    print(f"My fortresses: {my_fortresses}")

    return 0, 0, 0
```

### 2. ステップ数での条件実行
```python
def __init__(self):
    super().__init__()
    self.step = 0

def update(self, info):
    self.step += 1

    # 最初の100ステップだけデバッグ出力
    if self.step <= 100:
        print(f"Step {self.step}: {info[1]}")

    return 0, 0, 0
```

### 3. ビジュアルで確認
`src/main.py` 内の `Game()` に `window=True` を渡してゲームを実行すると、
ウィンドウで状況を確認できます。

## 注意事項

- **視点変換**: `info` で受け取る `state` は常に自分視点（team=1が自分、team=2が相手）
- **無効なコマンド**: 無効なコマンドを返すとゲームが停止する可能性があるので注意
- **パフォーマンス**: `update()` は毎ステップ呼ばれるため、重い計算は避ける
- **状態の保持**: `self` を使って前のステップの情報を記憶できる

## トーナメントへの参加

1. このディレクトリに `player_<yourname>.py` を配置
2. `src/tournament.py` を実行すると自動的に検出される
3. 全プレイヤーで総当たり戦が行われる
4. 結果が表示される

## サンプルAI

参考として以下のAIが `src/tcg/sample_players.py`、`src/tcg/claude_player.py`があります。
- `RandomPlayer`: ランダムに行動
- `ClaudePlayer`: Claude-Codeに作らせた

これらを参考にして、独自の戦略を実装してください！

頑張って最強のAIを作りましょう！