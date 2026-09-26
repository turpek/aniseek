from __future__ import annotations

from loguru import logger
from numpy import ndarray

from aniseek.core.buffer_left import VideoBufferLeft
from aniseek.core.buffer_right import VideoBufferRight
from aniseek.core.interfaces.buffer import IVideoBuffer


class PlayerControl:
    def __init__(self, servant: IVideoBuffer | None = None, master: IVideoBuffer | None = None) -> None:
        self.servant: IVideoBuffer = servant  # type: ignore[assignment]
        self.master: IVideoBuffer = master  # type: ignore[assignment]

        self.__vbright: IVideoBuffer = None  # type: ignore[assignment]
        self.__vbleft: IVideoBuffer = None  # type: ignore[assignment]
        self.__define_buffers(servant, master)  # type: ignore[arg-type]

        self.frame_id: int | None = None
        self.__quit = False
        self.__paused = False
        self.__frame: ndarray | None = None
        self.__read = False
        self.__can_update_frame = True
        self.__can_collect = True
        self.__delay = 35
        self.__default_delay = 35
        self.__current_delay = self.__delay
        self.old = None

    def __define_buffers(self, servant: IVideoBuffer, master: IVideoBuffer) -> None:
        if isinstance(servant, VideoBufferRight):
            self.__vbright, self.__vbleft = self.servant, self.master
        else:
            self.__vbright, self.__vbleft = self.master, self.servant

    def __speed(self, delay: int) -> float | None:
        """
        Método que calcula a velocidade de reprodução do vídeo para
        delay diferente de zero

        Returns:
            float | None: Se o delay for maior que zero, None caso contrário
        """
        if delay > 0:
            return self.__default_delay / delay
        return None

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
        return None

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
            logger.trace(f'Collecting frame {self.frame_id}')
            self.master.put(self.frame_id, self.__frame)  # type: ignore[arg-type]
            if self.servant.is_task_complete():
                self.frame_id = None
                self.__frame = None

    def __opencv_format(self, frame: ndarray | None) -> tuple[bool, ndarray | None]:
        """
        Faz a converção para retornar o mesmo tipo que `cv2.VideoCapture.read`.

        Args:
            frame (ndarray): o frame coletado.
            frame_id (int): indice do frame coletado.

        Returns:
            tuple[bool, ndarray | None]
        """
        if isinstance(frame, ndarray):
            logger.opt(lazy=True).trace(
                'servant: {s} | master: {m}',
                s=lambda: [x[0] for x in self.servant._buffer._primary][:10],
                m=lambda: [x[0] for x in self.master._buffer._primary][:10],
            )
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

        if self.pause() or self.no_read():
            return False, None
        self.collect_frame()
        if self.servant.is_task_complete():
            return False, None
        elif self.can_update_frame():
            self.update_frame(*self.servant.get())  # type: ignore[arg-type]
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
            logger.debug('Setting rewind mode')
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
            logger.debug('Setting proceed mode')
            self.servant, self.master = self.master, self.servant

    @property
    def is_rewind(self) -> bool:
        return isinstance(self.servant, VideoBufferLeft)

    def set_pause(self):
        logger.debug(f'Setting pause state to {not self.__paused}')
        self.__paused = not self.__paused

    def pause(self) -> bool:
        return self.__paused

    def set_quit(self):
        logger.debug('Preparing player shutdown...')
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
            logger.info(f'Playback speed set to {self.__speed(delay):.2f}x (delay={delay})')

    def decrease_speed(self) -> None:
        delay = self.__adjust_delay(+1)
        if delay is not None:
            logger.info(f'Playback speed set to {self.__speed(delay):.2f}x (delay={delay})')

    def pause_delay(self) -> None:
        if self.__delay == 0:
            logger.debug('Unpausing playback due to delay')
            self.__delay = self.__current_delay
            self.__read = False
        else:
            logger.debug('Pausing playback due to delay')
            self.__current_delay = self.__delay
            self.__delay = 0
            self.__read = True

    def restore_delay(self) -> None:
        delay = self.__default_delay
        logger.info(f'Playback speed set to {self.__speed(delay):.2f}x (delay={delay})')
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

    def set_delay(self, value: int) -> None:
        """Define o delay diretamente."""
        self.__delay = max(0, value)
        if self.__delay > 0:
            self.__read = False
        else:
            self.__read = True

    def remove_frame(self) -> tuple[int | None, ndarray | None]:
        logger.debug(f'Servant buffer: {self.servant}')
        if isinstance(self.__frame, ndarray) and not self.pause():
            frame_id, frame = self.frame_id, self.__frame
            if not self.master._buffer.empty() and self.master[0] == self.frame_id:
                self.master._buffer.get()
            self.__frame = None
            self.frame_id = None
            return frame_id, frame
        elif not self.servant.is_task_complete():
            ret, frame = self.read()  # type: ignore[assignment]
            if ret is True:
                return self.remove_frame()
        return None, None

    def __speed_read(self, servant: IVideoBuffer, master: IVideoBuffer) -> bool:
        if not servant.is_task_complete():
            self.update_frame(*servant.get())  # type: ignore[arg-type]
            master.put(self.frame_id, self.__frame)  # type: ignore[arg-type]
            return True
        return False

    def set_frame(self, frame_id: int) -> None:
        logger.debug(f'Setting player target frame to {frame_id}')
        self.servant.set(frame_id)

    def _backward(self, frame_id: int) -> bool:
        """
        Método para voltar até o frame de índice de 'frame_id', esse método espera
        que o frame_id pertença ao intervalor do `VideoBufferLeft`, isto é, que seja
        maior que 'start_frame' e menor que 'buffer[0]' onde buffer é uma instância de
        `VideoBufferLeft`
        """
        servant, master = self.__vbleft, self.__vbright
        fid = servant[0]  # type: ignore[index]
        if fid is None:
            return False
        elif fid < frame_id:
            return True

        while self.__speed_read(servant, master):
            if servant[0] is not None and servant[0] < frame_id:  # type: ignore[index]
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
        fid = servant[0]  # type: ignore[index]
        if fid is None:
            return False
        elif fid > frame_id:
            return True
        while self.__speed_read(servant, master):
            if servant[0] is not None and servant[0] > frame_id:  # type: ignore[index]
                break
        return True

    def _is_valid_backward(self, frame_id: int) -> bool:
        buffer = self.__vbleft
        end_frame = buffer[0]  # type: ignore[index]
        if end_frame is None:
            return False

        first_frame = buffer.mapper_id(0)  # type: ignore[union-attr]
        start_frame = buffer.start_frame()  # type: ignore[union-attr]
        if first_frame == start_frame and end_frame > frame_id:
            return True
        return start_frame < frame_id and end_frame > frame_id  # type: ignore[operator]

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
        logger.debug(f'Starting frame restoration for {frame_id}')
        self.__set_frame(frame_id)
        self.update_frame(frame_id, frame)

    def set_buffers(self, servant: IVideoBuffer, master: IVideoBuffer):
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
        return self.servant  # type: ignore[return-value]

    def get_buffer_right(self) -> VideoBufferRight:
        """Retorna o VideoBufferRight."""
        if isinstance(self.master, VideoBufferRight):
            return self.master
        return self.servant  # type: ignore[return-value]
