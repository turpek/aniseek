# aniseek

**aniseek** é um motor inteligente para busca, navegação e leitura precisa frame a frame de vídeos, desenvolvido em Python. Diferente de um player convencional, o aniseek é focado na manipulação e extração temporal de frames, permitindo avanço e retrocesso instantâneos via buffers concorrentes.

Sua arquitetura é baseada em um sistema de duplo buffer (`VideoBufferLeft` e `VideoBufferRight`), que permite uma navegação eficiente tanto para frente (`proceed`) quanto para trás (`rewind`).

## ✨ Funcionalidades Principais

- **Navegação Frame a Frame:** Controle total sobre a reprodução, com a capacidade de avançar e retroceder quadro a quadro instantaneamente.
- **Gerenciamento de Seções:** Divida o vídeo em múltiplas seções, permitindo operações como:
  - **Dividir (`Split`):** Crie uma nova seção a partir do frame atual.
  - **Juntar (`Join`):** Mescle a seção atual com a anterior.
  - **Remover:** Exclua seções inteiras do vídeo.
  - **Navegar entre seções:** Salte diretamente para o início ou fim de seções.
- **Edição Não-Destrutiva:**
  - **Remoção de Frames:** Marque frames para serem removidos sem excluí-los do arquivo original.
  - **Lixeira (`Trash`):** Um sistema de lixeira que armazena os frames removidos e permite restaurá-los (`undo`).
- **Controle de Velocidade:** Acelere ou desacelere a velocidade de reprodução em tempo real.
- **Suporte a Playlist:** Carregue e navegue por uma lista sequencial de vídeos.
- **Persistência de Edições:** Salva o estado das seções e frames removidos em um arquivo sidecar `.json` associado ao vídeo.

## 🛠️ Tecnologias Utilizadas

- [Python 3.12+](https://www.python.org/)
- [OpenCV (`opencv-python`)](https://pypi.org/project/opencv-python/): Para decodificação e exibição dos frames de vídeo.
- [pynput](https://pypi.org/project/pynput/): Para captura precisa de modificadores de teclado (`Ctrl`, `Shift`, `Alt`) via hooks do SO.
- [NumPy](https://numpy.org/): Para manipulação de arrays de frames.
- [Loguru](https://github.com/Delgan/loguru): Para logging estruturado.
- [uv](https://github.com/astral-sh/uv): Gerenciamento moderno de pacotes e ambientes Python.

## 🚀 Instalação e Execução

**1. Clone o repositório:** 

```bash
git clone https://github.com/turpek/aniseek.git
cd aniseek
```

**2. Instale as dependências via `uv` (recomendado):**

```bash
uv sync
```

*Ou utilizando pip convencional:*

```bash
python -m venv .venv
source .venv/bin/activate  # No Windows: .venv\Scripts\activate
pip install -e .
```

**3. Exemplo de uso básico:**

```python
from aniseek.editing.playlist import Playlist
from aniseek.view import VideoCon

if __name__ == '__main__':
    video_path = "caminho/para/seu/video.mp4"
    playlist = Playlist([video_path])

    with VideoCon(playlist) as video:
        while not video.quit():
            ret, frame = video.read()
            video.show(ret, frame)
```

Execute o script com:

```bash
uv run python main.py
```

## ⌨️ Comandos e Atalhos

O sistema de atalhos adota uma separação categórica entre operações de **Frames/Reprodução** (teclas soltas) e operações de **Seções** (com tecla modificadora `Ctrl` via `pynput` por padrão, ou `Shift`/Maiúsculas no fallback OpenCV):

### 1. Reprodução e Controle de Frames (Sem modificador)

| Tecla | Ação | Descrição |
| :---: | :--- | :--- |
| **`d`** | **Proceed** | Avança frame a frame em direção normal (+1). |
| **`a`** | **Rewind** | Recua frame a frame em direção reversa (-1). |
| **`espaço`** | **Pause/Play (Delay)** | Pausa ativa para edição (delay=0) ou retoma à velocidade atual. |
| **`b`** | **Pause/Play (Toggle)** | Pausa ou retoma a reprodução contínua. |
| **`x`** | **Remover Frame** | Remove o frame atual e envia para a lixeira (`Trash`). |
| **`u`** | **Desfazer Frame** | Restaura o último frame removido da lixeira. |
| **`[`** | **Diminuir Velocidade** | Aumenta o delay entre frames exibidos. |
| **`]`** | **Aumentar Velocidade** | Diminui o delay entre frames exibidos. |
| **`=`** | **Restaurar Velocidade** | Restaura a velocidade padrão de reprodução. |
| **`n`** | **Próximo Vídeo** | Avança para o próximo vídeo da playlist. |
| **`p`** | **Vídeo Anterior** | Retorna para o vídeo anterior da playlist. |
| **`q`** | **Sair** | Encerra o player e persiste as seções no arquivo `.json`. |

### 2. Gerenciamento de Seções (Com Modificador)

| Operação | Padrão (`pynput`) | Fallback (`cv2`) | Descrição |
| :--- | :---: | :---: | :--- |
| **Próxima Seção** | **`Ctrl + d`** | `Shift + d` / `D` | Salta para a próxima seção do vídeo. |
| **Seção Anterior** | **`Ctrl + a`** | `Shift + a` / `A` | Salta para a seção anterior do vídeo. |
| **Dividir Seção** | **`Ctrl + s`** | `Shift + s` / `S` | Divide a seção no frame atual (**S**plit). |
| **Juntar Seção** | **`Ctrl + j`** | `Shift + j` / `J` | Une a seção atual com a anterior (**J**oin). |
| **Remover Seção** | **`Ctrl + x`** | `Shift + x` / `X` | Remove a seção inteira atual. |
| **Desfazer Seção** | **`Ctrl + u`** | `Shift + u` / `U` | Desfaz a última alteração de seção (**U**ndo). |

---

## 💡 Conceitos Fundamentais

- **`VideoReader` / Duplo Buffer:** Leitores paralelos concorrentes (`VideoBufferRight` e `VideoBufferLeft`) operando cooperativamente em memória (`servant` e `master`), garantindo troca de sentido instantânea sem lag de decodificação.
- **`FrameMapper`:** Estrutura otimizada em C (`array('l')`) que indexa os IDs válidos de frames com busca binária rápida (`bisect`) e alterna dinamicamente entre decodificação pesada (`read()`) e pulo leve de cabeçalho (`grab()`).
- **`SectionManager`:** Gerencia o ciclo de vida das seções temporais do vídeo e sua persistência automática em disco.
- **`Trash` & Memento:** Padrão arquitetural que preserva o histórico de edições e descartes para restauração a qualquer momento.
- **`InputHandler` / `PynputKeyReader`:** Motor desacoplado de leitura de teclado com suporte a modificadores em nível de sistema operacional, eliminando limitações de backends gráficos.
