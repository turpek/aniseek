from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Generator

from aniseek.config import config
from aniseek.core.interfaces.source import IFrameSource
from aniseek.core.sources.image import ImageSource
from aniseek.core.sources.opencv import OpenCVVideoSource
from aniseek.core.sources.pyav import PyAVVideoSource

VIDEO_EXTENSIONS: tuple[str, ...] = config.video_extensions

AVAILABLE_VIDEO_BACKENDS: dict[str, type[IFrameSource]] = {
    "opencv": OpenCVVideoSource,
    "pyav": PyAVVideoSource,
}


class SourceRegistry:
    """Registry and factory for default IFrameSource backends."""

    _instance: SourceRegistry | None = None

    def __new__(cls) -> SourceRegistry:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._video_source = OpenCVVideoSource
            cls._instance._image_source = ImageSource
        return cls._instance

    @classmethod
    def resolve_video_backend(
        cls, backend: type[IFrameSource] | str | None
    ) -> type[IFrameSource]:
        """Resolve a video backend class from a string name or class type.

        Args:
            backend: Backend class, string identifier ('opencv', 'pyav'), or None for default.

        Returns:
            type[IFrameSource]: Resolved backend class.

        Raises:
            ValueError: If the string name is not in AVAILABLE_VIDEO_BACKENDS.
            TypeError: If backend is not a subclass of IFrameSource.
        """
        if backend is None:
            return cls().video_source
        if isinstance(backend, str):
            key = backend.strip().lower()
            if key in AVAILABLE_VIDEO_BACKENDS:
                return AVAILABLE_VIDEO_BACKENDS[key]
            raise ValueError(
                f"Unknown video backend '{backend}'. Expected one of: {list(AVAILABLE_VIDEO_BACKENDS.keys())}"
            )
        if isinstance(backend, type) and issubclass(backend, IFrameSource):
            return backend
        raise TypeError(
            f"backend must be a subclass of IFrameSource or one of {list(AVAILABLE_VIDEO_BACKENDS.keys())}, got {backend}"
        )

    @property
    def video_source(self) -> type[IFrameSource]:
        """Class used as default backend for video files."""
        return self._video_source

    @video_source.setter
    def video_source(self, source_cls: type[IFrameSource]) -> None:
        if not issubclass(source_cls, IFrameSource):
            raise TypeError("video_source must be a subclass of IFrameSource")
        self._video_source = source_cls

    @property
    def image_source(self) -> type[IFrameSource]:
        """Class used as default backend for image directories."""
        return self._image_source

    @image_source.setter
    def image_source(self, source_cls: type[IFrameSource]) -> None:
        if not issubclass(source_cls, IFrameSource):
            raise TypeError("image_source must be a subclass of IFrameSource")
        self._image_source = source_cls

    def reset(self) -> None:
        """Reset registered sources to initial defaults."""
        self._video_source = OpenCVVideoSource
        self._image_source = ImageSource

    @contextmanager
    def use(
        self,
        *,
        video: type[IFrameSource] | str | None = None,
        image: type[IFrameSource] | None = None,
    ) -> Generator[SourceRegistry, None, None]:
        """Temporarily override default sources within a context block.

        Args:
            video (type[IFrameSource] | str | None): Temporary video source class or name.
            image (type[IFrameSource] | None): Temporary image source class.

        Yields:
            SourceRegistry: The registry instance with temporary overrides.
        """
        old_video = self._video_source
        old_image = self._image_source
        try:
            if video is not None:
                self.video_source = self.resolve_video_backend(video)
            if image is not None:
                self.image_source = image
            yield self
        finally:
            self._video_source = old_video
            self._image_source = old_image

    def create_source(
        self,
        path: str | Path,
        *,
        buffersize: int | None = None,
        fps: float | None = None,
        backend: type[IFrameSource] | str | None = None,
    ) -> IFrameSource:
        """Resolve and instantiate the appropriate IFrameSource based on path and backend.

        Args:
            path (str | Path): Path to a video file or image directory.
            buffersize (int | None): Buffer size for the frame source (defaults to config.buffersize).
            fps (float | None): Optional FPS override (defaults to detected video FPS or config.image_fps).
            backend (type[IFrameSource] | str | None): Video decoding backend ('opencv', 'pyav', or class).

        Returns:
            IFrameSource: Instantiated frame source.

        Raises:
            FileNotFoundError: If the path does not exist.
            ValueError: If the file extension is not a recognized video format.
        """
        actual_buffersize = buffersize if buffersize is not None else config.buffersize
        p = Path(path)
        if p.is_dir():
            actual_fps = fps if fps is not None else config.image_fps
            return self._image_source(p, buffersize=actual_buffersize, fps=actual_fps)

        video_cls = self.resolve_video_backend(backend)

        if p.suffix.lower() in VIDEO_EXTENSIONS:
            return video_cls(p, buffersize=actual_buffersize, fps=fps)

        if p.suffix:
            raise ValueError(
                f"Unsupported video file extension: {p.suffix}. "
                f"Expected one of: {', '.join(VIDEO_EXTENSIONS)}"
            )

        return video_cls(p, buffersize=actual_buffersize, fps=fps)


source_registry = SourceRegistry()
