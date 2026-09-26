"""Este módulo fornece a classe VideoBufferLeft.

A classe VideoBufferLeft é responsável por armazenar os frames lidos atráves do
módulo da opencv, a mesma tem a seguinte estrutura:

    class VideoBufferRight(Queue):
        +cap: string que armazena o caminho até o arquivo de mídeo a ser lido.
        +name: string que da o nome do buffer.
        +buffersize: inteiro que determina o tamanho do buffer.
        +sequence_frames_ord: lista que fornece os frames a serem lidos.
        +sequence_frames: dicionário que mapeia os frames a serem lidos.
        +process: Processo que roda em paralelo com o programa principal, na qual os frames serão lidos
        -_start_frame: inteiro que armazenao o id do primeiro frame a ser lido
        +parent_conn: pipe para comunicação com o processo descrito acima
        +child_conn: pipe passado para o processo descrito acima

        +start_frame() int: metodo que retorna o id do primeiro frame a ser lido

"""


import bisect
from threading import Semaphore, Thread

from loguru import logger
from numpy import ndarray

from aniseek.core.buffer import BufferLeft
from aniseek.core.frame_mapper import FrameMapper
from aniseek.core.interfaces.buffer import IVideoBuffer
from aniseek.core.interfaces.source import IFrameSource
from aniseek.core.reader import reader
from aniseek.custom_exceptions import VideoBufferError


class VideoBufferLeft(IVideoBuffer):
    """
    O VideoBufferLeft começa
    """

    def __init__(self,
                 source: IFrameSource,
                 frame_mapping: FrameMapper,
                 semaphore: Semaphore, *,
                 buffersize=25,
                 bufferlog=False,
                 name='buffer'):

        # Definições das variaveis que lidam com o Thread
        logger.debug("Initializing VideoBufferLeft")
        self.source = source
        self.cap = source
        self._frame_count = source.frame_count
        self.name = name
        self.buffersize = buffersize
        self._buffer = BufferLeft(semaphore, maxsize=buffersize, log=bufferlog)

        # Definições das variaveis responsavel pela criação do buffer
        # self.__frame_id = frame_mapping[0]
        self.__frame_id = frame_mapping[0]
        self._set_frame = None
        self.__set_end_frame = None
        self.__special_case = None

        # Atributos usados para determinar os frames que serao armazenados no buffer
        self.__mapping = frame_mapping

        self.thread = None
        self.__start()

    def __del__(self):
        self._buffer.send(False)

    def __len__(self):
        return len(self._buffer)

    def __repr__(self):
        return f'VideoBufferLeft("{self.frame_id}")'

    def __getitem__(self, index: int) -> int:
        """
        Retorna os frame_id do buffer, caso o mesmo esteja vazio -1 é retornado.

        Args:
            index (int): Indice do frame na qual se deseja conhecer o frame_id
                se o mesmo não for inteiro, -1 é retornado.

        Returns:
            int
                - Em caso de sucesso um número inteiro maior que zero é retornado.
                - Em caso de falha -1 é retornado.

        """
        if self._buffer.empty() or not isinstance(index, int):
            return None
        return self._buffer[index]

    def __start(self) -> None:
        """
        Inicia a thread

        Returns:
            None
        """
        if self.thread is None:
            logger.debug('Starting buffer thread')
            args = (self._buffer,)
            self.thread = Thread(target=reader, args=args)
            self.thread.start()

    def __calc_frame(self, frame_id: int) -> int | None:
        """
        Calcula o start_fame dado um frame_id

        Args:
            frame_id int: Identificador do frame.

        Returns:
            int: Se o `FrameMapper` não estiver vazio
            None: Se o `FrameMapper` estiver vazio
        """
        logger.debug('Calculating VideoBufferLeft window range')
        if self.__mapping.empty():
            return None

        frame_ids = self.__mapping.frame_ids
        temp_idx = bisect.bisect_left(frame_ids, frame_id)
        if (idx := temp_idx - self.buffersize) > 0:
            try:
                frame_id = frame_ids[idx]
            except IndexError:
                raise IndexError('frame_id does not belong to the lot range.')
        else:
            frame_id = frame_ids[0]

        # calculo para o metodo end_frame
        idx = temp_idx
        if idx < 1:
            self.__set_end_frame = frame_ids[0]
        elif idx < self.buffersize:
            # Por padrão o VideoBufferLeft é aberto para end_frame, para
            # manter tal caracteristica devemos tirar 1 do índice, para os
            # casos onde o conjuto de frames é menor que o tamanho do buffer
            self.__set_end_frame = frame_ids[idx - 1]

            # Caso Especial onde idx = 1 com isso idx - 1 == 0, fazendo com que
            # end_frame == start_frame, com isso nenhum frame sera lido, nesse caso
            # precisamos tratar esse caso de modo diferente no método run
            if (idx - 1) == 0:
                logger.debug('Setting variable for special case')
                self.__special_case = frame_ids[idx]
        else:
            self.__set_end_frame = frame_ids[idx - 1]

        return frame_id

    def is_task_complete(self) -> bool:
        """
        Checa se todos os frames do lotes foram consumidos.

        Returns:
            bool
        """
        if len(self.__mapping) <= 1 and self._buffer.empty():
            return True
        elif isinstance(self.__frame_id, int) and self.__frame_id < self.__mapping[0]:
            self.__frame_id = self.__mapping[0]
        return self.__frame_id == self.__mapping[0]

    def is_done(self) -> bool:
        """
        Verifica se todos os frames do lote foram processados.

        Returns:
            bool
        """
        if isinstance(self._set_frame, int):
            # Devemos considerar o caso especial, para saber mais, veja o método __calc_frame
            set_end_frame = self.__set_end_frame if self.__special_case is None else self.__special_case
            return set_end_frame == self._set_frame
        elif not self._buffer.empty():
            return self._buffer[-1] == self.__mapping[0]
        else:
            return self.is_task_complete()

    def do_task(self) -> bool:
        """
        Verifica se uma task pode ser iniciada.

        Returns:
            bool
        """
        return self._buffer.do_task() and self.is_done() is False

    def set_frame_id(self) -> None:
        """
        Método usado dentro de `FrameMapper` para setar o __frame_id usando o
        novo mapping.

        Returns:
            None
        """
        self.__frame_id = self.__mapping[0]

    def set(self, frame_id: int) -> None:
        """
        Coloco o frame a esquerda de frame_id como start_frame no próximo ciclo de leitura dos frames.
        O ínicio de um novo ciclo ocorre quando o buffer esta vazio! se o frame_id não
        estiver no lote o valor setado será o valor a esquerda mais próximo do mesmo. Esse método exclui
        os valores extremos definidos no `FrameMapper`, deve-se usar o em conjunto com `VideoBufferRight`
        para obter tais frames!

        Args:
            frame_id (int): id do frame a ser lido no próximo ciclo, ou seja, qu
        """
        logger.debug(f"Setting target frame id '{frame_id}'")
        if not isinstance(frame_id, int):
            raise TypeError('frame_id must be an integer')
        elif frame_id < 0:
            raise VideoBufferError(f"frame_id '{frame_id}' must be greater than 0.")
        self._set_frame = self.__calc_frame(frame_id)
        self._buffer.clear_buffer()
        self.__frame_id = frame_id if self.__mapping[0] == frame_id else None
        self._buffer.no_block_task(True)

    def end_frame(self) -> int:
        logger.debug("Getting end_frame")
        if isinstance(self._set_frame, int):
            return self.__set_end_frame
        elif self._buffer.empty() is False:
            frame_ids = self.__mapping.frame_ids
            idx = bisect.bisect_left(frame_ids, self._buffer[-1]) - 1
            if idx < 0:
                return frame_ids[0]
            else:
                return frame_ids[idx]
        elif isinstance(self.__frame_id, int) and self.__frame_id > self.__mapping[0]:
            return self.__frame_id - 1
        return self.__mapping[0]

    def start_frame(self) -> int:
        logger.debug("Getting start_frame")
        if isinstance(self._set_frame, int):
            return self._set_frame
        elif self._buffer.empty() is False:
            return self.__calc_frame(self._buffer[-1])
        elif isinstance(self.__frame_id, int):
            return self.__calc_frame(self.__frame_id)
        else:
            return self.__mapping[0]

    def run(self):
        if self.do_task():
            logger.debug("Attempting to start reader task in thread")
            start_frame = self.start_frame()
            end_frame = self.end_frame()
            logger.debug(f"start_frame set to {start_frame}, end_frame set to {end_frame}")

            # O VideoBufferLeft é aberto para end_frame, então o 1o.
            # frame valído para end_frame seria o de índice 1, no caso
            # de setar para um frame_id de 1, o VideoBufferLeft leria até
            # o frame_id=0, mas como o start_frame mínimo é 0,s teriamos
            # start_frame == end_frame, ou seja, nenhum frame seria lido,
            # então nesse caso, e somente nele, devemos íncluir o end_frame
            # nos frames lidos, com isso, teriamos os frames_id=[0, 1], então
            # após a task da thread devemos, remover o frame_id=1, para manter
            # a compatibilidade com o padrão de leitura da classe!
            if isinstance(self.__special_case, int):
                end_frame = self.__special_case

            mapping = self.__mapping.get_mapping()
            values = (self.source, start_frame, end_frame, mapping)

            # O método send deve ser usado somente em 2 casos:
            #   1o. Para enviar os dados para a thread
            #   2o. Para encerrar o thread
            # Peço que usem o send somente para o 2o caso e certifique-se usando
            # _buffer.task_id_done que a task está "parada"! caso contrário o mesmo
            # causara o encerramento do task.
            self._buffer.send(values)

            # Devemos sincronizar a thread principal com o inicio da task
            # para não corrermos o risco de acessar váriaveis que ainda não foram
            # atualizadas.
            self._buffer.synchronizing_main_thread()
            self._set_frame = None

            # Removendo o frame_id ínvalido do caso especial!
            if isinstance(self.__special_case, int):
                logger.debug("Resetting control variable for special case")
                self.__special_case = None
                self._buffer.unqueue()
                _ = self._buffer.get()

    def join(self) -> None:
        """
        Encerra a thread

        Returns:
            None
        """

        # Caso a thread esteja fazendo uma task, devemos encerrá-la
        self._buffer.end_task.set()
        self._buffer.send(False)
        self.thread.join()
        if self.source is not None:
            self.source.release()

    def join_like(self) -> None:
        """
        Encerra a thread sem fechar o VideoCapture

        Returns:
            None
        """
        self._buffer.end_task.set()
        self._buffer.send(False)
        self.thread.join()

    def put(self, frame_id: int, frame: ndarray) -> None:
        """
        Método usado para encher o buffer de maneira manual e de forma segura.

        Args:
            frame_id (int): frame_id do frame a ser colocado no buffer.
            frame (ndarray): frame a ser colocado no buffer.
        """
        logger.trace(f"Putting frame {frame_id} into vbuffer")

        if frame_id not in self.__mapping:
            raise VideoBufferError(f'frame_id "{frame_id}" does not belong to map')
        elif self._buffer.empty() is False:
            if self._buffer[0] > frame_id and len(self._buffer._primary) > 0:
                raise VideoBufferError(f"Inconsistency in operation: 'frame_id' '{frame_id}' is less than the current frame.")
            elif frame_id in self._buffer:
                raise VideoBufferError(f"The frame_id '{frame_id}' is already present in VideoBufferLeft.")

        # O método put tem prioriade sobre o set, portanto devemos
        # setar ambos os atributos relacionados ao set como None.
        self._set_frame = None
        self.__set_end_frame = None

        self.__frame_id = None
        self._buffer.put((frame_id, frame))

    def get(self) -> tuple[int, ndarray | None]:
        """
        Usado para consumir os frames do buffer e gerenciar paralelamento o fluxo
        do buffer.

        Returns:
            tuple[int, ndarray|None]
                - (int): indica o frame_id do frame
                - (ndarray): retorno do frame se a leitura do frame for bem sucedida
                - (None): retorna None caso a leitura tenha sido má sucedida
        """
        logger.trace("Attempting to get frame from VideoBufferLeft")
        self.run()
        self._buffer.unqueue()
        frame_id, frame = self._buffer.get()
        self.__frame_id = frame_id

        logger.trace(f"Frame {frame_id} read successfully from VideoBufferLeft")
        self.run()

        if isinstance(frame_id, int):
            self.__mapping.set_frame_id(frame_id)
        return frame_id, frame

    @property
    def frame_id(self) -> int:
        return self.__frame_id

    def mapper_id(self, index: int) -> int:
        return self.__mapping[index]
