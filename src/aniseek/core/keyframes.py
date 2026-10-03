from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from loguru import logger


def _read_vint(data: bytes, offset: int) -> tuple[int, int]:
    """Read an EBML variable-length integer (VINT) from bytes.

    Args:
        data (bytes): Byte buffer.
        offset (int): Starting index in data.

    Returns:
        tuple[int, int]: (decoded_value, byte_length).
    """
    first = data[offset]
    mask = 0x80
    vlen = 1
    while not (first & mask):
        mask >>= 1
        vlen += 1
    val = first & (mask - 1)
    for i in range(1, vlen):
        val = (val << 8) | data[offset + i]
    return val, vlen


def parse_mkv_cues(video_path: str | Path, fps: float) -> list[int] | None:
    """Parse keyframe indices directly from the EBML Cues element of a Matroska (.mkv) file.

    Reads the binary file without invoking external tools.

    Args:
        video_path (str | Path): Path to the .mkv video file.
        fps (float): Frames per second to convert timestamps into frame indices.

    Returns:
        list[int] | None: Sorted list of unique keyframe indices, or None if Cues is unavailable.
    """
    path = Path(video_path)
    if not path.is_file() or fps <= 0.0:
        return None

    try:
        with open(path, "rb") as f:
            header = f.read(65536)
            seg_idx = header.find(b"\x18\x53\x80\x67")
            if seg_idx == -1:
                return None
            _, seg_vlen = _read_vint(header, seg_idx + 4)
            seg_data_start = seg_idx + 4 + seg_vlen

            cues_id = b"\x1c\x53\xbb\x6b"
            cues_seek_idx = header.find(cues_id)
            if cues_seek_idx == -1:
                return None

            sp_idx = header.find(b"\x53\xac", cues_seek_idx)
            if sp_idx == -1:
                return None
            sp_data_size, sp_vlen = _read_vint(header, sp_idx + 2)
            seek_pos_bytes = header[sp_idx + 2 + sp_vlen: sp_idx + 2 + sp_vlen + sp_data_size]
            seek_pos_val = int.from_bytes(seek_pos_bytes, "big")

            cues_file_pos = seg_data_start + seek_pos_val
            f.seek(cues_file_pos)

            head = f.read(12)
            if not head.startswith(cues_id):
                return None
            cues_data_size, cues_vlen = _read_vint(head, 4)
            f.seek(cues_file_pos + 4 + cues_vlen)
            cues_data = f.read(cues_data_size)

        idx = 0
        dlen = len(cues_data)
        keyframe_indices: list[int] = []

        while idx < dlen:
            tag = cues_data[idx]
            idx += 1
            if tag == 0xBB:  # CuePoint
                cp_size, vlen = _read_vint(cues_data, idx)
                idx += vlen
                cp_end = idx + cp_size

                cue_time = None
                cue_track = 1
                while idx < cp_end:
                    subtag = cues_data[idx]
                    idx += 1
                    sub_size, vlen = _read_vint(cues_data, idx)
                    idx += vlen
                    sub_end = idx + sub_size

                    if subtag == 0xB3:  # CueTime (ms)
                        cue_time = int.from_bytes(cues_data[idx:sub_end], "big")
                    elif subtag == 0xB7:  # CueTrackPositions
                        t_idx = idx
                        while t_idx < sub_end:
                            ttag = cues_data[t_idx]
                            t_idx += 1
                            ttag_size, t_vlen = _read_vint(cues_data, t_idx)
                            t_idx += t_vlen
                            if ttag == 0xF7:  # CueTrack
                                cue_track = int.from_bytes(
                                    cues_data[t_idx: t_idx + ttag_size], "big"
                                )
                            t_idx += ttag_size
                    idx = sub_end

                if cue_time is not None and cue_track == 1:
                    frame_idx = int(round((cue_time / 1000.0) * fps))
                    keyframe_indices.append(frame_idx)
            else:
                elem_size, vlen = _read_vint(cues_data, idx)
                idx += vlen + elem_size

        if not keyframe_indices:
            return None

        sorted_kfs = sorted(set(keyframe_indices))
        if 0 not in sorted_kfs:
            sorted_kfs.insert(0, 0)
        logger.debug(
            f"Parsed {len(sorted_kfs)} keyframes directly from MKV binary Cues for {path.name}."
        )
        return sorted_kfs

    except Exception as exc:
        logger.debug(f"Failed to parse MKV binary Cues for {path.name}: {exc}")
        return None


def extract_keyframes_ffprobe(video_path: str | Path, fps: float) -> list[int] | None:
    """Extract keyframe frame indices from a video container using ffprobe.

    Used as fallback for non-Matroska containers.

    Args:
        video_path (str | Path): Path to the video file.
        fps (float): Frame rate used to convert packet timestamps into frame indices.

    Returns:
        list[int] | None: Sorted unique list of keyframe frame indices, or None if unavailable.
    """
    path = Path(video_path)
    if not path.is_file() or fps <= 0.0:
        return None

    if not shutil.which("ffprobe"):
        return None

    cmd = [
        "ffprobe",
        "-select_streams",
        "v:0",
        "-show_entries",
        "packet=pts_time,flags",
        "-of",
        "csv=p=0",
        str(path),
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            return None

        keyframes: list[int] = []
        for line in result.stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            parts = line.split(",")
            if len(parts) >= 2 and "K" in parts[1]:
                try:
                    pts = float(parts[0])
                    frame_idx = int(round(pts * fps))
                    keyframes.append(frame_idx)
                except ValueError:
                    continue

        sorted_kfs = sorted(set(keyframes))
        if 0 not in sorted_kfs:
            sorted_kfs.insert(0, 0)
        return sorted_kfs

    except Exception:
        return None


def extract_keyframe_indices(video_path: str | Path, fps: float) -> list[int] | None:
    """Extract keyframe frame indices from a video container.

    Tries reading binary Cues (for .mkv) first, then falls back to ffprobe if needed.

    Args:
        video_path (str | Path): Path to the video file.
        fps (float): Frame rate used to convert timestamps into frame indices.

    Returns:
        list[int] | None: Sorted unique list of keyframe frame indices, or None if extraction fails.
    """
    # 1. Pure Python binary Cues parsing (fastest, zero external dependencies)
    cues = parse_mkv_cues(video_path, fps)
    if cues is not None:
        return cues

    # 2. Subprocess ffprobe fallback (for mp4, avi, etc.)
    return extract_keyframes_ffprobe(video_path, fps)
