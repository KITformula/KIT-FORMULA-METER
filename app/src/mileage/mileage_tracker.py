import datetime
from src.util.distance_store import DistanceStore

class MileageTracker:
    """
    走行距離の計算、日付判定、永続化を管理するドメインクラス。
    Applicationクラスからロジックを分離するために使用。
    """

    def __init__(self):
        self.store = DistanceStore()
        
        # データをロード
        dist_data = self.store.load_state()
        
        self.loaded_total_km = dist_data["total_km"]
        last_daily_km = dist_data["daily_km"]
        last_date_str = dist_data["last_date"]
        
        # 今日の日付を取得
        self.today_str = datetime.date.today().isoformat()
        
        # 日付が変わっていれば、今日の積算距離の「開始値」は0
        # 同じ日なら、前回の続きから
        if last_date_str != self.today_str:
            print(f"MileageTracker: 日付変更 {last_date_str} -> {self.today_str}. Daily距離リセット.")
            self.start_daily_base = 0.0
        else:
            self.start_daily_base = last_daily_km
            
        # 現在の計算値（外部公開用）
        self.current_total_km = self.loaded_total_km
        self.current_daily_km = self.start_daily_base

    def update(self, session_km: float):
        """
        GPSWorkerから得られた「今回の起動ごとの走行距離」を受け取り、
        トータルと日別の距離を更新する。
        """
        # トータル = ロード時の値 + 今回の走行分
        self.current_total_km = self.loaded_total_km + session_km
        
        # 今日の距離 = 今日の開始時の値 + 今回の走行分
        self.current_daily_km = self.start_daily_base + session_km

    def get_mileage(self) -> tuple[float, float]:
        """
        (今日の距離, 総走行距離) を返す
        """
        return self.current_daily_km, self.current_total_km

    def save(self):
        """
        現在の状態を保存する
        """
        # 日付が変わっている可能性もあるため、保存時に現在日付で更新してもよいが
        # ここではシンプルに計算中の値を保存する
        self.store.save_state(self.current_total_km, self.current_daily_km)