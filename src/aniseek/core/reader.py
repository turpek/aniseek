from __future__ import annotations

import traceback
from time import time

from aniseek.core.buffer import Buffer
from aniseek.core.interfaces.source import IFrameSource

ReaderTaskData = tuple[IFrameSource, int, int, set[int]]


def reader_task(buffer: Buffer, data: ReaderTaskData) -> None:
    """Reads frames from an IFrameSource and pushes them into the buffer.

    Args:
        buffer (Buffer): Buffer where decoded frames are stored.
        data (ReaderTaskData): Tuple containing:
            - source (IFrameSource): Frame provider.
            - start_frame (int): Initial frame index.
            - last_frame (int): Final frame index.
            - mapping_frames (set[int]): Set of valid frame IDs to read.

    Raises:
        IndexError: If start_frame is greater than or equal to source.frame_count.
    """
    buffer.set()
    source, start_frame, last_frame, mapping_frames = data
    frame_id, qsize = start_frame, 0
    start = time()

    if start_frame >= source.frame_count:
        raise IndexError("start_frame ultrapassou o limite de frames.")

    source.seek(start_frame)

    ret = None
    while True:
        if frame_id in mapping_frames:
            ret, frame = source.read()
            buffer.sput((frame_id, frame))
            qsize += 1
        else:
            source.grab()

        if buffer.log:
            print(qsize, qsize, frame_id, ret)
        if frame_id == last_frame:
            break
        elif qsize == buffer.maxsize:
            break
        elif frame_id == source.frame_count:
            break
        elif buffer.end_task.is_set():
            break
        frame_id += 1

    buffer.clear()
    if buffer.log:
        end = time()
        count = frame_id - start_frame
        print(f"\nLidos {count} em {end - start}s")
        print(f"{count / (end - start):.2f} FPS")


def reader(buffer: Buffer) -> None:
    """Consumes task data from the buffer channel and executes reader_task.

    Args:
        buffer (Buffer): Buffer instance managing the task queue and worker lifecycle.
    """
    try:
        while True:
            data = buffer.recv()
            if isinstance(data, tuple):
                reader_task(buffer, data)
            else:
                break
    except Exception as e:
        exc_info = traceback.format_exc()
        buffer._error.put(e, exc_info)
    finally:
        buffer.set()
        buffer.clear()
