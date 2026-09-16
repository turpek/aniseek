from pytest import fixture
from aniseek.buffer import FakeBuffer as Buffer
from threading import Semaphore, Thread
from time import sleep
import numpy as np


@fixture
def buffer():
    semaphore = Semaphore()
    bf = Buffer(semaphore, maxsize=25)
    yield bf


def lote(start, end, step=1):
    return [(frame_id, np.ones((2, 2))) for frame_id in range(start, end, step)]


def test_buffer_secondary_vazio(buffer):
    expect = True
    result = buffer.secondary_empty()
    assert expect == result


def test_buffer_secondary_nao_esta_vazio(buffer):
    expect = False
    [buffer.sput(frame) for frame in lote(0, 1, 1)]
    result = buffer.secondary_empty()
    assert expect == result


def test_colocando_1_frame_no_buffer_secondary(buffer):
    expect = 1
    [buffer.sput(frame) for frame in lote(0, 1, 1)]
    result = buffer._secondary.qsize()
    assert expect == result


def test_enchendo_o_buffer_secondary(buffer):
    expect = True
    [buffer.sput(frame) for frame in lote(0, 25, 1)]
    result = buffer._secondary.full()
    assert expect == result


def test_setando_o_buffer(buffer):
    expect = False
    buffer.set()
    result = buffer.task_is_done()
    assert expect == result


def test_clear_do_buffer(buffer):
    expect = True
    buffer.set()
    buffer.clear()
    result = buffer.task_is_done()
    assert expect == result

def test_buffer_esta_vazio(buffer):
    expect = True
    result = buffer.empty()
    assert expect == result

def test_buffer_colocando_1_frame_no_buffer_manualmente(buffer):
    expect = False
    [buffer.put(frame) for frame in lote(0, 1, 1)]
    result = buffer.empty()
    assert expect == result


def test_buffer_nao_esta_cheio(buffer):
    expect = False
    [buffer.put(frame) for frame in lote(0, 1, 1)]
    result = buffer.full()
    assert expect == result


def test_buffer_esta_cheio(buffer):
    expect = True
    [buffer.put(frame) for frame in lote(0, 25, 1)]
    result = buffer.full()
    assert expect == result


def test_buffer_checando_o_ultimo_elemento(buffer):
    expect_frame_id = 25
    [buffer.put(frame) for frame in lote(25, 0, -1)]
    result_frame_id, _ = buffer._primary[-1]
    assert expect_frame_id == result_frame_id


def test_buffer_esta_cheio_e_colocando_mais_1_elemento(buffer):
    expect_frame_id = 24
    [buffer.put(frame) for frame in lote(25, 0, -1)]
    [buffer.put(frame) for frame in lote(0, -1, -1)]
    result_frame_id, _ = buffer._primary[-1]
    assert expect_frame_id == result_frame_id


def test_buffer_lendo_1_valor_do_buffer(buffer):
    expect_frame_id = 0
    [buffer.put(frame) for frame in lote(0, 1, 1)]
    result_frame_id, _ = buffer.get()
    assert expect_frame_id == result_frame_id


def test_buffer_lendo_todos_os_valores_do_buffer(buffer):
    expect = list(range(25))
    [buffer.put(frame) for frame in lote(24, -1, -1)]
    result = [buffer.get()[0] for frame in range(25)]
    assert expect == result


def test_buffer_nao_esta_bloqueado_para_task(buffer):
    expect = True
    result = buffer.no_block_task()
    assert expect == result


def test_buffer_bloquando_a_task_ao_colocar_valor_no_buffer_manualmente(buffer):
    expect = False
    [buffer.put(frame) for frame in lote(0, 1, 1)]
    result = buffer.no_block_task()
    assert expect == result


def test_buffer_bloquando_a_task_manualmente(buffer):
    expect = False
    result = buffer.no_block_task(False)
    assert expect == result


def test_buffer_desbloquando_a_task_manualmente(buffer):
    expect = True
    [buffer.put(frame) for frame in lote(0, 1, 1)]
    result = buffer.no_block_task(True)
    assert expect == result


def test_buffer_desbloquando_a_task_ao_ler_o_buffer(buffer):
    expect = True
    [buffer.put(frame) for frame in lote(0, 1, 1)]
    buffer.get()
    result = buffer.no_block_task()
    assert expect == result


def test_buffer_do_task_retorna_true(buffer):
    expect = True
    result = buffer.do_task()
    assert expect == result


def test_buffer_do_task_retorna_false_secondary_nao_esta_vazio(buffer):
    expect = False
    expect_secondary = False
    expect_no_block_task = True
    expect_task_is_done = True
    [buffer.sput(frame) for frame in lote(0, 1, 1)]

    result = buffer.do_task()
    result_secondary = buffer.secondary_empty()
    result_no_block_task = buffer.no_block_task()
    result_task_is_done = buffer.task_is_done()

    assert expect == result
    assert expect_secondary == result_secondary
    assert expect_no_block_task == result_no_block_task
    assert expect_task_is_done == result_task_is_done


def test_buffer_do_task_retorna_false_no_block_task_eh_false(buffer):
    expect = False
    expect_secondary = True
    expect_no_block_task = False
    expect_task_is_done = True
    [buffer.put(frame) for frame in lote(0, 1, 1)]

    result = buffer.do_task()
    result_secondary = buffer.secondary_empty()
    result_no_block_task = buffer.no_block_task()
    result_task_is_done = buffer.task_is_done()

    assert expect == result
    assert expect_secondary == result_secondary
    assert expect_no_block_task == result_no_block_task
    assert expect_task_is_done == result_task_is_done


def test_buffer_do_task_retorna_false_task_is_done_eh_false(buffer):
    expect = False
    expect_secondary = True
    expect_no_block_task = True
    expect_task_is_done = False

    buffer.set()
    result = buffer.do_task()
    result_secondary = buffer.secondary_empty()
    result_no_block_task = buffer.no_block_task()
    result_task_is_done = buffer.task_is_done()

    assert expect == result
    assert expect_secondary == result_secondary
    assert expect_no_block_task == result_no_block_task
    assert expect_task_is_done == result_task_is_done


def test_buffer_do_task_secondary_eh_task_is_done_sao_false(buffer):
    expect = False
    expect_secondary = False
    expect_no_block_task = True
    expect_task_is_done = False

    buffer.set()
    [buffer.sput(frame) for frame in lote(0, 1, 1)]
    result = buffer.do_task()
    result_secondary = buffer.secondary_empty()
    result_no_block_task = buffer.no_block_task()
    result_task_is_done = buffer.task_is_done()

    assert expect == result
    assert expect_secondary == result_secondary
    assert expect_no_block_task == result_no_block_task
    assert expect_task_is_done == result_task_is_done


def test_buffer_do_task_no_block_task_eh_task_is_done_sao_false(buffer):
    expect = False
    expect_secondary = True
    expect_no_block_task = False
    expect_task_is_done = False

    buffer.set()
    buffer._wait_task.put(True)  # Para não bloquear os testes
    [buffer.put(frame) for frame in lote(0, 1, 1)]
    result = buffer.do_task()
    result_secondary = buffer.secondary_empty()
    result_no_block_task = buffer.no_block_task()
    result_task_is_done = buffer.task_is_done()

    assert expect == result
    assert expect_secondary == result_secondary
    assert expect_no_block_task == result_no_block_task
    assert expect_task_is_done == result_task_is_done


def test_buffer_do_task_secondary_eh_no_block_task_eh_sao_false(buffer):
    expect = False
    expect_secondary = False
    expect_no_block_task = False
    expect_task_is_done = True

    [buffer.put(frame) for frame in lote(0, 1, 1)]
    [buffer.sput(frame) for frame in lote(0, 1, 1)]
    result = buffer.do_task()
    result_secondary = buffer.secondary_empty()
    result_no_block_task = buffer.no_block_task()
    result_task_is_done = buffer.task_is_done()

    assert expect == result
    assert expect_secondary == result_secondary
    assert expect_no_block_task == result_no_block_task
    assert expect_task_is_done == result_task_is_done


def test_buffer_do_task_todos_sao_false(buffer):
    expect = False
    expect_secondary = False
    expect_no_block_task = False
    expect_task_is_done = False

    [buffer.put(frame) for frame in lote(0, 1, 1)]
    [buffer.sput(frame) for frame in lote(0, 1, 1)]
    buffer.set()
    result = buffer.do_task()
    result_secondary = buffer.secondary_empty()
    result_no_block_task = buffer.no_block_task()
    result_task_is_done = buffer.task_is_done()

    assert expect == result
    assert expect_secondary == result_secondary
    assert expect_no_block_task == result_no_block_task
    assert expect_task_is_done == result_task_is_done


def test_buffer_clear_queue_com_ela_vazia(buffer):
    expect = True

    buffer.clear_queue()
    result = buffer.secondary_empty()
    assert expect == result


def test_buffer_clear_queue_com_ela_cheia(buffer):
    expect = True

    [buffer.sput(frame) for frame in lote(0, 25, 1)]
    buffer.clear_queue()
    result = buffer.secondary_empty()
    assert expect == result


def test_buffer_clear_buffer_com_ele_vazio(buffer):
    expect_primary = True
    expect_secondary = True

    buffer.clear_buffer()
    result_primary = buffer.empty()
    result_secondary = buffer.secondary_empty()

    assert expect_primary == result_primary
    assert expect_secondary == result_secondary


def test_buffer_clear_buffer_com_ele_cheio(buffer):
    expect_primary = True
    expect_secondary = True

    [buffer.sput(frame) for frame in lote(0, 25, 1)]
    buffer.unqueue()
    [buffer.sput(frame) for frame in lote(25, 50, 1)]
    buffer.clear_buffer()
    result_primary = buffer.empty()
    result_secondary = buffer.secondary_empty()

    assert expect_primary == result_primary
    assert expect_secondary == result_secondary


def test_buffer_synchronizing_main_thread(buffer):
    expect = False

    def task(buffer):
        # Função que simula uma task
        buffer.set()
        sleep(0.001)
        buffer.clear()
    th = Thread(target=task, args=(buffer,))
    th.start()
    buffer.synchronizing_main_thread()
    result = buffer.task_is_done()
    th.join()
    assert expect == result
