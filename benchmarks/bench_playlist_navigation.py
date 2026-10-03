#!/usr/bin/env python3
"""Benchmark determinístico para navegação de playlist, lazy open e recuperação de frames inválidos.

Este script gera dados sintéticos padronizados e mede a evolução das métricas de performance:
1. Troca rápida de vídeos na playlist (lazy open vs abertura síncrona).
2. Transição ao fim da seção em modo rewind (PrevVideoEndCommand).
3. Throughput de reprodução em rewind aproveitando o cache em memória RAM.
4. Recuperação e ajuste imediato em arquivos com cauda de frames inválidos/truncados.
5. Throughput de seções esparsas com faixas inválidas intercaladas (grab vs read).
"""

from __future__ import annotations

import argparse
import json
import platform
import statistics
import time
from dataclasses import asdict, dataclass
from pathlib import Path

import cv2
import numpy as np
from loguru import logger

from aniseek.core.sources.opencv import OpenCVVideoSource
from aniseek.core.video_reader import VideoReader
from aniseek.editing.playlist import Playlist
from aniseek.editing.section import SectionManager, VideoSection
from aniseek.view import FrameViewer, NextVideoCommand, PrevVideoEndCommand

# Desativa logs verbose durante a execução dos benchmarks para não distorcer medições
logger.disable("aniseek")


@dataclass
class PlaylistBenchmarkResults:
    cpu_model: str
    system_os: str
    python_version: str
    timestamp: float
    # Métrica 1: Troca de vídeos
    lazy_switch_next_ms: float
    lazy_switch_prev_ms: float
    # Métrica 2: Salto ao final em rewind
    prev_video_end_total_ms: float
    # Métrica 3: Throughput do cache de rewind
    rewind_cache_fps: float
    rewind_cache_mean_ms: float
    # Métrica 4: Recuperação de cauda inválida
    tail_probe_resolution_ms: float
    # Métrica 5: Seções esparsas com faixas inválidas
    sparse_throughput_fps: float


def get_cpu_model() -> str:
    """Detecta o modelo da CPU do sistema."""
    if platform.system() == "Linux":
        try:
            with open("/proc/cpuinfo") as f:
                for line in f:
                    if "model name" in line:
                        return line.split(":", 1)[1].strip()
        except OSError:
            pass
    return platform.processor() or "Unknown CPU"


def generate_benchmark_assets(data_dir: Path, force: bool = False) -> tuple[Path, Path, Path]:
    """Gera vídeos sintéticos determinísticos para o benchmark."""
    data_dir.mkdir(parents=True, exist_ok=True)
    v1_path = data_dir / "bench_sample_01.mkv"
    v2_path = data_dir / "bench_sample_02.mkv"
    trunc_path = data_dir / "bench_sample_truncated.mkv"

    if not force and v1_path.exists() and v2_path.exists() and trunc_path.exists():
        return v1_path, v2_path, trunc_path

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    width, height, fps = 320, 240, 30.0

    def make_video(path: Path, num_frames: int, base_color: tuple[int, int, int]) -> None:
        out = cv2.VideoWriter(str(path), fourcc, fps, (width, height))
        for i in range(num_frames):
            img = np.full((height, width, 3), base_color, dtype=np.uint8)
            cv2.putText(
                img,
                f"Frame {i:04d}",
                (30, 130),
                cv2.FONT_HERSHEY_SIMPLEX,
                1.0,
                (255, 255, 255),
                2,
            )
            out.write(img)
        out.release()

    # Cria dois vídeos padrão com 300 frames cada
    make_video(v1_path, 300, (40, 40, 120))
    make_video(v2_path, 300, (120, 40, 40))

    # Cria vídeo com metadados declarando 200 frames mas com cauda truncada (faltando frames no fim)
    raw_trunc = data_dir / "temp_trunc.mkv"
    make_video(raw_trunc, 200, (40, 120, 40))
    raw_data = raw_trunc.read_bytes()
    # Trunca os últimos 3500 bytes mantendo o cabeçalho intacto
    trunc_path.write_bytes(raw_data[:-3500])
    raw_trunc.unlink(missing_ok=True)

    return v1_path, v2_path, trunc_path


def bench_lazy_switching(v1: Path, v2: Path, runs: int = 10) -> tuple[float, float]:
    """Mede a latência da troca rápida entre vídeos na playlist."""
    playlist = Playlist(videos=[v1, v2])
    viewer = FrameViewer.from_playlist(playlist=playlist)
    ctrl = viewer.video_controller

    next_times: list[float] = []
    prev_times: list[float] = []

    for _ in range(runs):
        t0 = time.perf_counter()
        ctrl.next_video()
        next_times.append((time.perf_counter() - t0) * 1000.0)

        t1 = time.perf_counter()
        ctrl.prev_video()
        prev_times.append((time.perf_counter() - t1) * 1000.0)

    viewer.join()
    return round(statistics.median(next_times), 3), round(statistics.median(prev_times), 3)


def bench_prev_video_end(v1: Path, v2: Path, runs: int = 5) -> tuple[float, float, float]:
    """Mede a transição para o fim do vídeo anterior e a taxa de quadros no rewind."""
    playlist = Playlist(videos=[v1, v2])
    viewer = FrameViewer.from_playlist(playlist=playlist)
    ctrl = viewer.video_controller
    cmd_prev_end = PrevVideoEndCommand(ctrl, prefill_frames=30)
    cmd_next = NextVideoCommand(ctrl)

    transition_times: list[float] = []
    rewind_latencies: list[float] = []

    for _ in range(runs):
        # Avança para o vídeo 2
        cmd_next.on_press()
        viewer.read()

        # Mede a transição para o final do vídeo 1 em rewind
        t0 = time.perf_counter()
        cmd_prev_end.on_press()
        flag, frame = viewer.read()
        t1 = time.perf_counter()
        transition_times.append((t1 - t0) * 1000.0)

        # Consome os primeiros 20 frames em rewind direto do cache da RAM
        for _ in range(20):
            t_frame = time.perf_counter()
            f_flag, f_frame = viewer.read()
            rewind_latencies.append((time.perf_counter() - t_frame) * 1000.0)

    viewer.join()
    mean_trans = round(statistics.mean(transition_times), 2)
    mean_rewind_lat = round(statistics.mean(rewind_latencies), 4)
    fps_rewind = round(1000.0 / mean_rewind_lat, 2) if mean_rewind_lat > 0 else 0.0

    return mean_trans, fps_rewind, mean_rewind_lat


def bench_tail_probe_recovery(trunc_path: Path, runs: int = 5) -> float:
    """Mede o tempo de recuperação imediata em arquivos com cauda de frames inválidos."""
    times: list[float] = []
    for _ in range(runs):
        source = OpenCVVideoSource(trunc_path)
        nominal_count = source.frame_count

        t0 = time.perf_counter()
        # Força leitura no frame nominal extremo que falhará e disparará o probe reverso
        source.seek(nominal_count - 1)
        source.read()
        t1 = time.perf_counter()
        times.append((t1 - t0) * 1000.0)
        source.release()

    return round(statistics.median(times), 3)


def bench_sparse_sections_throughput(v1: Path) -> float:
    """Mede o throughput de reprodução de seções esparsas com faixas inválidas intercaladas."""
    # Define seções válidas intercaladas com lacunas (faixas inválidas que devem ser puladas via grab)
    sections = [
        VideoSection(0, 50),
        VideoSection(80, 140),
        VideoSection(180, 260),
    ]
    sec_manager = SectionManager(sections)
    valid_frames = sec_manager.get_mapping()

    reader = VideoReader.from_default(v1, frames=valid_frames, buffersize=30)
    read_count = 0

    t0 = time.perf_counter()
    while not reader.is_task_complete:
        flag, frame = reader.read()
        if flag:
            read_count += 1
    elapsed = time.perf_counter() - t0
    reader.close()

    fps = round(read_count / elapsed, 2) if elapsed > 0 else 0.0
    return fps


def run_all_benchmarks(data_dir: Path, force_gen: bool = False) -> PlaylistBenchmarkResults:
    """Executa todos os testes de performance da suíte de navegação."""
    v1, v2, v_trunc = generate_benchmark_assets(data_dir, force=force_gen)

    next_ms, prev_ms = bench_lazy_switching(v1, v2)
    end_ms, rewind_fps, rewind_lat_ms = bench_prev_video_end(v1, v2)
    probe_ms = bench_tail_probe_recovery(v_trunc)
    sparse_fps = bench_sparse_sections_throughput(v1)

    return PlaylistBenchmarkResults(
        cpu_model=get_cpu_model(),
        system_os=f"{platform.system()} {platform.release()}",
        python_version=platform.python_version(),
        timestamp=time.time(),
        lazy_switch_next_ms=next_ms,
        lazy_switch_prev_ms=prev_ms,
        prev_video_end_total_ms=end_ms,
        rewind_cache_fps=rewind_fps,
        rewind_cache_mean_ms=rewind_lat_ms,
        tail_probe_resolution_ms=probe_ms,
        sparse_throughput_fps=sparse_fps,
    )


def print_report(
    current: PlaylistBenchmarkResults,
    baseline: PlaylistBenchmarkResults | None = None,
) -> None:
    """Imprime relatório formatado e detalhado no terminal com comparação opcional."""
    print("\n" + "=" * 80)
    print("        🚀 ANISEEK BENCHMARK: PLAYLIST NAVIGATION & LAZY BUFFERING")
    print("=" * 80)
    print(f" CPU: {current.cpu_model}")
    print(f" OS:  {current.system_os} | Python: {current.python_version}")
    print("-" * 80)

    col1 = "Métrica / Cenário de Teste"
    col2 = "Resultado Atual"
    col3 = "Referência (dev)"
    col4 = "Variação"

    if baseline is not None:
        print(f"{col1:<44} | {col2:>12} | {col3:>14} | {col4:>12}")
        print("-" * 88)
    else:
        print(f"{col1:<54} | {col2:>20}")
        print("-" * 78)

    def row(label: str, cur_val: float, base_val: float | None, unit: str, higher_is_better: bool = False):
        cur_str = f"{cur_val:.2f} {unit}"
        if baseline is None or base_val is None:
            print(f"{label:<54} | {cur_str:>20}")
            return

        base_str = f"{base_val:.2f} {unit}"
        if base_val > 0:
            if higher_is_better:
                diff_pct = ((cur_val - base_val) / base_val) * 100.0
            else:
                # Menor tempo é melhor
                diff_pct = ((base_val - cur_val) / base_val) * 100.0
            sign = "+" if diff_pct > 0 else ""
            diff_str = f"{sign}{diff_pct:.1f}%"
        else:
            diff_str = "N/A"

        print(f"{label:<44} | {cur_str:>12} | {base_str:>14} | {diff_str:>12}")

    row("1. Troca rápida 'next_video' (lazy)", current.lazy_switch_next_ms, baseline.lazy_switch_next_ms if baseline else None, "ms", False)
    row("2. Troca rápida 'prev_video' (lazy)", current.lazy_switch_prev_ms, baseline.lazy_switch_prev_ms if baseline else None, "ms", False)
    row("3. Transição fim de seção (rewind)", current.prev_video_end_total_ms, baseline.prev_video_end_total_ms if baseline else None, "ms", False)
    row("4. Throughput do cache de rewind", current.rewind_cache_fps, baseline.rewind_cache_fps if baseline else None, "fps", True)
    row("5. Latência por frame no rewind", current.rewind_cache_mean_ms, baseline.rewind_cache_mean_ms if baseline else None, "ms", False)
    row("6. Recuperação cauda inválida (probe)", current.tail_probe_resolution_ms, baseline.tail_probe_resolution_ms if baseline else None, "ms", False)
    row("7. Throughput seções esparsas (grab)", current.sparse_throughput_fps, baseline.sparse_throughput_fps if baseline else None, "fps", True)

    print("=" * (88 if baseline else 78) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark de navegação e buffers no aniseek")
    parser.add_argument("--save", type=str, default=None, help="Caminho para gravar JSON com resultados")
    parser.add_argument("--compare", type=str, default=None, help="Caminho do arquivo JSON de baseline para comparação")
    parser.add_argument("--force-gen", action="store_true", help="Força regeração dos vídeos sintéticos de teste")
    args = parser.parse_args()

    data_dir = Path("benchmarks/data")
    results = run_all_benchmarks(data_dir, force_gen=args.force_gen)

    baseline: PlaylistBenchmarkResults | None = None
    if args.compare:
        cmp_file = Path(args.compare)
        if cmp_file.exists():
            with open(cmp_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                baseline = PlaylistBenchmarkResults(**data)
        else:
            print(f"⚠️ Arquivo de baseline '{args.compare}' não encontrado. Exibindo apenas resultado atual.")

    print_report(results, baseline)

    if args.save:
        save_file = Path(args.save)
        save_file.parent.mkdir(parents=True, exist_ok=True)
        with open(save_file, "w", encoding="utf-8") as f:
            json.dump(asdict(results), f, indent=2)
        print(f"💾 Resultados salvos com sucesso em: {save_file}")


if __name__ == "__main__":
    main()
