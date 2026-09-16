import traceback
from time import time

import cv2

from aniseek.buffer import Buffer


def reader_task(buffer: Buffer, data: tuple) -> None:
    """Função responsável por ler os frames através do modulo da Opencv.

        Args:
            cap (VideoCapture): objeto usado para gerar os frames.
            buffer (Buffer): objeto onde os frames serão armazenados.
            data (tuple[int, int, set]): deve passar como parametro (start_frame, last_frame, mapping_frames)

        Returns:
            None

    """

    # O fluxo principal do programa deve passar o frame_id "start_frame" que
    # define o  frame incial, ja mapping_frames é um set contendo todos os frames a serem lidos.
    buffer.set()
    cap, start_frame, last_frame, mapping_frames = data
    frame_id, qsize = start_frame, 0
    start = time()

    # Verificando se cap já esta no frame inicial e se o frame_start
    # é menor que o último frame do vídeo
    check_frame_id = int(cap.get(cv2.CAP_PROP_POS_FRAMES))
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    if start_frame >= frame_count:
        raise IndexError('start_frame ultrapassou o limite de frames do vídeo.')
    elif check_frame_id != frame_id:
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_id)

    # Bloco onde os frames são lidos e armazenados na fila
    ret = None
    while True:

        if frame_id in mapping_frames:
            ret, frame = cap.read()
            buffer.sput((frame_id, frame))
            qsize += 1
        else:
            cap.grab()

        if buffer.log:
            print(qsize, qsize, frame_id, ret)
        if frame_id == last_frame:
            break
        elif qsize == buffer.maxsize:
            break
        elif frame_id == frame_count:
            # raise IndexError('o video acabou')
            break
        elif buffer.end_task.is_set():
            break
        frame_id += 1

    buffer.clear()
    if buffer.log:
        end = time()
        count = frame_id - start_frame
        print(f'\nLidos {count} em {end - start}s')
        print(f'{count / (end - start):.2f} FPS')


def reader(buffer: Buffer) -> None:
    """Um invólucro que chama a função responsável por ler os frames através do modulo da Opencv.

        Args:
            cap (str): instancia de VideoCapture.
            buffer (Buffer): objeto onde os frames serão armazenados.
    """

    try:
        # if not cap.isOpened():
        #    raise VideoOpenError('Não foi possível abrir o arquivo.')

        # Bloco "príncipal" da função, que é responsavel por ativar a leitura dos
        # frames por meio da função reader_task.
        while True:

            data = buffer.recv()
            if hasattr(data, '__contains__'):
                reader_task(buffer, data)
            else:
                break

    except Exception as e:
        exc_info = traceback.format_exc()
        buffer._error.put(e, exc_info)
    finally:
        buffer.set()
        # if cap is not None:
        #    cap.release()
        buffer.clear()
