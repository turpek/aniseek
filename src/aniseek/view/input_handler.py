from __future__ import annotations

import queue
from threading import Lock

import cv2
from loguru import logger
from pynput import keyboard

from aniseek.view.interfaces.input import InputHandler


class KeyModifierState:
    def __init__(self) -> None:
        self._lock = Lock()
        self.ctrl = False
        self.shift = False
        self.alt = False
        self.__just_pressed = False

    def on_press(self, key: keyboard.Key | keyboard.KeyCode | None) -> None:
        with self._lock:
            if key in (keyboard.Key.ctrl, keyboard.Key.ctrl_r):
                self.ctrl = True
                self.__just_pressed = True
            elif key in (keyboard.Key.shift, keyboard.Key.shift_r):
                self.shift = True
                self.__just_pressed = True
            elif key in (keyboard.Key.alt, keyboard.Key.alt_r, keyboard.Key.alt_gr):
                self.alt = True
                self.__just_pressed = True

    def on_release(self, key: keyboard.Key | keyboard.KeyCode | None) -> None:
        with self._lock:
            if key in (keyboard.Key.ctrl, keyboard.Key.ctrl_r):
                self.ctrl = False
            elif key in (keyboard.Key.shift, keyboard.Key.shift_r):
                self.shift = False
            elif key in (keyboard.Key.alt, keyboard.Key.alt_r, keyboard.Key.alt_gr):
                self.alt = False

    def just_pressed(self) -> bool:
        with self._lock:
            return self.__just_pressed

    def snapshot(self) -> tuple[bool, bool, bool]:
        with self._lock:
            self.__just_pressed = False
            return self.ctrl, self.shift, self.alt


class CV2KeyReader(InputHandler):
    def __init__(self) -> None:
        super().__init__()

    def get_code(self, delay: int) -> int:
        return cv2.waitKeyEx(delay)


class PynputKeyReader(InputHandler):
    def __init__(self) -> None:
        super().__init__()
        self._queue: queue.Queue[int] = queue.Queue()
        self._modifiers = KeyModifierState()
        self._listener: keyboard.Listener | None = None
        try:
            self._listener = keyboard.Listener(
                on_press=self._on_press,
                on_release=self._on_release,
            )
            self._listener.start()
        except Exception as err:
            logger.warning(f'Failed to initialize pynput keyboard listener: {err}')
            self._listener = None

    def _on_press(self, key: keyboard.Key | keyboard.KeyCode | None) -> None:
        if key is None:
            return

        self._modifiers.on_press(key)

        # Ignore standalone modifier keys
        if key in (
            keyboard.Key.ctrl,
            keyboard.Key.ctrl_r,
            keyboard.Key.shift,
            keyboard.Key.shift_r,
            keyboard.Key.alt,
            keyboard.Key.alt_r,
            keyboard.Key.alt_gr,
        ):
            return

        ctrl, shift, alt = self._modifiers.snapshot()
        base_code: int | None = None

        if isinstance(key, keyboard.KeyCode):
            if key.char is not None and len(key.char) == 1:
                ascii_val = ord(key.char)
                # Handle control characters emitted when Ctrl is held (ASCII 1-26)
                if ctrl and 1 <= ascii_val <= 26:
                    base_code = ord('a') + ascii_val - 1
                else:
                    base_code = ord(key.char.lower())
        elif isinstance(key, keyboard.Key):
            if key == keyboard.Key.space:
                base_code = ord(' ')
            elif key == keyboard.Key.esc:
                base_code = 27
            elif key == keyboard.Key.enter:
                base_code = 13
            elif key == keyboard.Key.tab:
                base_code = 9
            elif key == keyboard.Key.backspace:
                base_code = 8
            elif key == keyboard.Key.delete:
                base_code = 127
            elif key == keyboard.Key.home:
                base_code = self.KEY_HOME
            elif key == keyboard.Key.end:
                base_code = self.KEY_END

        if base_code is not None:
            if ctrl:
                base_code |= self.CTRL_BIT
            if shift:
                base_code |= self.SHIFT_BIT
            if alt:
                base_code |= self.ALT_BIT
            self._queue.put(base_code)

    def _on_release(self, key: keyboard.Key | keyboard.KeyCode | None) -> None:
        self._modifiers.on_release(key)

    def join(self) -> None:
        if self._listener is not None and self._listener.running:
            try:
                self._listener.stop()
                self._listener.join(timeout=0.5)
            except Exception as err:
                logger.debug(f'Error stopping pynput listener: {err}')

    def get_code(self, delay: int) -> int:
        # Keep OpenCV window responsive and allow frame rendering
        cv_code = cv2.waitKey(max(1, delay))

        try:
            return self._queue.get_nowait()
        except queue.Empty:
            pass

        # Fallback to OpenCV key code if pynput listener is not active
        if self._listener is None and cv_code != -1:
            return cv_code & 0xFF

        return -1


# Alias for backward compatibility
HybridKeyReader = PynputKeyReader
