from __future__ import annotations

from abc import ABC, abstractmethod

from aniseek.view.interfaces.command import ButtonState


class InputHandler(ABC):
    CTRL_BIT = 0x100  # 256
    SHIFT_BIT = 0x200  # 512
    ALT_BIT = 0x400  # 1024
    KEY_HOME = 0xFF50  # 65360
    KEY_LEFT = 0xFF51  # 65361
    KEY_UP = 0xFF52  # 65362
    KEY_RIGHT = 0xFF53  # 65363
    KEY_DOWN = 0xFF54  # 65364
    KEY_END = 0xFF57  # 65367

    def __init__(self) -> None:
        ...

    def join(self) -> None:
        ...

    @abstractmethod
    def get_code(self, delay: int) -> int:
        ...

    def get_event(self, delay: int) -> tuple[int, ButtonState] | None:
        code = self.get_code(delay)
        if code != -1:
            return code, ButtonState.PRESS
        return None
