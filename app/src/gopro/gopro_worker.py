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
            self.status_changed.emit(f"Sys Error: {e}")
        finally:
            try:
                tasks = asyncio.all_tasks(self.loop)
                for task in tasks:
                    task.cancel()
                self.loop.run_until_complete(asyncio.gather(*tasks, return_exceptions=True))
            except:
                pass
            self.loop.close()
            self.thread = None

    async def _main_task(self):
        while self._keep_running:
            # 1. ターゲット未定ならスキャン
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
            
            # フラグ: 修復（Unpair）が必要か
            need_repair = False

            try:
                # ★ 接続前に念のため強制切断を試みる（キャッシュ残り対策）
                # await self._force_disconnect(self.target_address) # ※BlueZのバグを誘発することもあるので一旦コメントアウト

                async with BleakClient(self.target_address, timeout=25.0, disconnected_callback=self._on_disconnect) as client:
                    self.client = client
                    
                    if not client.is_connected:
                        raise Exception("Connect Failed (Initial)")

                    self.status_changed.emit("Verifying...")
                    
                    # ペアリング試行
                    try:
                        await client.pair(protection_level=2)
                    except Exception as e:
                        logger.warning(f"Pairing note: {e}")

                    # ★ 接続検証: バッテリーレベル読み取り
                    # これが成功して初めて「接続成功」とみなす
                    try:
                        # 少し待ってから読み取る（接続直後の不安定さを回避）
                        await asyncio.sleep(1.0)
                        bat_val = await client.read_gatt_char(UUID_BATTERY_LEVEL)
                        bat_percent = int(bat_val[0])
                        self.status_changed.emit(f"Ready! Bat:{bat_percent}%")
                        self.connection_success.emit(True)
                    except Exception as e:
                        logger.error(f"Verification Failed: {e}")
                        self.status_changed.emit("Auth Failed")
                        need_repair = True
                        # 検証失敗時は例外を投げてwithブロックを抜け、切断処理へ
                        raise e

                    # --- コマンドループ ---
                    while self._keep_running and client.is_connected:
                        try:
                            try:
                                cmd = await asyncio.wait_for(self._command_queue.get(), timeout=5.0)
                                
                                if cmd == "RECORD_START":
                                    self.status_changed.emit("REC ON...")
                                    await client.write_gatt_char(COMMAND_REQ_UUID, CMD_SHUTTER_ON, response=True)
                                    self.status_changed.emit("Recording!")
                                    
                                elif cmd == "RECORD_STOP":
                                    self.status_changed.emit("REC OFF...")
                                    await client.write_gatt_char(COMMAND_REQ_UUID, CMD_SHUTTER_OFF, response=True)
                                    self.status_changed.emit("Stopped")
                                    
                            except asyncio.TimeoutError:
                                # ハートビート: 接続確認
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
                err_msg = str(e)
                self.status_changed.emit("Conn Error")
                
                # 特定のエラー、または「接続できたのに切れた」場合は修復へ
                if "Authentication" in err_msg or "Not connected" in err_msg or "Software caused connection abort" in err_msg:
                    need_repair = True
                
                # ★ Device disconnected が出たら、ターゲットアドレス自体が怪しいので忘れる
                if "Device disconnected" in err_msg:
                    need_repair = True
                    self.target_address = None

            except Exception as e:
                logger.error(f"General error: {e}")
                self.status_changed.emit("Error")
                need_repair = True

            # --- 終了処理 ---
            self.client = None
            self.connection_success.emit(False)
            self.status_changed.emit("Disconnected")

            # 3. 修復が必要ならUnpairして待機
            if need_repair and self._keep_running:
                self.status_changed.emit("Repairing...")
                # アドレスがあればUnpair
                if self.target_address:
                    await self._force_unpair(self.target_address)
                
                # ★ 重要: 修復後は必ずアドレスを忘れて再スキャンさせる
                self.target_address = None 
                await asyncio.sleep(3.0)
            
            await asyncio.sleep(1.0)

    async def _scan_for_gopro(self):
        try:
            device = await BleakScanner.find_device_by_filter(
                lambda d, ad: d.name and "GoPro" in d.name,
                timeout=10.0 
            )
            return device.address if device else None
        except Exception as e:
            logger.error(f"Scan error: {e}")
            return None

    async def _force_unpair(self, address):
        """OSのペアリング情報を削除する"""
        try:
            # 接続せずにクライアントを作ってunpairだけ叩く
            client = BleakClient(address)
            # Linux(BlueZ)環境でのみ有効
            if hasattr(client, "unpair"):
                # BlueZバックエンドであることを確認
                if isinstance(client._backend, BleakClientBlueZDBus):
                    await client.unpair()
                    logger.info(f"Unpaired {address} successfully.")
        except Exception as e:
            logger.warning(f"Unpair failed: {e}")

    def _on_disconnect(self, client):
        self.status_changed.emit("Link Lost")