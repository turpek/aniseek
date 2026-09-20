from abc import ABC, abstractmethod


class InputHandler(ABC):
    CTRL_BIT = 0x100  # 256
    SHIFT_BIT = 0x200  # 512
    ALT_BIT = 0x400  # 1024
    KEY_HOME = 0xFF50  # 65360
    KEY_END = 0xFF57  # 65367

    def __init__(self) -> None:
        ...

    def join(self) -> None:
        ...

    @abstractmethod
    def get_code(self, delay: int) -> int:
        ...
