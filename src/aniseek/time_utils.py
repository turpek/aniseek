from __future__ import annotations


def timestamp_to_seconds(timestamp: str) -> float:
    """Converte uma string de timestamp (SS, MM:SS ou HH:MM:SS.mmm) em segundos float."""
    timestamp = timestamp.strip()
    if not timestamp:
        raise ValueError("Timestamp não pode ser vazio.")

    if ":" in timestamp:
        parts = timestamp.split(":")
        if len(parts) == 2:
            minutes = float(parts[0])
            seconds = float(parts[1])
            if minutes < 0 or seconds < 0:
                raise ValueError(f"Componentes de tempo não podem ser negativos: '{timestamp}'.")
            return minutes * 60.0 + seconds
        elif len(parts) == 3:
            hours = float(parts[0])
            minutes = float(parts[1])
            seconds = float(parts[2])
            if hours < 0 or minutes < 0 or seconds < 0:
                raise ValueError(f"Componentes de tempo não podem ser negativos: '{timestamp}'.")
            return hours * 3600.0 + minutes * 60.0 + seconds
        else:
            raise ValueError(
                f"Formato de timestamp inválido: '{timestamp}'. Use 'MM:SS' ou 'HH:MM:SS'."
            )

    seconds = float(timestamp)
    if seconds < 0:
        raise ValueError(f"Tempo em segundos não pode ser negativo: '{timestamp}'.")
    return seconds


def seconds_to_timestamp(seconds: float) -> str:
    """Converte uma quantidade de segundos em string formatada 'HH:MM:SS.mmm'."""
    if seconds < 0:
        raise ValueError(f"Segundos não podem ser negativos: {seconds}.")

    total_ms = round(seconds * 1000)
    hours, remainder = divmod(total_ms, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    secs, millis = divmod(remainder, 1000)

    return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"


def time_to_seconds(time_val: float | int | str) -> float:
    """Normaliza um valor de tempo (segundos numéricos ou string de timestamp) para float."""
    if isinstance(time_val, (int, float)):
        if time_val < 0:
            raise ValueError(f"Tempo não pode ser negativo: {time_val}.")
        return float(time_val)
    elif isinstance(time_val, str):
        return timestamp_to_seconds(time_val)

    raise TypeError(
        f"Tipo de tempo inválido: esperava int, float ou str, recebeu {type(time_val).__name__}."
    )


def time_to_frame(time_val: float | int | str, fps: float) -> int:
    """Calcula o índice do frame mais próximo correspondente a um tempo e taxa de FPS."""
    if fps <= 0:
        raise ValueError(f"FPS deve ser maior que zero, recebido: {fps}.")

    seconds = time_to_seconds(time_val)
    return round(seconds * fps)


def frame_to_seconds(frame_id: int, fps: float) -> float:
    """Converte o índice de um frame para tempo em segundos."""
    if frame_id < 0:
        raise ValueError(f"frame_id não pode ser negativo: {frame_id}.")
    if fps <= 0:
        raise ValueError(f"FPS deve ser maior que zero, recebido: {fps}.")

    return frame_id / fps


def frame_to_timestamp(frame_id: int, fps: float) -> str:
    """Converte o índice de um frame diretamente para string de timestamp 'HH:MM:SS.mmm'."""
    seconds = frame_to_seconds(frame_id, fps)
    return seconds_to_timestamp(seconds)


def resolve_frame_range(
    total_frames: int,
    start: int | float | str | None,
    end: int | float | str | None,
    fps: float,
) -> tuple[int, int]:
    """Converte e normaliza os limites start e end (int, float ou str) em índices inteiros de frames."""
    if total_frames < 0:
        raise ValueError(f"total_frames não pode ser negativo: {total_frames}.")

    if start is None:
        start_idx = 0
    elif isinstance(start, int):
        start_idx = max(0, start)
    else:
        start_idx = max(0, time_to_frame(start, fps))

    if end is None:
        end_idx = total_frames
    elif isinstance(end, int):
        end_idx = min(total_frames, end)
    else:
        end_idx = min(total_frames, time_to_frame(end, fps))

    return start_idx, end_idx
