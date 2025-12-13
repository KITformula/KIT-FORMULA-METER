import json
import os
import datetime


class DistanceStore:
    """
    総走行距離、日別走行距離、およびタイヤ別走行距離を管理するクラス。
    """

    STATE_FILE_PATH = "distance_state.json"

    def __init__(self):
        self.storage_path = os.path.abspath(self.STATE_FILE_PATH)

    def load_state(self) -> dict:
        """
        ファイルから走行距離データを読み込む。
        """
        # デフォルトのタイヤデータ構造
        default_tires = {
            "Dry 1": 0.0, "Dry 2": 0.0, "Dry 3": 0.0, "Dry 4": 0.0, "Dry 5": 0.0,
            "Wet 1": 0.0, "Wet 2": 0.0
        }
        
        default_state = {
            "total_km": 0.0, 
            "daily_km": 0.0, 
            "last_date": "",
            "tire_mileage": default_tires.copy()
        }

        try:
            if not os.path.exists(self.storage_path):
                return default_state

            with open(self.storage_path, "r") as f:
                data = json.load(f)

                total_km = float(data.get("total_km", 0.0))
                daily_km = float(data.get("daily_km", 0.0))
                last_date = str(data.get("last_date", ""))
                
                # 保存されているタイヤデータを取得し、デフォルトとマージ（新しいキーが増えた場合に対応）
                loaded_tires = data.get("tire_mileage", {})
                tire_mileage = default_tires.copy()
                for k, v in loaded_tires.items():
                    if k in tire_mileage:
                        tire_mileage[k] = float(v)

                if total_km < 0 or daily_km < 0:
                    return default_state

                print(f"走行距離ロード: Total={total_km:.1f}km")
                return {
                    "total_km": total_km,
                    "daily_km": daily_km,
                    "last_date": last_date,
                    "tire_mileage": tire_mileage
                }

        except Exception as e:
            print(f"エラー: 走行距離ファイルの読み込みに失敗しました。 {e}")
            return default_state

    def save_state(self, total_km: float, daily_km: float, tire_mileage: dict):
        """
        現在の状態を保存する。
        """
        try:
            today_str = datetime.date.today().isoformat()

            data = {
                "total_km": total_km,
                "daily_km": daily_km,
                "last_date": today_str,
                "tire_mileage": tire_mileage
            }

            with open(self.storage_path, "w") as f:
                json.dump(data, f, indent=4)

        except Exception as e:
            print(f"エラー: 走行距離の保存に失敗しました。 {e}")