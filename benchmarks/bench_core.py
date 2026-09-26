from __future__ import annotations

import argparse
import gc
import json
import platform
import statistics
import time
import tracemalloc
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from loguru import logger

from aniseek.core.interfaces.source import IFrameSource
from aniseek.core.sources.opencv import OpenCVVideoSource
from aniseek.core.sources.registry import source_registry
from aniseek.core.video_reader import Direction, VideoReader

logger.disable("aniseek")

# Registro de backends disponíveis para benchmark
AVAILABLE_BACKENDS: dict[str, type[IFrameSource]] = {
    "opencv": OpenCVVideoSource,
}

# Tentativa de importação de backends opcionais (ex: PyAV futuro)
try:
    from aniseek.core.sources.pyav import (
        PyAVVideoSource,  # type: ignore[import-not-found]
    )
    AVAILABLE_BACKENDS["pyav"] = PyAVVideoSource
except ImportError:
    pass


@dataclass
class BenchmarkResults:
    backend: str
    video_path: str
    video_resolution: str
    cpu_model: str
    system_os: str
    python_version: str
    timestamp: float
    ttff_ms: float
    forward_fps: float
    forward_mean_ms: float
    reverse_fps: float
    reverse_mean_ms: float
    ping_pong_p50_ms: float
    ping_pong_p95_ms: float
    ping_pong_mean_ms: float
    sparse_step5_fps: float
    sparse_step5_elapsed_s: float
    memory_peak_mb: float
    gc_collections: int


def get_cpu_model() -> str:
    """Detecta o nome do modelo da CPU."""
    if platform.system() == "Linux":
        try:
            with open("/proc/cpuinfo") as f:
                for line in f:
                    if "model name" in line:
                        return line.split(":", 1)[1].strip()
        except OSError:
            pass
    return platform.processor() or "Unknown CPU"


def bench_ttff(path: Path, backend_cls: type[IFrameSource], source_kwargs: dict[str, Any]) -> float:
    """Mede o tempo até o primeiro frame válido (Time to First Frame)."""
    with source_registry.use(video=backend_cls):
        start = time.perf_counter()
        reader = VideoReader.from_default(path, buffersize=30, **source_kwargs)
        try:
            reader.read()
            elapsed_ms = (time.perf_counter() - start) * 1000.0
        finally:
            reader.close()
    return round(elapsed_ms, 2)


def bench_forward(
    path: Path,
    backend_cls: type[IFrameSource],
    num_frames: int,
    source_kwargs: dict[str, Any],
) -> tuple[float, float]:
    """Mede o throughput de leitura sequencial em avanço (+1)."""
    with source_registry.use(video=backend_cls):
        reader = VideoReader.from_default(
            path,
            start=0,
            end=num_frames,
            buffersize=30,
            **source_kwargs,
        )
        count = 0
        try:
            start = time.perf_counter()
            while not reader.is_task_complete:
                ret, _ = reader.read()
                if ret:
                    count += 1
                if count >= num_frames:
                    break
            elapsed = time.perf_counter() - start
        finally:
            reader.close()

    fps = round(count / elapsed, 2) if elapsed > 0 else 0.0
    mean_ms = round((elapsed / count) * 1000.0, 2) if count > 0 else 0.0
    return fps, mean_ms


def bench_reverse(
    path: Path,
    backend_cls: type[IFrameSource],
    num_frames: int,
    start_offset: int,
    source_kwargs: dict[str, Any],
) -> tuple[float, float]:
    """Mede o throughput de leitura sequencial reversa (-1)."""
    with source_registry.use(video=backend_cls):
        start_idx = max(0, start_offset - num_frames)
        end_idx = start_offset
        reader = VideoReader.from_default(
            path,
            start=start_idx,
            end=end_idx,
            direction=Direction.REVERSE,
            buffersize=30,
            **source_kwargs,
        )
        count = 0
        try:
            start = time.perf_counter()
            while not reader.is_task_complete:
                ret, _ = reader.read()
                if ret:
                    count += 1
                if count >= num_frames:
                    break
            elapsed = time.perf_counter() - start
        finally:
            reader.close()

    fps = round(count / elapsed, 2) if elapsed > 0 else 0.0
    mean_ms = round((elapsed / count) * 1000.0, 2) if count > 0 else 0.0
    return fps, mean_ms


def bench_ping_pong(
    path: Path,
    backend_cls: type[IFrameSource],
    cycles: int,
    step_frames: int,
    source_kwargs: dict[str, Any],
) -> tuple[float, float, float]:
    """Mede a latência de troca de direção (Master/Servant Ping-Pong)."""
    with source_registry.use(video=backend_cls):
        reader = VideoReader.from_default(
            path,
            start=20,
            end=300,
            buffersize=30,
            **source_kwargs,
        )
        latencies: list[float] = []
        try:
            # Pré-carregamento suave
            for _ in range(5):
                reader.read()

            for _ in range(cycles):
                # Inversão para trás
                t0 = time.perf_counter()
                reader.rewind()
                reader.read()
                latencies.append((time.perf_counter() - t0) * 1000.0)

                for _ in range(step_frames - 1):
                    reader.read()

                # Inversão para frente
                t1 = time.perf_counter()
                reader.proceed()
                reader.read()
                latencies.append((time.perf_counter() - t1) * 1000.0)

                for _ in range(step_frames - 1):
                    reader.read()
        finally:
            reader.close()

    p50 = round(statistics.median(latencies), 2) if latencies else 0.0
    p95 = round(statistics.quantiles(latencies, n=20)[18], 2) if len(latencies) >= 20 else p50
    mean_val = round(statistics.mean(latencies), 2) if latencies else 0.0
    return p50, p95, mean_val


def bench_sparse_step(
    path: Path,
    backend_cls: type[IFrameSource],
    total_range: int,
    step: int,
    source_kwargs: dict[str, Any],
) -> tuple[float, float]:
    """Mede a eficiência do salto de frames com cap.grab()."""
    with source_registry.use(video=backend_cls):
        reader = VideoReader.from_default(
            path,
            start=0,
            end=total_range,
            step=step,
            buffersize=30,
            **source_kwargs,
        )
        count = 0
        try:
            start = time.perf_counter()
            while not reader.is_task_complete:
                ret, _ = reader.read()
                if ret:
                    count += 1
            elapsed = time.perf_counter() - start
        finally:
            reader.close()

    fps = round(count / elapsed, 2) if elapsed > 0 else 0.0
    return fps, round(elapsed, 2)


def bench_memory_gc(
    path: Path,
    backend_cls: type[IFrameSource],
    num_frames: int,
    source_kwargs: dict[str, Any],
) -> tuple[float, int]:
    """Mede o pico de RAM e o número de coletas de Garbage Collection."""
    gc.collect()
    gc_before = sum(stat["collections"] for stat in gc.get_stats())

    tracemalloc.start()
    with source_registry.use(video=backend_cls):
        reader = VideoReader.from_default(
            path,
            start=0,
            end=num_frames,
            buffersize=30,
            **source_kwargs,
        )
        count = 0
        try:
            while not reader.is_task_complete and count < num_frames:
                ret, _ = reader.read()
                if ret:
                    count += 1
        finally:
            reader.close()

    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    gc_after = sum(stat["collections"] for stat in gc.get_stats())
    gc_diff = max(0, gc_after - gc_before)
    peak_mb = round(peak / (1024 * 1024), 2)
    return peak_mb, gc_diff


def run_benchmark(
    video_path: Path,
    backend_name: str,
    frames: int,
    source_kwargs: dict[str, Any] | None = None,
) -> BenchmarkResults:
    """Executa a bateria completa de benchmarks para o backend selecionado."""
    if backend_name not in AVAILABLE_BACKENDS:
        raise ValueError(
            f"Backend '{backend_name}' não suportado. "
            f"Opções disponíveis: {list(AVAILABLE_BACKENDS.keys())}"
        )

    backend_cls = AVAILABLE_BACKENDS[backend_name]
    kwargs = source_kwargs or {}

    print("\n=======================================================")
    print("🚀 Iniciando Benchmark do aniseek.core")
    print(f"   Backend: {backend_name}")
    print(f"   Vídeo:   {video_path.name}")
    print("=======================================================")

    # Medição do vídeo
    source_temp = backend_cls(video_path)
    res_str = f"{int(source_temp.frame_count)} frames @ {source_temp.fps:.2f}fps"
    source_temp.release()

    print("1/6 Testando Time to First Frame (TTFF)...")
    ttff = bench_ttff(video_path, backend_cls, kwargs)

    print(f"2/6 Testando Throughput Forward (+1) em {frames} frames...")
    fwd_fps, fwd_ms = bench_forward(video_path, backend_cls, frames, kwargs)

    print(f"3/6 Testando Throughput Reverse (-1) em {frames} frames...")
    rev_fps, rev_ms = bench_reverse(video_path, backend_cls, frames, 250, kwargs)

    print("4/6 Testando Latência Ping-Pong (Inversão Master/Servant)...")
    p50, p95, mean_lat = bench_ping_pong(video_path, backend_cls, cycles=15, step_frames=5, source_kwargs=kwargs)

    print("5/6 Testando Fatiamento Esparso (step=5 / cap.grab)...")
    step_fps, step_time = bench_sparse_step(video_path, backend_cls, total_range=min(frames * 2, 400), step=5, source_kwargs=kwargs)

    print("6/6 Monitorando Alocação de Memória e Coletas do GC...")
    peak_mb, gc_cycles = bench_memory_gc(video_path, backend_cls, min(frames, 150), kwargs)

    return BenchmarkResults(
        backend=backend_name,
        video_path=str(video_path),
        video_resolution=res_str,
        cpu_model=get_cpu_model(),
        system_os=f"{platform.system()} {platform.release()}",
        python_version=platform.python_version(),
        timestamp=time.time(),
        ttff_ms=ttff,
        forward_fps=fwd_fps,
        forward_mean_ms=fwd_ms,
        reverse_fps=rev_fps,
        reverse_mean_ms=rev_ms,
        ping_pong_p50_ms=p50,
        ping_pong_p95_ms=p95,
        ping_pong_mean_ms=mean_lat,
        sparse_step5_fps=step_fps,
        sparse_step5_elapsed_s=step_time,
        memory_peak_mb=peak_mb,
        gc_collections=gc_cycles,
    )


def print_report(res: BenchmarkResults, compare_res: BenchmarkResults | None = None) -> None:
    """Imprime o relatório formatado no terminal com comparação opcional."""
    print("\n" + "=" * 70)
    print("📊 RELATÓRIO DE DESEMPENHO (aniseek.core)")
    print(f"   CPU:      {res.cpu_model}")
    print(f"   Backend:  {res.backend.upper()}" + (f" (comparado com: {compare_res.backend.upper()})" if compare_res else ""))
    print(f"   Vídeo:    {Path(res.video_path).name} ({res.video_resolution})")
    print("=" * 70)

    header = f"{'Métrica':<35} | {'Atual':>12}"
    if compare_res:
        header += f" | {'Base':>12} | {'Variação':>10}"
    print(header)
    print("-" * len(header))

    def row(label: str, val_now: float, val_base: float | None, unit: str = "", higher_is_better: bool = True) -> None:
        val_str = f"{val_now:.2f} {unit}".strip()
        if val_base is None:
            print(f"{label:<35} | {val_str:>12}")
            return

        base_str = f"{val_base:.2f} {unit}".strip()
        if val_base == 0:
            delta_str = "N/A"
        else:
            diff = ((val_now - val_base) / val_base) * 100.0
            sign = "+" if diff > 0 else ""
            good = (diff > 0 and higher_is_better) or (diff < 0 and not higher_is_better)
            indicator = "🟢" if good else ("⚪" if abs(diff) < 2 else "🔴")
            delta_str = f"{sign}{diff:.1f}% {indicator}"
        print(f"{label:<35} | {val_str:>12} | {base_str:>12} | {delta_str:>10}")

    c = compare_res
    row("Tempo até 1º Frame (TTFF)", res.ttff_ms, c.ttff_ms if c else None, "ms", higher_is_better=False)
    row("Throughput Forward (+1)", res.forward_fps, c.forward_fps if c else None, "fps", higher_is_better=True)
    row("Tempo Médio por Frame Forward", res.forward_mean_ms, c.forward_mean_ms if c else None, "ms", higher_is_better=False)
    row("Throughput Reverse (-1)", res.reverse_fps, c.reverse_fps if c else None, "fps", higher_is_better=True)
    row("Tempo Médio por Frame Reverse", res.reverse_mean_ms, c.reverse_mean_ms if c else None, "ms", higher_is_better=False)
    row("Latência Ping-Pong (Mediana p50)", res.ping_pong_p50_ms, c.ping_pong_p50_ms if c else None, "ms", higher_is_better=False)
    row("Latência Ping-Pong (Pico p95)", res.ping_pong_p95_ms, c.ping_pong_p95_ms if c else None, "ms", higher_is_better=False)
    row("Throughput Fatiamento (step=5)", res.sparse_step5_fps, c.sparse_step5_fps if c else None, "fps", higher_is_better=True)
    row("Pico de Memória Alocada", res.memory_peak_mb, c.memory_peak_mb if c else None, "MB", higher_is_better=False)
    row("Ciclos de Garbage Collection", float(res.gc_collections), float(c.gc_collections) if c else None, "", higher_is_better=False)

    print("=" * len(header) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark de desempenho do aniseek.core")
    parser.add_argument(
        "--video",
        type=str,
        default="assets/xmodel.mp4",
        help="Caminho do vídeo para teste",
    )
    parser.add_argument(
        "--backend",
        type=str,
        default="opencv",
        choices=list(AVAILABLE_BACKENDS.keys()),
        help="Backend de decodificação",
    )
    parser.add_argument(
        "--frames",
        type=int,
        default=150,
        help="Quantidade de frames por teste",
    )
    parser.add_argument(
        "--save",
        type=str,
        default=None,
        help="Salvar resultado em arquivo JSON",
    )
    parser.add_argument(
        "--compare",
        type=str,
        default=None,
        help="Comparar com resultado JSON existente",
    )

    args = parser.parse_args()

    vpath = Path(args.video)
    if not vpath.exists():
        # Fallbacks em assets/ e raiz
        candidate_fallbacks = [
            Path("assets/xmodel.mp4"),
            Path("assets/model.mp4"),
            Path("xmodel.mp4"),
            Path("model.mp4"),
        ]
        for candidate in candidate_fallbacks:
            if candidate.exists():
                vpath = candidate
                break
        else:
            raise FileNotFoundError(f"Vídeo de teste não encontrado: {args.video}")

    results = run_benchmark(
        video_path=vpath,
        backend_name=args.backend,
        frames=args.frames,
    )

    compare_results: BenchmarkResults | None = None
    if args.compare:
        cmp_path = Path(args.compare)
        if cmp_path.exists():
            with open(cmp_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                compare_results = BenchmarkResults(**data)
        else:
            print(f"⚠️ Arquivo de comparação '{args.compare}' não encontrado. Exibindo apenas resultado atual.")

    print_report(results, compare_results)

    if args.save:
        save_path = Path(args.save)
        save_path.parent.mkdir(parents=True, exist_ok=True)
        with open(save_path, "w", encoding="utf-8") as f:
            json.dump(asdict(results), f, indent=2)
        print(f"💾 Resultados gravados com sucesso em: {save_path}")


if __name__ == "__main__":
    main()
