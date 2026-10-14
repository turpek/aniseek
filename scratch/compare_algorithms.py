from __future__ import annotations

import bisect
import time
from typing import NamedTuple


class InstrumentedVideoSource:
    """Dublê instrumentalizado de IFrameSource para medição exata de seeks e grabs."""

    def __init__(
        self,
        frame_count: int,
        keyframes: list[int] | None = None,
        corrupt_ranges: list[tuple[int, int]] | None = None,
        actual_eof: int | None = None,
    ):
        self.nominal_frame_count = frame_count
        self.actual_eof = actual_eof if actual_eof is not None else frame_count
        self.keyframes = sorted(keyframes) if keyframes is not None else []
        self.corrupt_ranges = corrupt_ranges or []

        self.current_pos = 0
        self.seek_count = 0
        self.grab_count = 0
        self.seek_history: list[int] = []

    def set_pos(self, frame_id: int) -> None:
        self.seek_count += 1
        self.seek_history.append(frame_id)
        self.current_pos = frame_id

    def grab(self) -> bool:
        self.grab_count += 1
        pos = self.current_pos
        self.current_pos += 1

        # Além do fim real do arquivo: falha
        if pos >= self.actual_eof:
            return False

        # Dentro de uma zona corrompida: falha
        for start, end in self.corrupt_ranges:
            if start <= pos <= end:
                return False

        return True


class AlgoResult(NamedTuple):
    name: str
    status: str  # "RECOVERED", "EOF_ADJUSTED", "ERROR_ZERO"
    recovered_frame: int | None
    new_frame_count: int
    seeks: int
    grabs: int
    duration_us: float


# ==============================================================================
# 1. ALGORITMO ATUAL COM KEYFRAMES (Tail Candidate Binary Search)
# ==============================================================================
def run_current_with_keyframes(src: InstrumentedVideoSource, current_pos: int) -> AlgoResult:
    start_time = time.perf_counter()
    kfs = [k for k in src.keyframes if k < src.nominal_frame_count]
    if not kfs:
        return AlgoResult("Atual (com Keyframes)", "FAILED_NO_KFS", None, src.nominal_frame_count, src.seek_count, src.grab_count, 0)

    last_good = -1
    # Checa último candidato
    src.set_pos(kfs[-1])
    if src.grab():
        last_good = kfs[-1]
    else:
        low_idx = 0
        high_idx = len(kfs) - 2
        while low_idx <= high_idx:
            mid_idx = (low_idx + high_idx) // 2
            target = kfs[mid_idx]
            src.set_pos(target)
            if src.grab():
                last_good = target
                low_idx = mid_idx + 1
            else:
                high_idx = mid_idx - 1

    if last_good >= 0:
        curr = last_good
        # Nota: implementação atual não dava set(last_good) antes do while
        while src.grab():
            curr += 1
        new_count = curr + 1
        duration = (time.perf_counter() - start_time) * 1_000_000
        return AlgoResult("Atual (com Keyframes)", "EOF_ADJUSTED", curr, new_count, src.seek_count, src.grab_count, duration)

    duration = (time.perf_counter() - start_time) * 1_000_000
    return AlgoResult("Atual (com Keyframes)", "ERROR_ZERO", 0, 0, src.seek_count, src.grab_count, duration)


# ==============================================================================
# 2. ALGORITMO ATUAL SEM KEYFRAMES (Reverse Galloping do Final)
# ==============================================================================
def run_current_without_keyframes(src: InstrumentedVideoSource, current_pos: int, sequential_threshold: int = 64) -> AlgoResult:
    start_time = time.perf_counter()
    high = src.nominal_frame_count - 1
    src.set_pos(high)
    if src.grab():
        duration = (time.perf_counter() - start_time) * 1_000_000
        return AlgoResult("Atual (sem Keyframes)", "EOF_ADJUSTED", high, high + 1, src.seek_count, src.grab_count, duration)

    step = 16
    b_low = None
    b_high = high
    while step < src.nominal_frame_count:
        target = max(0, high - step)
        src.set_pos(target)
        if src.grab():
            b_low = target
            b_high = high - (step // 16) if step > 16 else high
            break
        step *= 16

    if b_low is None:
        src.set_pos(0)
        if not src.grab():
            duration = (time.perf_counter() - start_time) * 1_000_000
            return AlgoResult("Atual (sem Keyframes)", "ERROR_ZERO", 0, 0, src.seek_count, src.grab_count, duration)
        b_low = 0

    last_good = b_low
    while (b_high - b_low) > sequential_threshold:
        mid = (b_low + b_high) // 2
        src.set_pos(mid)
        if src.grab():
            last_good = mid
            b_low = mid + 1
        else:
            b_high = mid - 1

    src.set_pos(last_good)
    src.grab()
    curr = last_good
    while src.grab():
        curr += 1

    duration = (time.perf_counter() - start_time) * 1_000_000
    return AlgoResult("Atual (sem Keyframes)", "EOF_ADJUSTED", curr, curr + 1, src.seek_count, src.grab_count, duration)


# ==============================================================================
# 3. NOVO ALGORITMO COM KEYFRAMES (Tentativas 2^N ate N=4 + Forward Keyframes)
# ==============================================================================
def run_new_with_keyframes(src: InstrumentedVideoSource, current_pos: int) -> AlgoResult:
    start_time = time.perf_counter()

    # 1. Tentativas exponenciais 2^N com N de 0 a 4 (passos 1, 2, 4, 8, 16)
    last_failed = current_pos
    for n in range(5):  # N=0..4 -> 2^0=1, 2^1=2, 2^2=4, 2^3=8, 2^4=16
        step = 1 << n
        target = current_pos + step
        if target >= src.nominal_frame_count:
            break
        src.set_pos(target)
        if src.grab():
            duration = (time.perf_counter() - start_time) * 1_000_000
            return AlgoResult("Novo (com Keyframes)", "RECOVERED", target, src.nominal_frame_count, src.seek_count, src.grab_count, duration)
        last_failed = target

    # 2. Apos N=4 (16 frames), busca galopante exponencial nos keyframes a frente
    kfs = src.keyframes
    start_idx = bisect.bisect_right(kfs, last_failed)
    first_valid_kf = None

    step_kf = 1
    curr_idx = start_idx
    b_low = start_idx
    b_high = None

    while curr_idx < len(kfs) and kfs[curr_idx] < src.nominal_frame_count:
        target = kfs[curr_idx]
        src.set_pos(target)
        if src.grab():
            b_high = curr_idx
            break
        last_failed = target
        b_low = curr_idx + 1
        curr_idx = start_idx + step_kf
        step_kf *= 2

    # Se encontramos um indice superior valido, busca binaria na janela de keyframes
    if b_high is not None:
        low = b_low
        high = b_high
        best_kf_idx = b_high
        while low <= high:
            mid = (low + high) // 2
            src.set_pos(kfs[mid])
            if src.grab():
                best_kf_idx = mid
                high = mid - 1
            else:
                low = mid + 1
        first_valid_kf = kfs[best_kf_idx]

    if first_valid_kf is not None:
        duration = (time.perf_counter() - start_time) * 1_000_000
        return AlgoResult("Novo (com Keyframes)", "RECOVERED", first_valid_kf, src.nominal_frame_count, src.seek_count, src.grab_count, duration)

    # 3. Nenhum keyframe decodifica ate o fim: arquivo acabou fisicamente ali!
    low = max(0, current_pos - 1)
    high = min(src.nominal_frame_count - 1, last_failed)
    last_good = low
    while low <= high:
        mid = (low + high) // 2
        src.set_pos(mid)
        if src.grab():
            last_good = mid
            low = mid + 1
        else:
            high = mid - 1

    new_count = last_good + 1
    duration = (time.perf_counter() - start_time) * 1_000_000
    return AlgoResult("Novo (com Keyframes)", "EOF_ADJUSTED", last_good, new_count, src.seek_count, src.grab_count, duration)


# ==============================================================================
# 4. NOVO ALGORITMO SEM KEYFRAMES (Tentativas 2^N continuas + Binary Search)
# ==============================================================================
def run_new_without_keyframes(src: InstrumentedVideoSource, current_pos: int) -> AlgoResult:
    start_time = time.perf_counter()

    # Tentativas galopantes continuas 2^N para N >= 0 (1, 2, 4, 8, 16, 32, 64, 128...)
    n = 0
    last_failed = current_pos
    first_valid = None

    while True:
        step = 1 << n  # 2^n
        target = current_pos + step
        if target >= src.nominal_frame_count:
            break
        src.set_pos(target)
        if src.grab():
            first_valid = target
            break
        last_failed = target
        n += 1

    if first_valid is not None:
        # Se n == 0, recuperou no frame seguinte imediato
        if n == 0:
            duration = (time.perf_counter() - start_time) * 1_000_000
            return AlgoResult("Novo (sem Keyframes)", "RECOVERED", first_valid, src.nominal_frame_count, src.seek_count, src.grab_count, duration)

        # Se n > 0, busca binaria na janela [last_failed, first_valid] para achar o 1o decodificavel
        low = last_failed + 1
        high = first_valid
        exact_recovery = first_valid
        while low <= high:
            mid = (low + high) // 2
            src.set_pos(mid)
            if src.grab():
                exact_recovery = mid
                high = mid - 1
            else:
                low = mid + 1

        duration = (time.perf_counter() - start_time) * 1_000_000
        return AlgoResult("Novo (sem Keyframes)", "RECOVERED", exact_recovery, src.nominal_frame_count, src.seek_count, src.grab_count, duration)

    # Nenhum positivo ate o fim: arquivo acabou!
    low = max(0, current_pos - 1)
    high = min(src.nominal_frame_count - 1, last_failed)
    last_good = low
    while low <= high:
        mid = (low + high) // 2
        src.set_pos(mid)
        if src.grab():
            last_good = mid
            low = mid + 1
        else:
            high = mid - 1

    new_count = last_good + 1
    duration = (time.perf_counter() - start_time) * 1_000_000
    return AlgoResult("Novo (sem Keyframes)", "EOF_ADJUSTED", last_good, new_count, src.seek_count, src.grab_count, duration)


# ==============================================================================
# SUÍTE DE CENÁRIOS COMPARATIVOS
# ==============================================================================
def run_benchmark():
    total_frames = 34053
    # Gera keyframes a cada 24 frames (~1s em 24fps)
    simulated_kfs = list(range(0, total_frames, 24))

    scenarios = [
        {
            "title": "CENÁRIO 1: Falha isolada no meio do vídeo (Frame 15.000 corrompido)",
            "nominal": total_frames,
            "actual_eof": total_frames,
            "corrupt": [(15000, 15000)],
            "fail_pos": 15000,
        },
        {
            "title": "CENÁRIO 2: Buraco de 48 frames no meio do vídeo (Frames 15.000..15.047 corrompidos)",
            "nominal": total_frames,
            "actual_eof": total_frames,
            "corrupt": [(15000, 15047)],
            "fail_pos": 15000,
        },
        {
            "title": "CENÁRIO 3: Cauda truncada pelo container (Nominal 34.053, físico termina em 34.047)",
            "nominal": total_frames,
            "actual_eof": 34047,
            "corrupt": [],
            "fail_pos": 34047,
        },
        {
            "title": "CENÁRIO 4: Download incompleto cortado no meio (Físico termina no frame 15.000)",
            "nominal": total_frames,
            "actual_eof": 15000,
            "corrupt": [],
            "fail_pos": 15000,
        },
    ]

    print("=" * 80)
    print(" BENCHMARK COMPARATIVO: 4 ALGORITMOS DE DETECÇÃO E RECUPERAÇÃO")
    print("=" * 80)

    for sc in scenarios:
        print(f"\n▶ {sc['title']}")
        print("-" * 80)
        print(f"{'Algoritmo':<26} | {'Status':<12} | {'Recup/EOF':<10} | {'Total':<6} | {'Seeks':<5} | {'Grabs':<5} | {'Tempo'}")
        print("-" * 80)

        algos = [
            ("Atual (com Keyframes)", run_current_with_keyframes),
            ("Atual (sem Keyframes)", run_current_without_keyframes),
            ("Novo (com Keyframes)", run_new_with_keyframes),
            ("Novo (sem Keyframes)", run_new_without_keyframes),
        ]

        for name, func in algos:
            src = InstrumentedVideoSource(
                frame_count=sc["nominal"],
                keyframes=simulated_kfs,
                corrupt_ranges=sc["corrupt"],
                actual_eof=sc["actual_eof"],
            )
            res = func(src, sc["fail_pos"])
            rec_str = str(res.recovered_frame) if res.recovered_frame is not None else "-"
            print(f"{res.name:<26} | {res.status:<12} | {rec_str:<10} | {res.new_frame_count:<6} | {res.seeks:<5} | {res.grabs:<5} | {res.duration_us:>6.1f} µs")


if __name__ == "__main__":
    run_benchmark()


def run_real_video_benchmark():
    import cv2
    from pathlib import Path
    from aniseek.core.keyframes import parse_mkv_cues

    vpath = Path("/home/gui/Downloads/Animes/2024/1-winter-2024/Mato Seihei no Slave/Mato Seihei no Slave 09.mkv")
    if not vpath.is_file():
        print("Arquivo de teste real não encontrado.")
        return

    cap = cv2.VideoCapture(str(vpath))
    nominal = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    kfs = parse_mkv_cues(vpath, fps) or []
    cap.release()

    class RealVideoAdapter:
        def __init__(self, video_path: Path, nominal_count: int, keyframes: list[int]):
            self.cap = cv2.VideoCapture(str(video_path))
            self.nominal_frame_count = nominal_count
            self.keyframes = keyframes
            self.seek_count = 0
            self.grab_count = 0

        def set_pos(self, frame_id: int):
            self.seek_count += 1
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_id)

        def grab(self) -> bool:
            self.grab_count += 1
            return bool(self.cap.grab())

        def release(self):
            self.cap.release()

    print("\n" + "=" * 80)
    print(" BENCHMARK EM ARQUIVO REAL: Mato Seihei no Slave 09.mkv")
    print(f" (Nominal: {nominal} frames, FPS: {fps:.2f}, Keyframes: {len(kfs)})")
    print("=" * 80)

    # Testando fim de arquivo no vídeo real (EOF probe em nominal - 1)
    print("\n▶ CENÁRIO REAL: Verificação de cauda / EOF no arquivo físico real")
    print("-" * 80)
    print(f"{'Algoritmo':<26} | {'Status':<12} | {'Recup/EOF':<10} | {'Total':<6} | {'Seeks':<5} | {'Grabs':<5} | {'Tempo'}")
    print("-" * 80)

    algos = [
        ("Atual (com Keyframes)", run_current_with_keyframes),
        ("Atual (sem Keyframes)", run_current_without_keyframes),
        ("Novo (com Keyframes)", run_new_with_keyframes),
        ("Novo (sem Keyframes)", run_new_without_keyframes),
    ]

    for name, func in algos:
        adapter = RealVideoAdapter(vpath, nominal, kfs)
        res = func(adapter, nominal - 1)
        adapter.release()
        rec_str = str(res.recovered_frame) if res.recovered_frame is not None else "-"
        print(f"{res.name:<26} | {res.status:<12} | {rec_str:<10} | {res.new_frame_count:<6} | {res.seeks:<5} | {res.grabs:<5} | {res.duration_us / 1000:>6.2f} ms")


if __name__ == "__main__":
    run_benchmark()
    run_real_video_benchmark()
