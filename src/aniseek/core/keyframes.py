from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from loguru import logger


def extract_keyframe_indices(video_path: str | Path, fps: float) -> list[int] | None:
    """Extract keyframe frame indices from a video container using ffprobe.

    Args:
        video_path (str | Path): Path to the video file.
        fps (float): Frame rate used to convert packet timestamps into frame indices.

    Returns:
        list[int] | None: Sorted unique list of keyframe frame indices, or None if extraction fails.
    """
    path = Path(video_path)
    if not path.is_file() or fps <= 0.0:
        return None

    if not shutil.which("ffprobe"):
        logger.debug("ffprobe not available in system PATH; skipping keyframe extraction.")
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
            logger.debug(f"ffprobe failed for {path} with code {result.returncode}")
            return None

        keyframes: list[int] = []
        for line in result.stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            # Format: <pts_time>,<flags> (e.g. 0.021000,K__)
            parts = line.split(",")
            if len(parts) >= 2 and "K" in parts[1]:
                try:
                    pts = float(parts[0])
                    frame_idx = int(round(pts * fps))
                    keyframes.append(frame_idx)
                except ValueError:
                    continue

        if not keyframes:
            return None

        sorted_keyframes = sorted(set(keyframes))
        logger.debug(
            f"Extracted {len(sorted_keyframes)} keyframes for {path.name} (last: {sorted_keyframes[-1]})."
        )
        return sorted_keyframes

    except Exception as exc:
        logger.debug(f"Unexpected error extracting keyframes with ffprobe: {exc}")
        return None
