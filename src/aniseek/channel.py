from queue import Queue
from threading import Lock


class _Channel:
    def __init__(self, send, recv, send_err, recv_err):
        self._send = send
        self._recv = recv
        self._handle = True
        self._error = False
        self.closed = False
        self.send_err = send_err
        self.recv_err = recv_err
        self.lock = Lock()

    def _check_error(self):
        if not self.recv_err.empty():
            self._error = True
        if self._error is True:
            raise BrokenPipeError('Broken pipe')

    def _check_closed(self):
        if self._handle is None:
            raise OSError("handle is closed")

    def send(self, msg):
        self._check_closed()
        self._check_error()
        with self.lock:
            self._send.put_nowait(msg)

    def recv(self):
        self._check_closed()
        self._check_error()
        with self.lock:
            return self._recv.get()

    def poll(self):
        self._check_closed()
        with self.lock:
            return not self._recv.empty()

    def close(self):
        self._handle = None
        self.closed = True
        with self.lock:
            self.send_err.put(True)


class Channel:
    def __new__(self):
        inpt = Queue()
        outp = Queue()
        send_err = Queue()
        recv_err = Queue()

        self.pipe1 = _Channel(inpt, outp, send_err, recv_err)
        self.pipe2 = _Channel(outp, inpt, recv_err, send_err)
        return self.pipe1, self.pipe2


class Channel1:
    """
    Classe para comunicação em uma direção entre o programa e a threads
    """

    def __init__(self):
        self.__conn = Queue()

    def send(self, data: any) -> None:
        """
        Método para enviar dados para a thread, como a queue onde é armazenado os dados tem tamanho 1,
        verifique com o método poll sé a dados ainda a serem lidos, antes de colocar mais dados e assim
        não travar o fluxo do programa


        Args:
            data any: os dados a serem enviados.

        Returns:
            None
        """
        self.__conn.put(data)

    def recv(self) -> any:
        """
        Método para receber os dados envidos pelo método send

        Returns:
            any
        """
        return self.__conn.get()

    def poll(self) -> bool:
        """
        Verifica se a dados a serem lidos

        Returns:
            bool
        """
        return self.__conn.qsize() >= 1
