import json
import os


class FuelStore:
    """
    燃料の「状態（State）」を不揮発性メモリ（JSONファイル）に
    読み書きすることに特化したクラス。
    """

    STATE_FILE_PATH = "fuel_state.json"

    def __init__(self):
        self.storage_path = os.path.abspath(self.STATE_FILE_PATH)

    def load_state(self) -> tuple[float | None, float]:
        """
        ファイルから状態を読み込む。
        戻り値: (前回の燃料残量 [ml], 前回の合計消費量 [ml])
        """
        default_consumed = 0.0
        
        try:
            if not os.path.exists(self.storage_path):
                return None, default_consumed

            with open(self.storage_path, "r") as f:
                data = json.load(f)
                remaining_ml = float(data.get("remaining_ml", -1))
                consumed_ml = float(data.get("consumed_ml", 0.0)) # ★追加

                if remaining_ml < 0:
                    print(f"警告: 保存された残量が不正です。リセットします。")
                    return None, default_consumed

                print(f"燃料状態ロード: 残量={remaining_ml:.1f}ml, 消費合計={consumed_ml:.1f}ml")
                return remaining_ml, consumed_ml

        except Exception as e:
            print(f"エラー: 燃料状態ファイルの読み込みに失敗しました。 {e}")
            return None, default_consumed

    def save_state(self, remaining_ml: float, consumed_ml: float):
        """
        現在の燃料残量と合計消費量を保存する。
        """
        try:
            data = {
                "remaining_ml": remaining_ml,
                "consumed_ml": consumed_ml # ★追加
            }
            with open(self.storage_path, "w") as f:
                json.dump(data, f, indent=4)

        except Exception as e:
            print(f"エラー: 燃料状態の保存に失敗しました。 {e}")