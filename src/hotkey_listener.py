from __future__ import annotations

import ctypes
import logging
import platform
import threading
from ctypes import wintypes
from typing import Callable

logger = logging.getLogger(__name__)


class GlobalHotkeyListener:
    def __init__(self, on_trigger: Callable[[], None]) -> None:
        self.on_trigger = on_trigger
        self.system = platform.system().lower()
        self._thread: threading.Thread | None = None
        self._thread_id: int | None = None
        self._hotkey_id = 1
        self._running = threading.Event()

    def start(self) -> None:
        if self.system != "windows":
            logger.info("Global hotkey is only enabled on Windows.")
            return
        if self._thread is not None:
            return
        self._running.set()
        self._thread = threading.Thread(target=self._run_windows_loop, name="global_hotkey", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        if self.system != "windows":
            return
        self._running.clear()
        if self._thread_id is not None:
            user32 = ctypes.windll.user32
            user32.PostThreadMessageW(self._thread_id, 0x0012, 0, 0)
        if self._thread is not None:
            self._thread.join(timeout=1.0)
        self._thread = None
        self._thread_id = None

    def _run_windows_loop(self) -> None:
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32
        self._thread_id = kernel32.GetCurrentThreadId()

        mod_control = 0x0002
        mod_alt = 0x0001
        vk_q = 0x51
        if not user32.RegisterHotKey(None, self._hotkey_id, mod_control | mod_alt, vk_q):
            logger.warning("Failed to register global hotkey Ctrl+Alt+Q.")
            return

        logger.info("Global hotkey registered: Ctrl+Alt+Q to stop LiveSoul.")
        message = wintypes.MSG()
        try:
            while self._running.is_set():
                result = user32.GetMessageW(ctypes.byref(message), None, 0, 0)
                if result <= 0:
                    break
                if message.message == 0x0312 and message.wParam == self._hotkey_id:
                    logger.info("Global hotkey pressed. Stopping runtime.")
                    self.on_trigger()
                    break
                user32.TranslateMessage(ctypes.byref(message))
                user32.DispatchMessageW(ctypes.byref(message))
        finally:
            user32.UnregisterHotKey(None, self._hotkey_id)
