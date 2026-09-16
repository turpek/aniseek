import bisect
from array import array

from aniseek.custom_exceptions import InvalidFrameIdError
from aniseek.interfaces import IVideoBuffer


class FrameMapper:
    """Classe que implementa um mapa que contém os ids de frames de um vídeo."""

    def __init__(self, frame_ids: list[int], frame_count: int) -> None:
        self.__frame_count = None
        self.__frame_ids = None
        self.__frame_id = None
        self.__mapping = None
        self.__set_mapping(frame_ids, frame_count)

    def __getitem__(self, index: int | slice) -> int | array:
        """
        Obtem frame_id's do `FrameMapper` na posições do index, caso não
        exista um frame_id na posição requerida, um `IndexError` será
        levantada.

        Args:
            index (int | slice): valor usado para acessar os ids do `FrameMapper`.

        Returns:
            int: retorna um inteiro se index for uma instancia de int
            array: retorna um array contendo os frame_ids, caso index seja uma instancia de slice
        """
        if len(self.__frame_ids) > 0:
            return self.__frame_ids[index]

    def __len__(self) -> int:
        """
        Retorna o número de elementos contidos no mapping
        """
        return len(self.__frame_ids)

    def __contains__(self, frame_id: int) -> bool:
        """
        Verifica se um item está no `FrameMapper`.

        Args:
            frame_id (int): id do frame da qual se deseja verificar, se está
                contido no `FrameMapper`.

        Retuns:
            bool: retorna True caso `frame_id` esteja no conjunto do `FrameMapper`,
                caso contrário False é retornado.
        """
        return frame_id in self.__mapping

    def __get_last_frame_index(self, frame_array: array) -> int:
        """
        Método interno que calcula o indice a esquerda do `frame_count`
        no frame_array, se `frame_count` não estiver presente, o último
        indice é retornado.

        Args:
            frame_array (array[int]): um array de inteiros que representa o
                id dos frames.

        Returns:
            int: indice à esquerda do `frame_count`, caso o mesmo não esteja no
                `frame_array`, o último elemento é retornado.
        """
        return bisect.bisect_right(frame_array, self.__frame_count - 1)

    def __set_frame_indexes(self, frame_ids: list[int]) -> None:
        """Método interno para criar um array contendo os frame_ids."""
        frame_array = array('l', sorted(frame_ids))
        index = self.__get_last_frame_index(frame_array)
        self.__frame_ids = frame_array[:index]

    def __set_mapping(self, frame_ids: list[int], frame_count: int) -> None:
        """Método interno para setar o mapping."""
        self.__frame_count = frame_count
        self.__set_frame_indexes(frame_ids)
        self.__mapping = set(self.__frame_ids)

    def __set_buffers(self, vbuffers: list[IVideoBuffer]) -> None:
        """Método interno para setar o __frame_id nos vbuffers."""
        if len(vbuffers) == 0:
            raise ValueError('vbuffers list must not be empty.')
        for vbuffer in vbuffers:
            if isinstance(vbuffer, IVideoBuffer):
                vbuffer.set_frame_id()
            else:
                raise TypeError('vbuffers must be an instance of IVideoBuffer')

    def empty(self):
        return len(self.__mapping) == 0

    def set_mapping(self, frame_ids: list[int], frame_count: int, vbuffers: list[IVideoBuffer]) -> None:
        """
        Define um novo conjunto para mapear os frame_ids.

        Args:
            frame_ids (list[int]): uma lista que contem os ids dos frames, a quais devem
                assumir valores inteiros maiores que zero.
            frame_count (int): número de frames que à mídia em questão tema.

        Returns:
            None

        Raises:
            TypeError: Se vbuffers não forem instancia de IVideoBuffer.
        """
        self.__set_mapping(frame_ids, frame_count)
        # self.__set_buffers(vbuffers)

    def get_mapping(self) -> set:
        """
        Retorna uma copiá do set, que contem os frame_ids contidos no `FrameMapper`.

        Returns:
            set: um conjunto que contem todos os frame_ids do `FrameMapper`
        """
        return self.__mapping.copy()

    @property
    def frame_ids(self) -> array:
        """
        Property que retorna o array contendo todos os id dos frames.

        Returns:
            array: id's dos frames de um vídeo.
        """
        return self.__frame_ids

    def add(self, frame_id: int) -> None:
        """
        Adiciona um novo frame_id no `FrameMapper`, desde que o mesmo seja menor que
        o número de frames da mídia em questão, caso contrário `InvalidFrameIdError` será
        levantada.

        Args:
            frame_id (int): indica o id do frame a ser colocado no mapper.

        Returns:
            None
        """
        if frame_id >= self.__frame_count:
            raise InvalidFrameIdError('frame_id must be less than frame_count')
        elif frame_id < 0:
            raise InvalidFrameIdError('frame_id must be greater than zero')
        elif frame_id in self.__mapping:
            raise InvalidFrameIdError(f'frame_id "{frame_id}" is already in the mapping')
        bisect.insort(self.__frame_ids, frame_id)
        self.__mapping.add(frame_id)

    def remove(self, frame_id: int) -> None:
        """
        Caso `frame_id` esteja contido em `FrameMapper`, o mesmo será removido,
        caso contrário nada é feito.

        Args:
            frame_id (int)> indica o id do frame a ser removido do mapper.

        Returns:
            None
        """
        if frame_id in self.__mapping:
            del self.__frame_ids[bisect.bisect_left(self.__frame_ids, frame_id)]
            self.__mapping.remove(frame_id)
        elif isinstance(frame_id, int):
            ...

    def set_frame_id(self, frame_id: int) -> None:
        self.__frame_id = frame_id

    @property
    def frame_id(self) -> None | int:
        return self.__frame_id
