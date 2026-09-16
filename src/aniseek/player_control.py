from loguru import logger
from numpy import ndarray

from aniseek.buffer_left import VideoBufferLeft
from aniseek.buffer_right import VideoBufferRight
from aniseek.interfaces import IVideoBuffer


class PlayerControl:
    def __init__(self, servant: IVideoBuffer = None, master: IVideoBuffer = None):
        self.servant = servant
        self.master = master

        self.__vbright = None
        self.__vbleft = None
        self.__define_buffers(servant, master)

        self.frame_id = None
        self.__quit = False
        self.__paused = False
        self.__frame = None
        self.__read = False
        self.__can_update_frame = True
        self.__can_collect = True
        self.__delay = 35
        self.__default_delay = 35
        self.__current_delay = self.__delay
        self.old = None

    def __define_buffers(self, servant: IVideoBuffer, master: IVideoBuffer):
        if isinstance(servant, VideoBufferRight):
            self.__vbright, self.__vbleft = self.servant, self.master
        else:
            self.__vbright, self.__vbleft = self.master, self.servant

    def __speed(self, delay) -> float | None:
        """
        Método que calcula a velocidade de reprodução do vídeo para
        delay diferente de zero

        Returns:
            float | None: Se o delay for maior que zero, None caso contrário
        """
        if delay > 0:
            return self.__default_delay / delay

    def __adjust_delay(self, delta: int) -> int | None:
        """
        Ajusta o valor do delay.

        Args:
            delta (int): Valor a ser adicionado ao delay.

        Returns:
            int | None: Novo valor do delay, ou None se a alteração não for possível.
        """
        flag_delay = self.__delay != 0
        if flag_delay and self.__delay + delta > 0:
            self.__delay += delta
            return self.__delay
        elif not flag_delay and self.__current_delay + delta > 0:
            self.__current_delay += delta
            return self.__current_delay

    def __can_collect_frame(self) -> bool:
        return (
            self.can_collect() and
            isinstance(self.__frame, ndarray) and
            self.master[0] != self.frame_id
        )

    def update_frame(self, frame_id: int, frame: ndarray) -> None:
        self.frame_id = frame_id
        self.__frame = frame

    def collect_frame(self) -> None:
        """
        Método onde o `master` faz a coleta do trabalho do `servant`.

        Returns:
            None
        """
        if self.__can_collect_frame():
            logger.debug(f'colentando o frame de id {self.frame_id}')
            self.master.put(self.frame_id, self.__frame)
            if self.servant.is_task_complete():
                self.frame_id = None
                self.__frame = None

    def __opencv_format(self, frame: ndarray) -> tuple[bool, ndarray | None]:
        """
        Faz a converção para retornar o mesmo tipo que `cv2.VideoCapture.read`.

        Args:
            frame (ndarray): o frame coletado.
            frame_id (int): indice do frame coletado.

        Returns:
            tuple[bool, ndarray | None]
        """
        if isinstance(frame, ndarray):
            ls = [x[0] for x in self.servant._buffer._primary]
            ms = [x[0] for x in self.master._buffer._primary]
            logger.info(f'servant: {ls[:10]}')
            logger.info(f'master: {ms[:10]}')
            return True, frame
        return False, None

    def read(self) -> tuple[bool, ndarray | None]:
        """
        Lê um frame de vídeo e retorna uma tupla contendo o estado da operação e o frame.

        A função tenta ler um frame de vídeo e retorna um booleano indicando o sucesso ou falha da operação.
        Se a leitura for bem-sucedida, o segundo elemento da tupla será o frame (como um `ndarray`).
        Caso contrário, o segundo elemento será `None`.

        Returns:
            tuple[bool, ndarray | None]:
                - O primeiro valor é um `bool` indicando se a operação foi bem-sucedida (`True`) ou não (`False`).
                - O segundo valor é um `ndarray` representando o frame lido, ou `None` se a operação falhar.
        """

        self.collect_frame()
        if self.servant.is_task_complete() or self.pause() or self.no_read():
            return False, None
        elif self.can_update_frame():
            self.update_frame(*self.servant.get())
        return self.__opencv_format(self.__frame)

    def rewind(self) -> None:
        """
        Controle para retroceder o vídeo.

        Esse metodo faz o swap entre os buffers, se servant for instância de `VideoBufferRight`, com isso
        o buffer que faz a leitura reversa, ou seja, o `master`, passa a funcionar como o `servant`.

        Returns:
            None
        """
        if isinstance(self.servant, VideoBufferRight):
            logger.debug('setando o modo rewind')
            self.servant, self.master = self.master, self.servant

    def proceed(self) -> None:
        """
        Controle para retroceder o vídeo.

        Esse metodo faz o swap entre os buffers se `servant` for instância de `VideoBufferRight`, com isso
        o buffer que faz a leitura correta, ou seja, o `master`, passa a funcionar como o `servant`.

        Returns:
            None
        """
        if isinstance(self.servant, VideoBufferLeft):
            logger.debug('setando o modo proceed')
            self.servant, self.master = self.master, self.servant

    def set_pause(self):
        logger.debug(f'setting the pause to {not self.__paused}')
        self.__paused = not self.__paused

    def pause(self) -> bool:
        return self.__paused

    def set_quit(self):
        logger.debug('preparando para sair...')
        self.__quit = True

    def quit(self) -> bool:
        return self.__quit

    def set_read(self) -> None:
        self.__read = False

    def disable_collect(self) -> None:
        self.__can_collect = False

    def disable_update_frame(self) -> None:
        self.__can_update_frame = False

    def no_read(self):
        read_flag = self.__read
        if not self.__read:
            self.__read = True
        return read_flag and self.__delay == 0

    def can_collect(self) -> bool:
        result = self.__can_collect
        self.__can_collect = True
        return result

    def can_update_frame(self) -> bool:
        update_flag = self.__can_update_frame
        self.__can_update_frame = True
        return update_flag

    def increase_speed(self) -> None:
        delay = self.__adjust_delay(-1)
        if delay is not None:
            logger.info(f'speed {self.__speed(delay):.2f}x {delay}')

    def decrease_speed(self) -> None:
        delay = self.__adjust_delay(+1)
        if delay is not None:
            logger.info(f'speed {self.__speed(delay):.2f}x {delay}')

    def pause_delay(self) -> None:
        if self.__delay == 0:
            logger.debug('unpause by delay')
            self.__delay = self.__current_delay
            self.__read = False
        else:
            logger.debug('pause by delay')
            self.__current_delay = self.__delay
            self.__delay = 0
            self.__read = True

    def restore_delay(self) -> None:
        delay = self.__default_delay
        logger.info(f'speed {self.__speed(delay):.2f}x {delay}')
        if self.__delay > 0:
            self.__delay = self.__default_delay
        else:
            self.__current_delay = self.__default_delay

    @property
    def delay(self) -> int:
        return self.__delay

    @property
    def current_delay(self) -> int:
        return self.__current_delay

    def remove_frame(self) -> tuple[int | None, ndarray | None]:
        logger.debug(f'servo {self.servant}')
        if isinstance(self.__frame, ndarray) and not self.pause():
            frame_id, frame = self.frame_id, self.__frame
            if not self.master._buffer.empty() and self.master[0] == self.frame_id:
                self.master._buffer.get()
            self.__frame = None
            self.frame_id = None
            return frame_id, frame
        elif not self.servant.is_task_complete():
            ret, frame = self.read()
            if ret is True:
                return self.remove_frame()
        return None, None

    def __speed_read(self, servant: IVideoBuffer, master: IVideoBuffer):
        if not servant.is_task_complete():
            self.update_frame(*servant.get())
            master.put(self.frame_id, self.__frame)
            return True
        return False

    def set_frame(self, frame_id: int) -> None:
        logger.debug(f'setting the frame for the frame_id {frame_id}')
        self.servant.set(frame_id)

    def _backward(self, frame_id: int) -> bool:
        """
        Método para voltar até o frame de índice de 'frame_id', esse método espera
        que o frame_id pertença ao intervalor do `VideoBufferLeft`, isto é, que seja
        maior que 'start_frame' e menor que 'buffer[0]' onde buffer é uma instância de
        `VideoBufferLeft`
        """
        servant, master = self.__vbleft, self.__vbright
        fid = servant[0]
        if fid is None:
            return False
        elif fid < frame_id:
            return True

        while self.__speed_read(servant, master):
            if servant[0] is not None and servant[0] < frame_id:
                break
        return True

    def _forward(self, frame_id: int) -> bool:
        """
        Método para avançar até o frame de índice com o valor de 'frame_id', esse método
        espera que  frame_id pertença ao intervalo do `VideoBufferRight`, isto é, que seja
        maior que 'buffer[0]', onde buffer é uma instância de `VideoBufferRight`e menor que
        'end_frame'
        """
        servant, master = self.__vbright, self.__vbleft
        fid = servant[0]
        if fid is None:
            return False
        elif fid > frame_id:
            return True
        while self.__speed_read(servant, master):
            if servant[0] is not None and servant[0] > frame_id:
                break
        return True

    def _is_valid_backward(self, frame_id: int) -> bool:
        buffer = self.__vbleft
        end_frame = buffer[0]
        if end_frame is None:
            return False

        first_frame = buffer.mapper_id(0)
        start_frame = buffer.start_frame()
        if first_frame == start_frame and end_frame > frame_id:
            return True
        return start_frame < frame_id and end_frame > frame_id

    def __set_frame(self, frame_id) -> None:
        if isinstance(self.servant, VideoBufferRight):
            if self.servant.mapper_id(0) == frame_id:
                self.servant.set(frame_id)
                self.master.set(frame_id)
            elif self.servant.mapper_id(-1) == frame_id:
                self.servant.set(frame_id)
                self.master.set(frame_id)
            else:
                self.servant.set(frame_id + 1)
                self.master.set(frame_id)
        else:
            self.servant.set(frame_id)
            self.master.set(frame_id)

    def restore_frame(self, frame_id: int, frame: ndarray) -> None:
        logger.debug(f'starting frame restoration {frame_id}')
        self.__set_frame(frame_id)
        self.update_frame(frame_id, frame)

    def set_buffers(self, servant: VideoBufferRight, master: VideoBufferLeft):
        self.servant = servant
        self.master = master
        self.frame_id = None
        self.__frame = None

    def swap(self):
        self.master, self.servant = self.servant, self.master

    def undo_config(self):
        self.disable_collect()
        self.disable_update_frame()
        self.set_read()

    def join(self):
        self.servant.join()
        self.master.join()

    def get_buffer_left(self) -> VideoBufferLeft:
        """Retorna o VideoBufferLeft."""
        if isinstance(self.master, VideoBufferLeft):
            return self.master
        return self.servant

    def get_buffer_right(self) -> VideoBufferRight:
        """Retorna o VideoBufferRight."""
        if isinstance(self.master, VideoBufferRight):
            return self.master
        return self.servant
