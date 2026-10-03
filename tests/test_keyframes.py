from __future__ import annotations

import subprocess

from aniseek.core.keyframes import extract_keyframe_indices


def test_extract_keyframe_indices_missing_file():
    """Retorna None quando o arquivo de video nao existe."""
    assert extract_keyframe_indices("/path/to/missing_video.mp4", 24.0) is None


def test_extract_keyframe_indices_invalid_fps(tmp_path):
    """Retorna None quando fps e zero ou negativo."""
    dummy = tmp_path / "video.mp4"
    dummy.touch()
    assert extract_keyframe_indices(dummy, 0.0) is None
    assert extract_keyframe_indices(dummy, -24.0) is None


def test_extract_keyframe_indices_ffprobe_missing(tmp_path, monkeypatch):
    """Retorna None quando ffprobe nao esta disponivel no PATH."""
    dummy = tmp_path / "video.mp4"
    dummy.touch()
    monkeypatch.setattr("shutil.which", lambda _: None)
    assert extract_keyframe_indices(dummy, 24.0) is None


def test_extract_keyframe_indices_ffprobe_failure(tmp_path, monkeypatch):
    """Retorna None quando ffprobe falha com codigo de erro."""
    dummy = tmp_path / "video.mp4"
    dummy.touch()
    fake_result = subprocess.CompletedProcess(
        args=["ffprobe"],
        returncode=1,
        stdout="",
        stderr="Error",
    )
    monkeypatch.setattr("subprocess.run", lambda *args, **kwargs: fake_result)
    assert extract_keyframe_indices(dummy, 24.0) is None


def test_extract_keyframe_indices_success(tmp_path, monkeypatch):
    """Extrai e calcula indices inteiros ordenados a partir de saida ffprobe."""
    dummy = tmp_path / "video.mp4"
    dummy.touch()
    stdout_sample = (
        "0.000000,K__\n"
        "0.041708,___\n"
        "1.000000,K__\n"
        "2.500000,K__\n"
        "invalid_line\n"
        ",K__\n"
    )
    fake_result = subprocess.CompletedProcess(
        args=["ffprobe"],
        returncode=0,
        stdout=stdout_sample,
        stderr="",
    )
    monkeypatch.setattr("subprocess.run", lambda *args, **kwargs: fake_result)

    result = extract_keyframe_indices(dummy, 24.0)
    assert result == [0, 24, 60]
