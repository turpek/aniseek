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


def test_parse_mkv_cues_binary_success(tmp_path):
    """Extrai quadros-chave diretamente de binario MKV com bloco Cues."""
    dummy_mkv = tmp_path / "synthetic.mkv"
    cue_point = b"\xbb\x89\xb3\x82\x03\xe8\xb7\x83\xf7\x81\x01"
    cues_data = b"\x1c\x53\xbb\x6b" + bytes([0x80 | len(cue_point)]) + cue_point
    data = bytearray(b"\x18\x53\x80\x67\x80")
    data.extend(b"\x00" * 5)
    data.extend(b"\x1c\x53\xbb\x6b\x53\xac\x81\x20")
    data.extend(b"\x00" * (37 - len(data)))
    data.extend(cues_data)
    dummy_mkv.write_bytes(bytes(data))

    result = extract_keyframe_indices(dummy_mkv, 24.0)
    assert result == [0, 24]
