import datetime
from src.util.distance_store import DistanceStore


class MileageTracker:
    """
    走行距離の計算、日付判定、永続化を管理するドメインクラス。
    タイヤごとの距離も管理する。
    """

    def __init__(self):
        self.store = DistanceStore()

        # データをロード
        dist_data = self.store.load_state()

        self.current_total_km = dist_data["total_km"]
        last_daily_km = dist_data["daily_km"]
        last_date_str = dist_data["last_date"]
        self.tire_mileage = dist_data["tire_mileage"] # dict

        # 今日の日付を取得
        self.today_str = datetime.date.today().isoformat()

        # 日付が変わっていれば、今日の距離はリセット
        if last_date_str != self.today_str:
            print(f"MileageTracker: 日付変更 {last_date_str} -> {self.today_str}. Daily距離リセット.")
            self.current_daily_km = 0.0
        else:
            self.current_daily_km = last_daily_km

        # セッションごとの差分計算用
        self.last_seen_session_km = 0.0

    def update(self, session_km: float, current_tire_name: str):
        """
        GPSWorkerから得られた「今回の起動ごとの走行距離(session_km)」を受け取り、
        前回値との差分(delta)を計算して各積算値に加算する。
        """
        # 差分を計算
        delta = session_km - self.last_seen_session_km
        
        # GPSWorkerがリセットされた場合などを考慮（マイナスなら無視またはリセット）
        if delta < 0:
            delta = 0 # もしGPS側が0リセットされたら、差分なしとして次回から追従
            
        if delta > 0:
            self.current_total_km += delta
            self.current_daily_km += delta
            
            # タイヤごとの積算
            if current_tire_name in self.tire_mileage:
                self.tire_mileage[current_tire_name] += delta
            else:
                # 未知のタイヤ名が来た場合は新規登録するか、無視するか。ここでは安全に登録。
                self.tire_mileage[current_tire_name] = delta

        # 次回用に保存
        self.last_seen_session_km = session_km

    def get_mileage_info(self) -> dict:
        """
        表示用の全情報を辞書で返す
        """
        return {
            "daily": self.current_daily_km,
            "total": self.current_total_km,
            "tires": self.tire_mileage
        }

    def save(self):
        """
        現在の状態を保存する
        """
        self.store.save_state(
            self.current_total_km, 
            self.current_daily_km, 
            self.tire_mileage
        )