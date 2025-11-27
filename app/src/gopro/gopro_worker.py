import asyncio
import logging
import threading
from bleak import BleakScanner, BleakClient
from bleak.exc import BleakError
from PyQt5.QtCore import QObject, pyqtSignal

logger = logging.getLogger(__name__)

# --- GoPro UUIDs ---
COMMAND_REQ_UUID = "b5f90072-aa8d-11e3-9046-0002a5d5c51b"
CMD_SHUTTER_ON = bytearray([0x03, 0x01, 0x01, 0x01])
CMD_SHUTTER_OFF = bytearray([0x03, 0x01, 0x01, 0x00])
UUID_BATTERY_LEVEL = "00002a19-0000-1000-8000-00805f9b34fb"


class GoProWorker(QObject):
    # GUIへの通知用シグナル
    status_changed = pyqtSignal(str)
    connection_success = pyqtSignal(bool)
    battery_changed = pyqtSignal(int)

    def __init__(self):
        super().__init__()
        self.target_address = None
        self.ignore_addresses = set()

        self.loop = None
        self.thread = None
        self._keep_running = False
        self._command_queue = asyncio.Queue()

    def start_connection(self):
        if self.thread and self.thread.is_alive():
            return

        self._keep_running = True
        self.target_address = None
        self.ignore_addresses.clear()

        self.thread = threading.Thread(target=self._run_async_loop, daemon=True)
        self.thread.start()

    def stop(self):
        """GUIから呼ばれる: 処理を停止"""
        # ▼ ログ追加: ボタンが効いているか確認しやすくする
        logger.info(">>> GoProWorker: STOP SIGNAL RECEIVED <<<")

        self._keep_running = False
        if self.loop:
            self.loop.call_soon_threadsafe(self._command_queue.put_nowait, None)

    def send_command_record_start(self):
        if self.loop:
            self.loop.call_soon_threadsafe(
                self._command_queue.put_nowait, "RECORD_START"
            )

    def send_command_record_stop(self):
        if self.loop:
            self.loop.call_soon_threadsafe(
                self._command_queue.put_nowait, "RECORD_STOP"
            )

    def _run_async_loop(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        try:
            self.loop.run_until_complete(self._main_logic())
        except Exception as e:
            logger.error(f"GoPro Worker Critical Error: {e}")
            self.status_changed.emit(f"Sys Error: {e}")
        finally:
            try:
                tasks = asyncio.all_tasks(self.loop)
                for task in tasks:
                    task.cancel()
                self.loop.run_until_complete(
                    asyncio.gather(*tasks, return_exceptions=True)
                )
            except Exception:
                pass
            self.loop.close()
            self.thread = None
            self.status_changed.emit("Disconnected")

    async def _main_logic(self):
        while self._keep_running:
            try:
                # -------------------------------------------------
                # 1. スキャン (アドレスが未定の場合)
                # -------------------------------------------------
                if self.target_address is None:
                    self.status_changed.emit("Scanning...")
                    logger.info("Scanning for GoPro...")

                    if not self._command_queue.empty():
                        cmd = self._command_queue.get_nowait()
                        if cmd is None:
                            return

                    try:
                        # ▼ 修正: タイムアウトを 8.0 -> 3.0 に短縮してレスポンス向上
                        device = await BleakScanner.find_device_by_filter(
                            lambda d, ad: d.name
                            and "GoPro" in d.name
                            and d.address not in self.ignore_addresses,
                            timeout=3.0,
                        )
                    except asyncio.TimeoutError:
                        device = None

                    if not self._keep_running:
                        return

                    if not device:
                        self.status_changed.emit("Not Found / Retrying")
                        if self.ignore_addresses:
                            logger.info(f"Ignored addresses: {self.ignore_addresses}")

                        # ▼ 修正: 待機時間を 2.0 -> 1.0 に短縮
                        await asyncio.sleep(1.0)
                        continue

                    self.target_address = device.address
                    self.status_changed.emit(f"Found: {device.name}")
                    logger.info(f"Found GoPro: {self.target_address}")

                # -------------------------------------------------
                # 2. 接続試行
                # -------------------------------------------------
                self.status_changed.emit("Connecting...")

                async with BleakClient(
                    self.target_address,
                    timeout=20.0,
                    disconnected_callback=self._on_disconnect,
                ) as client:
                    if not client.is_connected:
                        raise Exception("Connection failed (is_connected=False)")

                    self.status_changed.emit("Pairing...")
                    try:
                        await client.pair(protection_level=2)
                        logger.info("Pairing requested")
                    except Exception as e:
                        logger.warning(f"Pairing warning (continuing): {e}")

                    self.status_changed.emit("Verifying...")
                    try:
                        bat_val = await client.read_gatt_char(UUID_BATTERY_LEVEL)
                        bat_percent = int(bat_val[0])

                        self.status_changed.emit(f"Connected! Bat:{bat_percent}%")
                        self.battery_changed.emit(bat_percent)
                        self.connection_success.emit(True)

                        self.ignore_addresses.clear()

                    except Exception as e:
                        self.status_changed.emit("Auth Failed")
                        raise Exception(f"Authentication/Read Failed: {e}")

                    # -------------------------------------------------
                    # 3. コマンド待機ループ
                    # -------------------------------------------------
                    logger.info("Entered command loop")
                    while self._keep_running and client.is_connected:
                        try:
                            cmd = await asyncio.wait_for(
                                self._command_queue.get(), timeout=5.0
                            )

                            if cmd is None:
                                logger.info("Stop command received. Exiting main loop.")
                                return

                            if cmd == "RECORD_START":
                                self.status_changed.emit("REC: Starting...")
                                await client.write_gatt_char(
                                    COMMAND_REQ_UUID, CMD_SHUTTER_ON, response=True
                                )
                                self.status_changed.emit("Recording!")

                            elif cmd == "RECORD_STOP":
                                self.status_changed.emit("REC: Stopping...")
                                await client.write_gatt_char(
                                    COMMAND_REQ_UUID, CMD_SHUTTER_OFF, response=True
                                )
                                self.status_changed.emit("Ready")

                        except asyncio.TimeoutError:
                            try:
                                bat_val = await client.read_gatt_char(
                                    UUID_BATTERY_LEVEL
                                )
                                bat_percent = int(bat_val[0])
                                self.battery_changed.emit(bat_percent)
                            except Exception as hb_err:
                                logger.warning(f"Heartbeat failed: {hb_err}")
                                break

                        except Exception as e:
                            logger.error(f"Command Loop Error: {e}")
                            break

            # -------------------------------------------------
            # 4. エラーハンドリング
            # -------------------------------------------------
            except (BleakError, Exception) as e:
                if not self._keep_running:
                    return

                logger.error(f"Connection/Runtime Error: {e}")
                self.status_changed.emit("Error / Retrying...")
                self.connection_success.emit(False)

                if self.target_address:
                    logger.info(f"Adding {self.target_address} to ignore list")
                    self.ignore_addresses.add(self.target_address)

                    self.status_changed.emit("Cleaning up...")
                    try:
                        async with BleakClient(self.target_address) as temp_client:
                            await temp_client.unpair()
                        logger.info("Unpair successful")
                    except Exception as unpair_err:
                        logger.warning(f"Unpair failed: {unpair_err}")

            finally:
                if not self._keep_running:
                    return

                self.target_address = None
                await asyncio.sleep(3.0)

    def _on_disconnect(self, client):
        logger.info("GoPro Disconnected callback")
        self.connection_success.emit(False)
        if self.loop and self._keep_running:
            self.loop.call_soon_threadsafe(
                self._command_queue.put_nowait, "DISCONNECTED_EVENT"
            )
