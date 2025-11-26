import json
import os
import datetime


class DistanceStore:
    """
    総走行距離と日別走行距離の状態をJSONファイルに読み書きするクラス。
    """

    STATE_FILE_PATH = "distance_state.json"

    def __init__(self):
        self.storage_path = os.path.abspath(self.STATE_FILE_PATH)

    def load_state(self) -> dict:
        """
        ファイルから走行距離データを読み込む。
        戻り値: {"total_km": float, "daily_km": float, "last_date": str}
        ファイルがない場合やエラー時はデフォルト値を返す。
        """
        default_state = {"total_km": 0.0, "daily_km": 0.0, "last_date": ""}
        
        try:
            if not os.path.exists(self.storage_path):
                return default_state

            with open(self.storage_path, "r") as f:
                data = json.load(f)
                
                # 古い形式(total_kmのみ)の場合の互換性対応も含め、getで取得
                # もしファイルにキーがなければデフォルト値(0.0)が使われる
                total_km = float(data.get("total_km", 0.0))
                daily_km = float(data.get("daily_km", 0.0))
                last_date = str(data.get("last_date", ""))

                if total_km < 0 or daily_km < 0:
                    return default_state

                print(f"走行距離ロード: Total={total_km:.1f}km, Daily={daily_km:.1f}km ({last_date})")
                return {
                    "total_km": total_km,
                    "daily_km": daily_km,
                    "last_date": last_date
                }

        except Exception as e:
            print(f"エラー: 走行距離ファイルの読み込みに失敗しました。 {e}")
            return default_state

    def save_state(self, total_km: float, daily_km: float):
        """
        現在の総走行距離と日別距離を保存する。
        日付は保存時の現在日付（ローカル）を使用する。
        """
        try:
            today_str = datetime.date.today().isoformat() # YYYY-MM-DD
            
            data = {
                "total_km": total_km,
                "daily_km": daily_km,
                "last_date": today_str
            }
            
            with open(self.storage_path, "w") as f:
                json.dump(data, f, indent=4)

        except Exception as e:
            print(f"エラー: 走行距離の保存に失敗しました。 {e}")