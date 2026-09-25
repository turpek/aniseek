from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager
from typing import Any

DEFAULT_BUFFERSIZE: int = 30
DEFAULT_IMAGE_FPS: float = 24.0
DEFAULT_VIDEO_EXTENSIONS: tuple[str, ...] = (
    ".mp4",
    ".mkv",
    ".avi",
    ".mov",
    ".webm",
    ".flv",
    ".wmv",
    ".m4v",
    ".ts",
)
DEFAULT_IMAGE_EXTENSIONS: tuple[str, ...] = (
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
    ".bmp",
)


class Config:
    """Configuração global centralizada do aniseek."""

    def __init__(self) -> None:
        self._buffersize: int = DEFAULT_BUFFERSIZE
        self._image_fps: float = DEFAULT_IMAGE_FPS
        self._video_extensions: tuple[str, ...] = DEFAULT_VIDEO_EXTENSIONS
        self._image_extensions: tuple[str, ...] = DEFAULT_IMAGE_EXTENSIONS

    @property
    def buffersize(self) -> int:
        """Tamanho padrão da janela deslizante do buffer de vídeo."""
        return self._buffersize

    @buffersize.setter
    def buffersize(self, value: int) -> None:
        if not isinstance(value, int) or value <= 0:
            raise ValueError(f"buffersize deve ser um inteiro positivo, recebeu: {value}")
        self._buffersize = value

    @property
    def image_fps(self) -> float:
        """FPS padrão para sequências de imagem quando não fornecido pelo usuário."""
        return self._image_fps

    @image_fps.setter
    def image_fps(self, value: float) -> None:
        if value <= 0:
            raise ValueError(f"image_fps deve ser positivo, recebeu: {value}")
        self._image_fps = float(value)

    @property
    def video_extensions(self) -> tuple[str, ...]:
        """Extensões de arquivo reconhecidas como vídeo."""
        return self._video_extensions

    @video_extensions.setter
    def video_extensions(self, value: tuple[str, ...]) -> None:
        self._video_extensions = tuple(ext.lower() for ext in value)

    @property
    def image_extensions(self) -> tuple[str, ...]:
        """Extensões de arquivo reconhecidas como imagem."""
        return self._image_extensions

    @image_extensions.setter
    def image_extensions(self, value: tuple[str, ...]) -> None:
        self._image_extensions = tuple(ext.lower() for ext in value)

    def reset(self) -> None:
        """Restaura todas as configurações para seus valores padrão de fábrica."""
        self._buffersize = DEFAULT_BUFFERSIZE
        self._image_fps = DEFAULT_IMAGE_FPS
        self._video_extensions = DEFAULT_VIDEO_EXTENSIONS
        self._image_extensions = DEFAULT_IMAGE_EXTENSIONS

    @contextmanager
    def __call__(self, **kwargs: Any) -> Generator[Config, None, None]:
        """Aplica configurações temporárias dentro de um bloco 'with'."""
        old_state: dict[str, Any] = {}
        for key in kwargs:
            if not hasattr(self, key) or key.startswith("_"):
                raise AttributeError(f"Opção de configuração inválida: '{key}'")
            old_state[key] = getattr(self, key)

        try:
            for key, value in kwargs.items():
                setattr(self, key, value)
            yield self
        finally:
            for key, old_value in old_state.items():
                setattr(self, key, old_value)


config = Config()
