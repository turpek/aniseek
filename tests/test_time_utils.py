from __future__ import annotations

import pytest

from aniseek.time_utils import (
    frame_to_seconds,
    frame_to_timestamp,
    resolve_frame_range,
    seconds_to_timestamp,
    time_to_frame,
    time_to_seconds,
    timestamp_to_seconds,
)


@pytest.mark.parametrize(
    ("input_str", "expected_seconds"),
    [
        ("0", 0.0),
        ("45", 45.0),
        ("45.5", 45.5),
        ("01:30", 90.0),
        ("01:15.5", 75.5),
        ("00:01:15.500", 75.5),
        ("01:00:00", 3600.0),
        ("01:30:15.250", 5415.25),
    ],
    ids=[
        "seconds_zero",
        "seconds_int",
        "seconds_float",
        "mm_ss",
        "mm_ss_ms",
        "hh_mm_ss_ms",
        "hh_mm_ss_exact_hour",
        "hh_mm_ss_full",
    ],
)
def test_timestamp_to_seconds_valid(input_str, expected_seconds):
    """Valida conversão de múltiplos formatos de string de timestamp para segundos float."""
    result = timestamp_to_seconds(input_str)

    assert result == pytest.approx(expected_seconds)


@pytest.mark.parametrize(
    "invalid_input",
    ["", "   ", "abc", "01:02:03:04", "-10", "-01:00", "01:-05"],
    ids=["empty", "spaces", "non_numeric", "too_many_colons", "negative_sec", "negative_mm", "negative_ss"],
)
def test_timestamp_to_seconds_invalid(invalid_input):
    """Verifica se strings de timestamp inválidas ou negativas levantam ValueError."""
    with pytest.raises(ValueError):
        timestamp_to_seconds(invalid_input)


@pytest.mark.parametrize(
    ("seconds", "expected_timestamp"),
    [
        (0.0, "00:00:00.000"),
        (75.5, "00:01:15.500"),
        (3661.125, "01:01:01.125"),
        (5415.250, "01:30:15.250"),
    ],
    ids=["zero", "mm_ss_ms", "hh_mm_ss_ms", "full_hour"],
)
def test_seconds_to_timestamp_valid(seconds, expected_timestamp):
    """Valida formatação de segundos para string de timestamp HH:MM:SS.mmm."""
    result = seconds_to_timestamp(seconds)

    assert result == expected_timestamp


def test_seconds_to_timestamp_negative_raises():
    """Garante que fornecer segundos negativos para formatação levanta ValueError."""
    with pytest.raises(ValueError):
        seconds_to_timestamp(-1.0)


@pytest.mark.parametrize(
    ("time_val", "expected_seconds"),
    [
        (10, 10.0),
        (25.5, 25.5),
        ("01:30", 90.0),
    ],
    ids=["int_input", "float_input", "str_input"],
)
def test_time_to_seconds_types(time_val, expected_seconds):
    """Valida normalização de diferentes tipos de entrada numérica e textual para segundos."""
    result = time_to_seconds(time_val)

    assert result == pytest.approx(expected_seconds)


def test_time_to_seconds_invalid_type_raises():
    """Garante que tipos incompatíveis fornecidos a time_to_seconds levantam TypeError."""
    with pytest.raises(TypeError):
        time_to_seconds([10])


@pytest.mark.parametrize(
    ("time_val", "fps", "expected_frame"),
    [
        (0, 24.0, 0),
        (1.0, 24.0, 24),
        ("01:00", 24.0, 1440),
        ("01:15.5", 24.0, 1812),
        (1.5, 30.0, 45),
        ("00:00:01.000", 60.0, 60),
    ],
    ids=["zero_fps24", "1s_fps24", "1m_fps24", "1m15s_fps24", "1.5s_fps30", "1s_fps60"],
)
def test_time_to_frame_calculation(time_val, fps, expected_frame):
    """Valida cálculo do frame id correto a partir de tempo e FPS variados."""
    result = time_to_frame(time_val, fps)

    assert result == expected_frame


def test_time_to_frame_zero_or_negative_fps_raises():
    """Garante que FPS zero ou negativo levanta ValueError em time_to_frame."""
    with pytest.raises(ValueError):
        time_to_frame(10, 0.0)


@pytest.mark.parametrize(
    ("frame_id", "fps", "expected_seconds"),
    [
        (0, 24.0, 0.0),
        (24, 24.0, 1.0),
        (1812, 24.0, 75.5),
        (60, 30.0, 2.0),
    ],
    ids=["frame_0", "frame_24_fps24", "frame_1812_fps24", "frame_60_fps30"],
)
def test_frame_to_seconds(frame_id, fps, expected_seconds):
    """Valida conversão de frame id para segundos com base no FPS."""
    result = frame_to_seconds(frame_id, fps)

    assert result == pytest.approx(expected_seconds)


def test_frame_to_seconds_negative_frame_raises():
    """Garante que frame id negativo levanta ValueError em frame_to_seconds."""
    with pytest.raises(ValueError):
        frame_to_seconds(-5, 24.0)


def test_frame_to_timestamp_integration():
    """Valida conversão direta de frame id para timestamp formatado HH:MM:SS.mmm."""
    result = frame_to_timestamp(1812, 24.0)

    assert result == "00:01:15.500"


@pytest.mark.parametrize(
    ("total_frames", "start", "end", "fps", "expected_range"),
    [
        (1000, None, None, 24.0, (0, 1000)),
        (1000, 50, 200, 24.0, (50, 200)),
        (1000, -10, 2000, 24.0, (0, 1000)),
        (1000, "00:01", "00:02", 24.0, (24, 48)),
        (1000, 1.5, 3.0, 30.0, (45, 90)),
        (1000, "01:00", 500, 24.0, (1440, 500)),
    ],
    ids=["none_defaults", "int_bounds", "clamping", "timestamp_strings", "float_seconds", "mixed_types"],
)
def test_resolve_frame_range(total_frames, start, end, fps, expected_range):
    """Valida normalização e conversão de start e end em índices de frames sob diferentes formatos."""
    result = resolve_frame_range(total_frames, start, end, fps)

    assert result == expected_range


def test_resolve_frame_range_negative_total_frames():
    """Garante que total_frames negativo levanta ValueError em resolve_frame_range."""
    with pytest.raises(ValueError):
        resolve_frame_range(-10, 0, 10, 24.0)
