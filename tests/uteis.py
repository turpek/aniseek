from __future__ import annotations

import cv2
import numpy as np

from aniseek.core.interfaces.source import IFrameSource


class MyVideoCapture(IFrameSource):
    def __init__(self, isopened: bool = True, frame_count: int = 500) -> None:
        self.frames = [np.zeros((2, 2)) for _ in range(frame_count)]
        self.index = 0
        self.isopened = isopened

    @property
    def frame_count(self) -> int:
        return len(self.frames)

    @property
    def fps(self) -> float:
        return 24.0

    def seek(self, frame_id: int) -> None:
        self.index = frame_id

    def read(self) -> tuple[bool, np.ndarray | None]:
        if self.index < len(self.frames):
            frame = self.frames[self.index]
            self.index += 1
            return True, frame
        return False, None

    def grab(self) -> bool:
        self.index += 1
        return True

    def is_opened(self) -> bool:
        return self.isopened

    def release(self) -> None:
        self.isopened = False

    def set(self, flag: int, value: int) -> bool:
        if cv2.CAP_PROP_POS_FRAMES == flag:
            if 0 <= value <= len(self.frames):
                self.index = value
                return True
            return False
        return False

    def get(self, flag: int) -> int | float | bool:
        if cv2.CAP_PROP_FRAME_COUNT == flag:
            return len(self.frames)
        elif cv2.CAP_PROP_POS_FRAMES == flag:
            return self.index
        elif cv2.CAP_PROP_FPS == flag:
            return 24.0
        return False

    def isOpened(self) -> bool:
        return self.isopened
