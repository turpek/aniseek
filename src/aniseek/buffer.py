"""Este módulo tem uma classe que implementa um buffer, onde terá dois
buffers internos que farão a gestão do objeto, de maneira ao Buffer
estár sempre cheio, para isso temos os seguintes atributos e métodos.

class Buffer:
    -_primary: É um deque que define o buffer primario.
    -_secondary: É uma Queue que define o buffer segundario.

    +no_block_task() bool: Método para bloquear a task
    +clear() bool: Método para se chamado dentro da task para liberar os recursos de controle do Buffer.
    +empty() bool: Retorna True se o buffer primario estiver vazio.
    +full() bool: Retorna True se o buffer primario estiver cheio.
    +get() any: Retorna o valor armazenado no Buffer
    +put() None: Coloca um dado no buffer primario manualmente.
    +secondary_empty() bool: Retorna True se o buffer segundario estiver vazio.
    +set() bool: Método para ser chamado dentro da task, seta recurso para o controle do Buffer.
    +sput() bool: Método para armazenar o dado no buffer segundaroi.
    +task_is_done() bool: Verifica se a tarefa esta concluida.
    +unqueue None: Método que deve ser implementado ao herdar de Buffer.


class FakeBuffer(Buffer):
    classe que implementa unqueue para tornar possível a testagem do Buffer.
    +unqueue None: Método placebo.


class BufferRight(Buffer):
    +unqueue() None: Método que faz a transferencia dos valores armazenados no buffer segundario
        para o buffer primario


class BufferLeft(Buffer):
    +unqueue() None: Método que faz a transferencia dos valores armazenados no buffer segundario
        para o buffer primario
"""


from abc import ABC, abstractmethod
from collections import deque
from queue import Queue
from threading import Event, Lock, Semaphore

from loguru import logger

from aniseek.channel import Channel1
from aniseek.custom_exceptions import VideoBufferError


class Buffer(ABC, Channel1):
    def __init__(self, semaphore: Semaphore, *, maxsize: int = 15, log: bool = False):
        # Criando um deque e uma Queue onde os frames serão armazenados
        super().__init__()
        self.maxsize = maxsize
        self.log = log
        self._primary = deque(list(), maxlen=maxsize)
        self._secondary = Queue(maxsize=maxsize)
        self.__block_task = True
        self.lock = Lock()
        self.semaphore = semaphore
        self.event = Event()
        self.end_task = Event()

        # Queue para o envio de possíveis erros que venham a ocorrer na thread
        self._error = Queue()

        self.__task = Queue(maxsize=1)
        self._wait_task = Queue(maxsize=1)
        self._end_task = Queue(maxsize=1)
        self.__task.put_nowait(True)
        self._wait_task.put_nowait(True)

    def __getitem__(self, index: int) -> int:
        return self._primary[index][0]

    def __len__(self):
        return len(self._primary)

    def _wait_until_fill(self) -> None:
        # Espera a task ser concluida no caso em que o buffer estiver vazio!
        if self.empty():
            self.wait_task()

    def clear_buffer(self) -> None:
        """
        Método usado para limpar o Buffer de maneira segura.

        Returns:
            None
        """
        logger.debug('unloading the primary and secondary buffers')
        self.clear_queue()
        self._primary.clear()

    def clear_queue(self) -> None:
        """
        Removendo todos os elementos da Queue secondary.

        Returns:
            None
        """

        logger.debug('starting process to clear secondary buffer')
        # Matamos a task antes de limpar a queue, para isso enviamos False
        if not self.task_is_done():
            logger.debug('terminating the task in the thread')
            self.end_task.set()

        # Devemos descarregar o buffer secondary no primary antes de limpa-lo
        self.unqueue()
        logger.debug('unloading the secondary buffer')
        while self.secondary_empty() is False:
            self._secondary.get_nowait()

    def wait_task(self):
        """
        Espera até que a tarefa esteja concluida

        Returns:
            None
        """
        if self.task_is_done() is False:
            value = self._wait_task.get()
            self._wait_task.put(value)

    def do_task(self):
        """
        Método usado para determinar se o Buffer está pronto para iniciar uma task

        Returns:
            bool
        """
        return self.secondary_empty() and self.no_block_task() and self.task_is_done() and self.poll() is False

    def no_block_task(self, value: bool = None) -> bool:
        """
        Usado para verificar se a task deve ser feita (se nenhum argumento for passado), passe bool como
        argumento para bloquear ou liberar a task.

        Args:
            value (bool): Se value for False então a task será bloqueada, caso contrário será liberada.

        Returns:
            bool
        """
        if isinstance(value, bool):
            self.__block_task = value
        return self.__block_task

    def sput(self, value: any) -> None:
        """
        Método interno para preencher o buffer segundario.

        Args:
            value (any): dado a ser inserido no buffer

        Returns:
            None
        """
        self._secondary.put(value)

    def set(self) -> None:
        """
        Método para setar atributos que tem relação com inicio da task

        Returns:
            None
        """
        logger.debug('setting synchronization and task control variables with threads')
        self.semaphore.acquire()
        self.task_is_done(False)
        self._wait_task.get()
        self.event.set()
        self.end_task.clear()

    def clear(self) -> None:
        """
        Método para setar atributos que tem relação com o fim da task

        Returns:
            None
        """
        logger.debug('unsetting synchronization and task control variables with threads')
        self.semaphore.release()
        self.task_is_done(True)
        self._wait_task.put(True)
        self.event.clear()
        self.end_task.set()

    def synchronizing_main_thread(self) -> None:
        """
        Sincroniza a thread principal com a thread responsável pela task.

        Quando uma task é iniciada via `send`, há um pequeno intervalo de tempo até que as
        variáveis de controle do buffer sejam atualizadas. Nesse intervalo, a thread principal
        pode tentar acessar essas variáveis antes de serem devidamente configuradas, o que pode
        resultar em um comportamento inesperado no programa.

        O método `synchronizing_main_thread` usa um evento (`Event`) para forçar a thread principal
        a aguardar até que a atualização das variáveis de controle esteja concluída, garantindo
        a consistência do estado do buffer.

        Returns:
            None
        """
        logger.debug('synchronizing main thread')
        self.event.wait()

    def task_is_done(self, value: bool = None) -> bool:
        """
        Verifica se o ciclo para encher o buffer secundary foi concluido.

        Returns:
            bool
        """
        with self.lock:
            task_is_done = self.__task.get_nowait()
            if isinstance(value, bool):
                logger.debug(f'setting task_is_done to {value}')
                self.__task.put_nowait(value)
            else:
                self.__task.put_nowait(task_is_done)
        return task_is_done

    def secondary_empty(self) -> bool:
        """
        Verifica se o buffer segundario está vazio.

        Returns:
            bool
        """
        return self._secondary.empty()

    def empty(self) -> bool:
        """
        Verifica se o buffer está vazio.

        Returns:
            boll
        """
        return len(self._primary) == 0

    def full(self) -> bool:
        """
        Verifica se o buffer está cheio.

        Returns:
            boll
        """
        return len(self._primary) == self._primary.maxlen

    @abstractmethod
    def unqueue(self) -> None:
        ...

    def put(self, value: any) -> None:
        """
        Coloca um valor no Buffer, sem risco de ficar bloqueada até que a task esteja concluida.

        Args:
            value (any): valor a ser armazenado no Buffer.

        Returns:
            None
        """

        self.clear_queue()
        # Atributo para bloqueia da task enquanto o usuario colocar valores
        # manualmente, o bloqueio será desfeito somente quando um valor for lido
        # do Buffer
        self.no_block_task(False)
        self._primary.appendleft(value)

    def get(self) -> any:
        """
            Retira um valor do Buffer.

            Returns:
                any: valor a ser retirado do Buffer.
        """

        # Desbloquando a task
        self.no_block_task(True)
        try:
            return self._primary.popleft()
        except IndexError:
            raise VideoBufferError('get from an empty buffer')


class BufferRight(Buffer):
    def __init__(self, semaphore: Semaphore, *, maxsize: int = 25, log: bool = False):
        super().__init__(semaphore, maxsize=maxsize, log=log)

    def unqueue(self) -> None:
        """
        Método para passar os frames do buffer segundario para o primario.

        Returns:
            None
        """
        self._wait_until_fill()
        if self.task_is_done() and self.empty():
            logger.debug('unloading the primary buffer')
            while not self.secondary_empty():
                value = self._secondary.get()
                self._primary.append(value)


class BufferLeft(Buffer):
    def __init__(self, semaphore: Semaphore, *, maxsize: int = 25, log: bool = False):
        super().__init__(semaphore, maxsize=maxsize, log=log)

    def unqueue(self) -> None:
        """
        Método para passar os frames do buffer segundario para o primario.

        Returns:
            None
        """
        self._wait_until_fill()
        if self.task_is_done() and self.empty():
            logger.debug('unloading the primary buffer')
            while not self.secondary_empty():
                value = self._secondary.get()
                self._primary.appendleft(value)


class FakeBuffer(BufferRight):
    def __init__(self, semaphore: Semaphore, *, maxsize: int = 25, log: bool = False):
        super().__init__(semaphore, maxsize=maxsize, log=log)
