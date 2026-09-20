from collections import deque
from pathlib import Path

from aniseek.custom_exceptions import PlaylistError
from aniseek.editing.utils import VideoInfo


class Playlist:
    def __init__(self, videos: list[str | Path], labels: list[str | None] = None):
        """
        Playlist é a classe responsavel por gerencia a lista de reprodução de vídeos.
        Com ela é possível fazer

            1. Passar para o próximo vídeo.
            2. Voltar para o vídeo anterior.
            3. Ordenar a lista de reprodução pelo nome.
            4. Ordenar a lista de reprodução pela data.
            5. Inverter a lista de reprodução.
            6. Reproduzir o vídeo de forma aleatória.

        Args:
            videos (list[str | Path]): é o caminho até o arquivo de vídeo.
            lables (list[str | None] = None): são os rótulos das seções dos vídeos, a mesmas
                tem a relação de 1:1 com o argumento `videos`. se o elemento for None, o mesmo
                assumerá o valor de 'section_x' onde x é um valor inteiro
        """

        if len(videos) == 0:
            raise PlaylistError('the video list is empty')

        self.__right_videos = deque(maxlen=len(videos))
        self.__left_videos = deque(maxlen=len(videos))
        self.__video_file = None

        if labels:
            for video, label in zip(videos, labels):
                self.__right_videos.append(VideoInfo(Path(video), label))
        else:
            for video in videos:
                self.__right_videos.append(VideoInfo(Path(video), 'video_01'))

        self.__next_video_name()

    def __next_video_name(self):
        if len(self.__right_videos) > 0:
            if self.__video_file is not None:
                self.__left_videos.append(self.__video_file)
            self.__video_file = self.__right_videos.popleft()

    def __prev_video_name(self):
        if len(self.__left_videos) > 0:
            if self.__video_file is not None:
                self.__right_videos.appendleft(self.__video_file)
            self.__video_file = self.__left_videos.pop()

    def video_name(self) -> str | None:
        """
        Método que retorna o nome do vídeo para a reprodução atual.

        Returns:
            str: é o nome do arquivo.
            None: para a lista de reprodução vazia.
        """
        if self.__video_file:
            return self.__video_file.path

    def get_video_info(self) -> VideoInfo:
        return self.__video_file

    def next_video(self) -> None:
        """
        Passa para o próximo vídeo da lista de reprodução, para isso passa o nome do
        arquivo para o método open do ´VideoCon´, caso a lista de reprodução seja vazia,
        o nome será None

        Args:
            video_player (VideoCon): objeto responsavel pela reprodução do vídeo.

        Returns:
            None
        """
        self.__next_video_name()

    def prev_video(self) -> None:
        """
        Passa para o vídeo anterior da lista de reprodução, para isso passa o nome do
        arquivo para o método open do ´VideoCon´, caso a lista de reprodução seja vazia,
        o nome será None

        Args:
            video_player (VideoCon): objeto responsavel pela reprodução do vídeo.

        Returns:
            None
        """
        self.__prev_video_name()

    def is_beginning(self) -> bool:
        """
        Verifica se já chegou no começo da lista de reprodução

        Returns:
            True: Se chegou no começo da lista.
            False: Se não chegou no começo da lista.
        """
        return len(self.__left_videos) == 0

    def is_end(self) -> bool:
        """
        Verifica se já chegou no final da lista de reprodução

        Returns:
            True: Se chegou no final da lista.
            False: Se não chegou no final da lista.
        """
        return len(self.__right_videos) == 0
