import json
import os

class FuelStore:
    """
    燃料の「状態（State）」を不揮発性メモリ（今回はJSONファイル）に
    読み書きすることに特化した専門家。
    """
    
    # appディレクトリ直下に保存する
    STATE_FILE_PATH = "fuel_state.json"

    def __init__(self):
        self.storage_path = os.path.abspath(self.STATE_FILE_PATH)

    def load_state(self) -> float | None:
        """
        ファイルから前回の燃料残量 [ml] を読み込む。
        失敗した場合は None を返す。
        """
        try:
            if not os.path.exists(self.storage_path):
                return None
                
            with open(self.storage_path, 'r') as f:
                data = json.load(f)
                remaining_ml = float(data["remaining_ml"])
                
                if remaining_ml < 0:
                    print(f"警告: 保存された残量が不正です ({remaining_ml} ml)。リセットします。")
                    return None
                    
                print(f"前回の燃料残量 {remaining_ml:.2f} ml を読み込みました。")
                return remaining_ml
                
        except Exception as e:
            print(f"エラー: 燃料状態ファイルの読み込みに失敗しました。 {e}")
            try:
                os.remove(self.storage_path)
                print(f"破損した {self.storage_path} を削除しました。")
            except OSError:
                pass
            return None

    def save_state(self, remaining_ml: float):
        """
        現在の燃料残量 [ml] をファイルに上書き保存する。
        """
        try:
            data = {"remaining_ml": remaining_ml}
            with open(self.storage_path, 'w') as f:
                json.dump(data, f, indent=4)
                
        except Exception as e:
            print(f"エラー: 燃料状態の保存に失敗しました。 {e}")