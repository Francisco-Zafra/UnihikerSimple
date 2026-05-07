"""Optional UNIHIKER onboard buzzer helper.

The main app does not use the buzzer yet. This module keeps the hardware access
isolated so future features can opt in without making desktop runs fail when
PinPong is not installed.
"""

import threading
import time


class BuzzerClient:
    """Small lazy wrapper around PinPong's UNIHIKER buzzer."""

    def __init__(self, enabled=False):
        self.enabled = bool(enabled)
        self.available = False
        self.error = None
        self._board = None
        self._buzzer = None
        self._lock = threading.Lock()
        self._initialized = False

    def set_enabled(self, enabled):
        enabled = bool(enabled)
        if self.enabled == enabled:
            return

        self.enabled = enabled
        self.available = False
        self.error = None
        self._board = None
        self._buzzer = None
        self._initialized = False

    def initialize(self):
        if self._initialized:
            return self.available

        self._initialized = True
        if not self.enabled:
            self.error = "BUZZER_DISABLED"
            return False

        try:
            from pinpong.board import Board
            from pinpong.extension.unihiker import buzzer

            Board().begin()
        except Exception as exc:
            self.error = str(exc)
            return False

        self._board = Board
        self._buzzer = buzzer
        self.available = True
        self.error = None
        return True

    def beep(self, frequency=880, beats=1, background=True):
        if background:
            self._run_async(self._beep, frequency, beats)
            return

        self._beep(frequency, beats)

    def success(self):
        self.sequence((660, 880), beats=1)

    def warning(self):
        self.sequence((440, 330), beats=1)

    def sequence(self, frequencies, beats=1):
        self._run_async(self._sequence, tuple(frequencies), beats)

    def stop(self):
        if not self.initialize():
            return

        try:
            self._buzzer.stop()
        except AttributeError:
            pass

    def _run_async(self, target, *args):
        thread = threading.Thread(target=target, args=args, daemon=True)
        thread.start()

    def _beep(self, frequency, beats):
        if not self.initialize():
            return

        with self._lock:
            self._buzzer.pitch(int(frequency), beats)

    def _sequence(self, frequencies, beats):
        if not self.initialize():
            return

        with self._lock:
            for frequency in frequencies:
                self._buzzer.pitch(int(frequency), beats)
                time.sleep(0.12)
