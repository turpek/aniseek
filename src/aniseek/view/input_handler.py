from __future__ import annotations

import queue
from threading import Lock

import cv2
from loguru import logger
from pynput import keyboard

from aniseek.view.interfaces.command import ButtonState
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
    _MODIFIER_KEYS = (
        keyboard.Key.ctrl,
        keyboard.Key.ctrl_r,
        keyboard.Key.shift,
        keyboard.Key.shift_r,
        keyboard.Key.alt,
        keyboard.Key.alt_r,
        keyboard.Key.alt_gr,
    )

    def __init__(self) -> None:
        super().__init__()
        self._queue: queue.Queue[tuple[int, ButtonState]] = queue.Queue()
        self._modifiers = KeyModifierState()
        self._held_key: int | None = None
        self._state_lock = Lock()
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

    def _is_modifier(self, key: keyboard.Key | keyboard.KeyCode | None) -> bool:
        return key in self._MODIFIER_KEYS

    def _resolve_base_code(self, key: keyboard.Key | keyboard.KeyCode | None, ctrl: bool) -> int | None:
        if key is None:
            return None

        if isinstance(key, keyboard.KeyCode):
            if key.char is not None and len(key.char) == 1:
                ascii_val = ord(key.char)
                # Handle control characters emitted when Ctrl is held (ASCII 1-26)
                if ctrl and 1 <= ascii_val <= 26:
                    return ord('a') + ascii_val - 1
                return ord(key.char.lower())
            elif key.vk is not None:
                # Handle Numpad keys when char is None (e.g. Linux X11 or Windows)
                if key.vk == 0xFF9D:  # XK_KP_Begin / Numpad 5
                    return ord('5')
                elif 0xFFB0 <= key.vk <= 0xFFB9:  # XK_KP_0 to XK_KP_9
                    return ord('0') + (key.vk - 0xFFB0)
                elif 0x60 <= key.vk <= 0x69:  # Windows VK_NUMPAD0 to VK_NUMPAD9
                    return ord('0') + (key.vk - 0x60)
                elif key.vk == 0xFF8D:  # XK_KP_Enter
                    return 13
                elif key.vk == 0xFFAB:  # XK_KP_Add (+)
                    return ord('+')
                elif key.vk == 0xFFAD:  # XK_KP_Subtract (-)
                    return ord('-')
                elif key.vk == 0xFFAA:  # XK_KP_Multiply (*)
                    return ord('*')
                elif key.vk == 0xFFAF:  # XK_KP_Divide (/)
                    return ord('/')
                elif key.vk in (0xFFAC, 0xFF9E, 0xFF96):  # XK_KP_Decimal (.)
                    return ord('.')
        elif isinstance(key, keyboard.Key):
            if key == keyboard.Key.space:
                return ord(' ')
            elif key == keyboard.Key.esc:
                return 27
            elif key == keyboard.Key.enter:
                return 13
            elif key == keyboard.Key.tab:
                return 9
            elif key == keyboard.Key.backspace:
                return 8
            elif key == keyboard.Key.delete:
                return 127
            elif key == keyboard.Key.home:
                return self.KEY_HOME
            elif key == keyboard.Key.end:
                return self.KEY_END
            elif key == keyboard.Key.left:
                return self.KEY_LEFT
            elif key == keyboard.Key.right:
                return self.KEY_RIGHT
            elif key == keyboard.Key.up:
                return self.KEY_UP
            elif key == keyboard.Key.down:
                return self.KEY_DOWN

        return None

    def _on_press(self, key: keyboard.Key | keyboard.KeyCode | None) -> None:
        if key is None:
            return

        self._modifiers.on_press(key)
        if self._is_modifier(key):
            return

        ctrl, shift, alt = self._modifiers.snapshot()
        base_code = self._resolve_base_code(key, ctrl)
        if base_code is not None:
            if ctrl:
                base_code |= self.CTRL_BIT
            if shift:
                base_code |= self.SHIFT_BIT
            if alt:
                base_code |= self.ALT_BIT

            with self._state_lock:
                if self._held_key != base_code:
                    self._held_key = base_code
                    self._queue.put((base_code, ButtonState.PRESS))

    def _on_release(self, key: keyboard.Key | keyboard.KeyCode | None) -> None:
        self._modifiers.on_release(key)
        if self._is_modifier(key):
            return

        ctrl, shift, alt = self._modifiers.ctrl, self._modifiers.shift, self._modifiers.alt
        base_code = self._resolve_base_code(key, ctrl)
        if base_code is not None:
            if ctrl:
                base_code |= self.CTRL_BIT
            if shift:
                base_code |= self.SHIFT_BIT
            if alt:
                base_code |= self.ALT_BIT

            with self._state_lock:
                if self._held_key == base_code or self._held_key is not None:
                    self._held_key = None
                self._queue.put((base_code, ButtonState.RELEASE))

    def join(self) -> None:
        if self._listener is not None and self._listener.running:
            try:
                self._listener.stop()
                self._listener.join(timeout=0.5)
            except Exception as err:
                logger.debug(f'Error stopping pynput listener: {err}')

    def get_event(self, delay: int) -> tuple[int, ButtonState] | None:
        cv_code = cv2.waitKey(max(1, delay))

        try:
            return self._queue.get_nowait()
        except queue.Empty:
            pass

        with self._state_lock:
            if self._held_key is not None:
                return self._held_key, ButtonState.HOLD

        # Fallback to OpenCV key code if pynput listener is not active
        if self._listener is None and cv_code != -1:
            return cv_code & 0xFF, ButtonState.PRESS

        return None

    def get_code(self, delay: int) -> int:
        event = self.get_event(delay)
        while event is not None:
            code, state = event
            if state == ButtonState.PRESS:
                return code
            try:
                event = self._queue.get_nowait()
            except queue.Empty:
                break

        return -1


# Alias for backward compatibility
HybridKeyReader = PynputKeyReader
