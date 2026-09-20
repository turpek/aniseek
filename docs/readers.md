# Documentação dos Leitores de Vídeo (`aniseek`)

O `aniseek` oferece uma arquitetura de leitura de frames de alta performance desacoplada de interfaces gráficas, utilizando buffers concorrentes em segundo plano (`threads`) e saltos rápidos sem sobrecarga de CPU via `cap.grab()` gerenciados pelo `FrameMapper`.

A biblioteca expõe três classes principais de leitores em seu pacote público (`aniseek`):

1. **`ForwardReader`**: Leitor unidirecional otimizado para avanço (`+1`).
2. **`ReverseReader`**: Leitor unidirecional otimizado para retrocesso (`-1`).
3. **`VideoReader`**: Leitor bidirecional cooperativo com duplo buffer e troca de marcha instantânea (`proceed` / `rewind`).

Todas as três classes herdam de **`BaseVideoReader`**, compartilhando a mesma interface uniforme de inicialização, amostragem, protocolo iterador e context manager (`with`).

---

## 1. Construtor e Parâmetros (`BaseVideoReader`)

### Assinatura do Construtor:

```python
BaseVideoReader(
    video: str | Path,
    *,
    start: int | float | str | None = None,
    end: int | float | str | None = None,
    step: int = 1,
    frames: list[int] | None = None,
    buffersize: int = 30,
)
```

### Tabela de Parâmetros:

| Parâmetro | Tipo | Padrão | Descrição |
| :--- | :--- | :--- | :--- |
| `video` | `str \| Path` | *Obrigatório* | Caminho para o arquivo de vídeo. Instancia internamente o `OpenCVVideoSource`. |
| `start` | `int \| float \| str \| None` | `None` (0) | Ponto inicial: aceita índice de frame (`int`), segundos (`float`) ou timestamp (`str` ex: `"01:30"`). Omitir inicia no primeiro frame (`0`). |
| `end` | `int \| float \| str \| None` | `None` (total) | Ponto final limite: aceita índice de frame (`int`), segundos (`float`) ou timestamp (`str` ex: `"02:45"`). Omitir lê até o último frame do vídeo. |
| `step` | `int` | `1` | Intervalo entre frames amostrados (pula intermediários via `cap.grab()`). |
| `frames` | `list[int] \| None` | `None` | Lista explícita e arbitrária de índices de frames a decodificar. Sobrepõe `start`/`end`/`step`. |
| `buffersize` | `int` | `30` | Capacidade máxima da fila em memória para pré-carregamento concorrente. |

> [!TIP]
> **Flexibilidade de Entrada com Determinismo no Core:**
> Se `start` ou `end` forem informados como tempo (`float` em segundos ou `str` como `"MM:SS"` ou `"HH:MM:SS.mmm"`), o construtor utiliza internamente [`resolve_frame_range`](file:///home/gui/python/aniseek/src/aniseek/time_utils.py) para convertê-los automaticamente no índice inteiro exato usando o `fps` do vídeo.
> Todo o pipeline interno, buffers e leitores trabalham estritamente com **números inteiros** (`int`), preservando o determinismo absoluto.

---

### Propriedades e Métodos Disponíveis em Todos os Leitores:

- **`reader.read() -> tuple[bool, ndarray | None]`**: Lê o próximo frame na direção atual. Retorna `(True, frame)` se a decodificação teve sucesso ou `(False, None)` caso a tarefa tenha chegado ao fim ou um frame esteja corrompido.
- **`reader.set_frame(frame_id: int) -> None`**: Reposiciona o cursor de leitura diretamente para o índice de frame numérico indicado.
- **`reader.set_bounds(start: int, end: int) -> None`**: Redefine dinamicamente os limites de fatiamento (`start` e `end`) da leitura ativa.
- **`reader.is_task_complete -> bool`**: **A única verdade do ciclo de vida.** Retorna `True` estritamente quando todos os frames planejados pela amostragem/fatiamento foram consumidos.
- **`reader.frame_id -> int | None`**: Retorna o índice real absoluto do último frame retornado por `read()`.
- **`reader.total_frames -> int`**: Total de frames brutos do vídeo informados pelo container.
- **`reader.fps -> float`**: Taxa de quadros por segundo do vídeo.
- **`len(reader) -> int`**: Quantidade total de frames que serão entregues na amostragem atual.
- **`for ret, frame in reader:`**: Suporte nativo a loop iterador. Itera continuamente até `is_task_complete`.
- **`with ... as reader:`**: Context manager que garante liberação automática de threads e descritores de vídeo via `.close()`.

---

> [!IMPORTANT]
> ### ⚠️ A Regra de Ouro: `is_task_complete` é a única verdade!
> No ecossistema OpenCV, containers de vídeo (como MP4/H.264/HEVC) frequentemente apresentam pequenas falhas de decodificação em frames intermediários ou perto do fim (retornando `None`).
>
> **Nunca utilize `break` ao receber `ret == False` ou `frame is None`!**
> Se você aplicar um `break`, um único frame defeituoso descartará todos os frames subsequentes (causando imagens incompletas em rotinas de costura panorâmica/*stitch* ou interrupções precoces).
>
> **O padrão resiliente:** utilize sempre `is_task_complete` para governar o loop e utilize `continue` caso um frame individual falhe.

---

## 2. `ForwardReader` (Leitura Direta)

O `ForwardReader` utiliza internamente um único buffer concorrente (`VideoBufferRight`) que avança linearmente do primeiro ao último frame especificado. É a escolha ideal quando a tarefa exige apenas processamento sequencial para frente.

### Características:
- **Consumo de Memória:** Baixo (apenas 1 fila de tamanho `buffersize`).
- **Sentido:** Estritamente crescente (`start -> end`).
- **Otimização:** Descarta frames pulados via `cap.grab()` sem decodificação de imagem na CPU/GPU.

### Exemplos de Inicialização do Construtor:

```python
from pathlib import Path
from aniseek import ForwardReader

video = "video.mp4"

# 1. Ler o vídeo inteiro do início ao fim (start e end omitidos):
with ForwardReader(video) as reader:
    for ret, frame in reader:
        if not ret or frame is None:
            continue
        process(frame)

# 2. Fatiamento por Timestamp (strings "MM:SS" ou "HH:MM:SS.mmm"):
with ForwardReader(video, start="01:30", end="02:45.500") as reader:
    for ret, frame in reader:
        if not ret or frame is None:
            continue
        process(frame)

# 3. Fatiamento por Segundos (float) pulando de 2 em 2 frames:
with ForwardReader(video, start=90.0, end=165.5, step=2) as reader:
    for ret, frame in reader:
        if not ret or frame is None:
            continue
        process(frame)

# 4. Fatiamento por Índices de Frames (int) via loop while:
with ForwardReader(video, start=2160, end=3960) as reader:
    while not reader.is_task_complete:
        ret, frame = reader.read()
        if not ret or frame is None:
            continue
        process_frame(reader.frame_id, frame)

# 5. Lista Explícita de Frames Arbitrários:
with ForwardReader(video, frames=[10, 25, 30, 150, 500]) as reader:
    for ret, frame in reader:
        if not ret or frame is None:
            continue
        process_frame(reader.frame_id, frame)
```

---

## 3. `ReverseReader` (Leitura Reversa)

O `ReverseReader` opera com o `VideoBufferLeft`, projetado para decodificar e entregar frames em ordem decrescente. Ele divide a leitura em blocos no sentido inverso e alimenta uma fila de saída em ordem decrescente de forma assíncrona.

### Características:
- **Consumo de Memória:** Baixo (apenas 1 fila de buffer reverso).
- **Sentido:** Estritamente decrescente (`end - 1 -> start`).
- **Casos de Uso:** Análise retrospectiva de eventos, rotulagem do final para o início, buscas reversas.

### Exemplos de Inicialização:

```python
from aniseek import ReverseReader

video = "video.mp4"

# 1. Ler todo o vídeo em ordem decrescente (do último frame até o frame 0):
with ReverseReader(video) as reader:
    for ret, frame in reader:
        if not ret or frame is None:
            continue
        print(f"Frame reverso: {reader.frame_id}")

# 2. Ler trecho específico por tempo ("01:00" até "00:00"):
with ReverseReader(video, start=0, end="01:00") as reader:
    for ret, frame in reader:
        if not ret or frame is None:
            continue
        print(f"Frame reverso: {reader.frame_id}")

# 3. Ler últimos 60 frames por índices inteiros:
with ReverseReader(video, start=940, end=1000) as reader:
    while not reader.is_task_complete:
        ret, frame = reader.read()
        if not ret or frame is None:
            continue
        print(f"Frame lido em ordem reversa: {reader.frame_id}")
```

---

## 4. `VideoReader` (Leitura Bidirecional Cooperativa)

O `VideoReader` mantém dois buffers concorrentes simultâneos (`VideoBufferRight` e `VideoBufferLeft`) operando sob o padrão **Servant / Master**.

### Assinatura do Construtor:

```python
VideoReader(
    video: str | Path | cv2.VideoCapture,
    *,
    start: int | float | str | None = None,
    end: int | float | str | None = None,
    step: int = 1,
    frames: list[int] | None = None,
    direction: Direction | str = Direction.FORWARD,
    buffersize: int = 30,
)
```

### Métodos e Propriedades Exclusivos do `VideoReader`:

- **`reader.direction -> Direction`**: Retorna o sentido de reprodução ativo no momento (`Direction.FORWARD` ou `Direction.REVERSE`).
- **`reader.proceed()`**: Altera o sentido ativo para avanço (`+1`).
- **`reader.rewind()`**: Altera o sentido ativo para retrocesso (`-1`).
- **`reader.is_forward -> bool`**: Retorna `True` se o sentido atual for avanço.
- **`reader.is_reverse -> bool`**: Retorna `True` se o sentido atual for retrocesso.
- **Parâmetro `direction`**: Permite iniciar diretamente em `Direction.FORWARD` (padrão) ou `Direction.REVERSE` (strings `"forward"` e `"reverse"` também são aceitas).

### Exemplo de Uso:

```python
from aniseek import Direction, VideoReader

# Inicia fatiado por tempo em avanço (ou Direction.REVERSE)
with VideoReader("video.mp4", start="00:30", end="02:00", direction=Direction.FORWARD) as reader:
    print(f"Direção inicial: {reader.direction}")  # Direction.FORWARD

    # Avança alguns frames
    for _ in range(50):
        ret, frame = reader.read()
        if not ret or frame is None:
            continue
        print(f"Avançando: frame {reader.frame_id}")

    # Alterna instantaneamente para trás com latência zero
    print("Trocando sentido para REWIND...")
    reader.rewind()
    print(f"Nova direção: {reader.direction}")  # Direction.REVERSE

    # Lê 20 frames para trás (reaproveita cache da memória)
    for _ in range(20):
        ret, frame = reader.read()
        if not ret or frame is None:
            continue
        print(f"Retrocedendo: frame {reader.frame_id}")

    # Retoma avanço
    print("Retomando PROCEED...")
    reader.proceed()
    ret, frame = reader.read()
    print(f"Novo frame em avanço: {reader.frame_id}")
```

---

## 5. Utilitários de Tempo (`aniseek.time_utils`)

Para quem desejar realizar cálculos manuais de conversão fora dos leitores, o submódulo `time_utils` disponibiliza funções puras:

```python
from aniseek.time_utils import (
    resolve_frame_range,
    time_to_frame,
    frame_to_seconds,
    frame_to_timestamp,
    seconds_to_timestamp,
    timestamp_to_seconds,
)

# 1. Normalizar limites (retorna índices inteiros com clamping):
start_fid, end_fid = resolve_frame_range(total_frames=1000, start="01:30", end="02:45", fps=24.0)

# 2. Timestamp para frame:
fid = time_to_frame("01:15.500", fps=24.0)  # -> 1812

# 3. Frame para segundos e timestamp:
secs = frame_to_seconds(1812, fps=24.0)      # -> 75.5
stamp = frame_to_timestamp(1812, fps=24.0)   # -> "00:01:15.500"
```

---

## 6. Tabela Comparativa de Escolha

| Recurso | `ForwardReader` | `ReverseReader` | `VideoReader` |
| :--- | :---: | :---: | :---: |
| **Sentido Suportado** | Apenas Avanço (`+1`) | Apenas Retrocesso (`-1`) | Bidirecional (`+1` e `-1`) |
| **Alternância Dinâmica** | ❌ Não | ❌ Não | ✅ Sim (`proceed()` / `rewind()`) |
| **Buffers Concorrentes** | 1 (`Right`) | 1 (`Left`) | 2 (`Right` + `Left`) |
| **Uso de Memória** | Mínimo | Mínimo | Moderado (~2x `buffersize`) |
| **Fatiamento (`start`/`end`/`step`)** | ✅ Sim (int, float, str) | ✅ Sim (int, float, str) | ✅ Sim (int, float, str) |
| **Vídeo Completo (omitir start/end)**| ✅ Sim | ✅ Sim | ✅ Sim |
| **Lista de Frames Arbitrária** | ✅ Sim | ✅ Sim | ✅ Sim |
| **Indicação `is_task_complete`** | ✅ Sim (Soberano) | ✅ Sim (Soberano) | ✅ Sim (Soberano) |
| **Context Manager (`with`)** | ✅ Sim | ✅ Sim | ✅ Sim |
| **Caso Recomendado** | Pipelines lineares e inferência de IA | Inspeções retrospectivas pontuais | Navegação interativa em UI / Players |
