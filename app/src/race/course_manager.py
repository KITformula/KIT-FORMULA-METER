import json
import math
import os
from dataclasses import dataclass, asdict
from typing import List, Optional


@dataclass
class SectorPoint:
    index: int  # 0=Start/Finish, 1=Sector1, 2=Sector2...
    lat: float
    lon: float
    heading: float  # 進行方向 (度, 0-360)


class CourseManager:
    """
    コース（セクターライン）の定義データを管理し、
    通過判定に必要なゲート情報を提供するクラス。
    """

    COURSE_FILE_PATH = "course_data.json"
    GATE_WIDTH_METERS = 7.0  # ゲートの幅 (左右合計)

    def __init__(self):
        self.sectors: List[SectorPoint] = []
        self.load_course()

        # キャリブレーション用のオフセット値
        self.offset_lat = 0.0
        self.offset_lon = 0.0

    def set_sector_point(self, index: int, lat: float, lon: float, heading: float):
        """
        指定されたインデックスのセクター地点を登録・更新する。
        """
        
        # ★★★ 修正箇所: スタートライン(Index 0)を設定する場合は、既存のコースをリセットする ★★★
        if index == 0:
            self.offset_lat = 0.0
            self.offset_lon = 0.0
            # 過去に設定した中間セクター(Sector 1など)が残っているとラップ計測が止まるため、
            # 新しいスタートライン設定時にはリストを空にして初期化する。
            self.sectors = []  
            print("Course reset due to Start Line update.")

        # 既存の同じインデックスがあれば削除
        self.sectors = [s for s in self.sectors if s.index != index]

        new_sector = SectorPoint(index, lat, lon, heading)
        self.sectors.append(new_sector)

        # インデックス順にソート
        self.sectors.sort(key=lambda s: s.index)

        print(f"Sector {index} registered: {lat}, {lon}, {heading}deg")
        self.save_course()

    def calibrate_position(self, current_lat: float, current_lon: float):
        """
        現在のGPS座標を「スタート地点(Index 0)」とみなして、
        コース全体を平行移動（キャリブレーション）する。
        """
        start_sector = self.get_sector(0)
        if not start_sector:
            print("Calibration failed: No start sector defined.")
            return

        # 記録されているスタート地点と、現在の地点の差分を計算
        self.offset_lat = current_lat - start_sector.lat
        self.offset_lon = current_lon - start_sector.lon

        print(
            f"Course Calibrated. Offset: Lat={self.offset_lat}, Lon={self.offset_lon}"
        )

    def get_sector(self, index: int) -> Optional[SectorPoint]:
        for s in self.sectors:
            if s.index == index:
                return s
        return None

    def get_gate_line(self, index: int):
        """
        指定セクターの「仮想ゲート（線分）」の座標を計算して返す。
        オフセット（キャリブレーション）適用済み。
        戻り値: ((lat1, lon1), (lat2, lon2))  # 左端と右端
        """
        sector = self.get_sector(index)
        if not sector:
            return None

        # キャリブレーション適用
        center_lat = sector.lat + self.offset_lat
        center_lon = sector.lon + self.offset_lon
        heading = sector.heading

        # 進行方向に対して左右90度の角度
        # headingは北0度、時計回り。
        # 左側: heading - 90
        # 右側: heading + 90

        # 簡易的なメートル→緯度経度変換係数 (日本付近)
        # 緯度1度 ≒ 111km, 経度1度 ≒ 91km (cos(35deg) * 111)
        METERS_PER_LAT = 111000.0
        METERS_PER_LON = 91000.0

        half_width = self.GATE_WIDTH_METERS / 2.0

        # 左端
        rad_left = math.radians(heading - 90)
        left_lat = center_lat + (math.cos(rad_left) * half_width) / METERS_PER_LAT
        left_lon = center_lon + (math.sin(rad_left) * half_width) / METERS_PER_LON

        # 右端
        rad_right = math.radians(heading + 90)
        right_lat = center_lat + (math.cos(rad_right) * half_width) / METERS_PER_LAT
        right_lon = center_lon + (math.sin(rad_right) * half_width) / METERS_PER_LON

        return ((left_lat, left_lon), (right_lat, right_lon))

    def save_course(self):
        try:
            data = [asdict(s) for s in self.sectors]
            with open(self.COURSE_FILE_PATH, "w") as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            print(f"Failed to save course: {e}")

    def load_course(self):
        if not os.path.exists(self.COURSE_FILE_PATH):
            return
        try:
            with open(self.COURSE_FILE_PATH, "r") as f:
                data = json.load(f)
                self.sectors = [SectorPoint(**d) for d in data]
                self.sectors.sort(key=lambda s: s.index)
            print(f"Loaded {len(self.sectors)} sectors.")
        except Exception as e:
            print(f"Failed to load course: {e}")