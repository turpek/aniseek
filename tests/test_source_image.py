from __future__ import annotations

import cv2
import numpy as np
import pytest

from aniseek.core.sources.image import ImageSource


def test_image_source_raises_on_non_existent_directory(tmp_path):
    """Verifica se RuntimeError é levantado quando o diretório não existe."""
    missing_dir = tmp_path / "does_not_exist"

    with pytest.raises(RuntimeError):
        ImageSource(missing_dir)


def test_image_source_raises_when_path_is_a_file(tmp_path):
    """Verifica se RuntimeError é levantado quando o caminho fornecido é um arquivo e não um diretório."""
    file_path = tmp_path / "image.png"
    file_path.touch()

    with pytest.raises(RuntimeError):
        ImageSource(file_path)


def test_image_source_empty_directory(tmp_path):
    """Verifica se diretório vazio resulta em frame_count zero e falha ao ler."""
    empty_dir = tmp_path / "empty_dir"
    empty_dir.mkdir()

    source = ImageSource(empty_dir)

    assert source.frame_count == 0
    assert source.fps == 24.0
    assert source.is_opened() is True

    ret, frame = source.read()
    assert ret is False
    assert frame is None

    assert source.grab() is False


def test_image_source_reads_and_orders_images(tmp_path):
    """Verifica leitura sequencial, ordenação alfabética e propriedades básicas de imagens."""
    img_dir = tmp_path / "images"
    img_dir.mkdir()

    # Criando 3 imagens sintéticas com cores distintas
    img0 = np.full((10, 10, 3), 10, dtype=np.uint8)
    img1 = np.full((10, 10, 3), 50, dtype=np.uint8)
    img2 = np.full((10, 10, 3), 100, dtype=np.uint8)

    cv2.imwrite(str(img_dir / "frame_02.png"), img2)
    cv2.imwrite(str(img_dir / "frame_00.png"), img0)
    cv2.imwrite(str(img_dir / "frame_01.jpg"), img1)

    source = ImageSource(img_dir, fps=30.0)

    assert source.frame_count == 3
    assert source.fps == 30.0

    ret0, frame0 = source.read()
    assert ret0 is True
    assert frame0 is not None
    assert frame0[0, 0, 0] == 10

    ret1, frame1 = source.read()
    assert ret1 is True
    assert frame1 is not None
    assert frame1[0, 0, 0] == 50

    ret2, frame2 = source.read()
    assert ret2 is True
    assert frame2 is not None
    assert frame2[0, 0, 0] == 100

    ret_eof, frame_eof = source.read()
    assert ret_eof is False
    assert frame_eof is None


def test_image_source_seek_and_grab(tmp_path):
    """Valida posicionamento com seek e avanço com grab sem decodificação."""
    img_dir = tmp_path / "images"
    img_dir.mkdir()

    for i in range(5):
        img = np.full((10, 10, 3), i * 10, dtype=np.uint8)
        cv2.imwrite(str(img_dir / f"img_{i:02d}.png"), img)

    source = ImageSource(img_dir)

    source.seek(2)
    ret, frame = source.read()
    assert ret is True
    assert frame[0, 0, 0] == 20

    assert source.grab() is True

    ret, frame = source.read()
    assert ret is True
    assert frame[0, 0, 0] == 40


def test_image_source_context_manager_and_release(tmp_path):
    """Valida liberação de recursos ao utilizar o context manager."""
    img_dir = tmp_path / "images"
    img_dir.mkdir()

    with ImageSource(img_dir) as source:
        assert source.is_opened() is True

    assert source.is_opened() is False
    assert source.read() == (False, None)
    assert source.grab() is False
