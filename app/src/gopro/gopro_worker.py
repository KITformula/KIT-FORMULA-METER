import asyncio
import logging
import threading
from bleak import BleakScanner, BleakClient
from bleak.exc import BleakError
from bleak.backends.bluezdbus.client import BleakClientBlueZDBus
from PyQt5.QtCore import QObject, pyqtSignal

logger = logging.getLogger(__name__)

# GoPro UUIDs
COMMAND_REQ_UUID = "b5f90072-aa8d-11e3-9046-0002a5d5c51b"
CMD_SHUTTER_ON  = bytearray([0x03, 0x01, 0x01, 0x01])
CMD_SHUTTER_OFF = bytearray([0x03, 0x01, 0x01, 0x00])
# 接続確認用: バッテリーレベル
UUID_BATTERY_LEVEL = "00002a19-0000-1000-8000-00805f9b34fb"

class GoProWorker(QObject):
    status_changed = pyqtSignal(str)
    connection_success = pyqtSignal(bool)

    def __init__(self, target_address=None):
        super().__init__()
        self.target_address = target_address
        self.client = None
        self.loop = None
        self.thread = None
        self._keep_running = False
        self._command_queue = asyncio.Queue()

    def start_connection(self):
        if self.thread and self.thread.is_alive():
            return
        self._keep_running = True
        self.thread = threading.Thread(target=self._run_async_loop, daemon=True)
        self.thread.start()

    def stop(self):
        self._keep_running = False
        if self.loop:
            self.loop.call_soon_threadsafe(self._command_queue.put_nowait, None)

    def send_command_record_start(self):
        if self.loop:
            self.loop.call_soon_threadsafe(self._command_queue.put_nowait, "RECORD_START")

    def send_command_record_stop(self):
        if self.loop:
            self.loop.call_soon_threadsafe(self._command_queue.put_nowait, "RECORD_STOP")

    def _run_async_loop(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        try:
            self.loop.run_until_complete(self._main_task())
        except Exception as e:
            logger.error(f"GoPro Worker Error: {e}")
            self.status_changed.emit(f"Error: {e}")
        finally:
            self.loop.close()
            self.thread = None

    async def _main_task(self):
        while self._keep_running:
            # 1. アドレスがない場合のスキャン
            if not self.target_address:
                self.status_changed.emit("Scanning...")
                found_address = await self._scan_for_gopro()
                
                if not found_address:
                    self.status_changed.emit("GoPro Not Found")
                    await asyncio.sleep(3.0)
                    continue
                
                self.target_address = found_address
                self.status_changed.emit(f"Found: {self.target_address}")

            # 2. 接続試行
            self.status_changed.emit("Connecting...")
            
            # ★ 修正点: ここでの強制Unpairを削除しました。
            # まずは既存のペアリング情報で接続を試みます。
            
            need_repair = False # 修復が必要かどうかのフラグ

            try:
                async with BleakClient(self.target_address, timeout=20.0, disconnected_callback=self._on_disconnect) as client:
                    self.client = client
                    
                    if not client.is_connected:
                        raise Exception("Connect Failed")

                    self.status_changed.emit("Verifying...")
                    
                    # ペアリング試行（既にペアリング済みなら即座に完了する）
                    try:
                        await client.pair(protection_level=2)
                    except:
                        pass

                    # 接続検証
                    await asyncio.sleep(1.0)
                    try:
                        bat_val = await client.read_gatt_char(UUID_BATTERY_LEVEL)
                        bat_percent = int(bat_val[0])
                        # "Connected"を含めることで緑色表示にする
                        self.status_changed.emit(f"Connected! Bat:{bat_percent}%")
                        self.connection_success.emit(True)
                    except Exception as e:
                        logger.error(f"Verification Failed: {e}")
                        self.status_changed.emit("Auth Failed")
                        # 読めない＝認証エラーの可能性が高いので、修復フラグを立てる
                        need_repair = True
                        raise e

                    # --- コマンドループ ---
                    while self._keep_running and client.is_connected:
                        try:
                            try:
                                cmd = await asyncio.wait_for(self._command_queue.get(), timeout=5.0)
                                
                                if cmd is None:
                                    break

                                if cmd == "RECORD_START":
                                    self.status_changed.emit("Sending: REC ON")
                                    await client.write_gatt_char(COMMAND_REQ_UUID, CMD_SHUTTER_ON, response=True)
                                    self.status_changed.emit("Recording!")
                                    
                                elif cmd == "RECORD_STOP":
                                    self.status_changed.emit("Sending: REC OFF")
                                    await client.write_gatt_char(COMMAND_REQ_UUID, CMD_SHUTTER_OFF, response=True)
                                    self.status_changed.emit("Stopped")
                                    
                            except asyncio.TimeoutError:
                                # ハートビート
                                try:
                                    await client.read_gatt_char(UUID_BATTERY_LEVEL)
                                except:
                                    logger.warning("Heartbeat failed")
                                    break
                                    
                        except Exception as e:
                            logger.error(f"Loop Error: {e}")
                            break

            except BleakError as e:
                logger.error(f"Bleak error: {e}")
                self.status_changed.emit("Conn Error")
                err_str = str(e)
                
                # 特定のエラーなら修復フラグを立てる
                if "Authentication" in err_str or "Not connected" in err_str:
                    need_repair = True
                
                # デバイスが見つからない場合はアドレスが変わった可能性があるので忘れる
                if "not found" in err_str or "Device disconnected" in err_str:
                    self.target_address = None

            except Exception as e:
                logger.error(f"General error: {e}")
                self.status_changed.emit("Error")
                # 謎のエラーの場合はとりあえずアドレスを忘れて再スキャンへ
                self.target_address = None

            # --- 切断後の処理 ---
            self.client = None
            self.connection_success.emit(False)
            
            if self._keep_running:
                # ★ 修復が必要と判断された場合のみ Unpair を行う
                if need_repair and self.target_address:
                    self.status_changed.emit("Repairing...")
                    await self._force_unpair(self.target_address)
                    self.target_address = None # アドレスも忘れて最初からやり直す
                    await asyncio.sleep(3.0)
                else:
                    # 通常の切断（電源OFFなど）なら、Link Lostとして再接続を待つ
                    self.status_changed.emit("Link Lost / Retrying...")
                    await asyncio.sleep(2.0)

    async def _scan_for_gopro(self):
        try:
            device = await BleakScanner.find_device_by_filter(
                lambda d, ad: d.name and "GoPro" in d.name,
                timeout=8.0 
            )
            return device.address if device else None
        except Exception as e:
            logger.error(f"Scan error: {e}")
            return None

    async def _force_unpair(self, address):
        try:
            client = BleakClient(address)
            if hasattr(client, "unpair"):
                try:
                    await client.unpair()
                    logger.info(f"Unpaired {address}")
                except:
                    pass
        except:
            pass

    def _on_disconnect(self, client):
        self.status_changed.emit("Link Lost")
        if self.loop:
            self.loop.call_soon_threadsafe(self._command_queue.put_nowait, None)