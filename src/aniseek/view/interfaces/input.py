from abc import ABC, abstractmethod


class InputHandler(ABC):
    CTRL_BIT = 0x100  # 256
    SHIFT_BIT = 0x200  # 512
    ALT_BIT = 0x400  # 1024

    def __init__(self) -> None:
        ...

    def join(self) -> None:
        ...

    @abstractmethod
    def get_code(self, delay: int) -> int:
        ...
