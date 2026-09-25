from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Generator

from aniseek.config import config
from aniseek.core.interfaces.source import IFrameSource
from aniseek.core.sources.image import ImageSource
from aniseek.core.sources.opencv import OpenCVVideoSource

VIDEO_EXTENSIONS: tuple[str, ...] = config.video_extensions


class SourceRegistry:
    """Registry and factory for default IFrameSource backends."""

    _instance: SourceRegistry | None = None

    def __new__(cls) -> SourceRegistry:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._video_source = OpenCVVideoSource
            cls._instance._image_source = ImageSource
        return cls._instance

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
        video: type[IFrameSource] | None = None,
        image: type[IFrameSource] | None = None,
    ) -> Generator[SourceRegistry, None, None]:
        """Temporarily override default sources within a context block.

        Args:
            video (type[IFrameSource] | None): Temporary video source class.
            image (type[IFrameSource] | None): Temporary image source class.

        Yields:
            SourceRegistry: The registry instance with temporary overrides.
        """
        old_video = self._video_source
        old_image = self._image_source
        try:
            if video is not None:
                self.video_source = video
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
    ) -> IFrameSource:
        """Resolve and instantiate the appropriate IFrameSource based on path.

        Args:
            path (str | Path): Path to a video file or image directory.
            buffersize (int | None): Buffer size for the frame source (defaults to config.buffersize).
            fps (float | None): Optional FPS override (defaults to detected video FPS or config.image_fps).

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

        if p.suffix.lower() in VIDEO_EXTENSIONS:
            return self._video_source(p, buffersize=actual_buffersize, fps=fps)

        if p.suffix:
            raise ValueError(
                f"Unsupported video file extension: {p.suffix}. "
                f"Expected one of: {', '.join(VIDEO_EXTENSIONS)}"
            )

        return self._video_source(p, buffersize=actual_buffersize, fps=fps)


source_registry = SourceRegistry()
