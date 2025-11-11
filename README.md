Territory Conquering Game
=========================
この実験では、陣取りゲームのAIプレイヤーを開発します。 

## 実験の準備

1. まずuvをインストールします。[uv](https://docs.astral.sh/uv/getting-started/installation/)を参考にしましょう。

2. リポジトリをクローンし、必要なライブラリをインストール:
```bash
git clone https://github.com/matt76k/tcg
cd tcg
uv sync
```

3. ゲームの実行:
```bash
uv run python src/main.py
```

## 実験内容

src/tcg/players以下のファイルを参考にして独自のAIプレイヤーを実装してください。
