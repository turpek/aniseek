from pathlib import Path

from pytest import fixture, raises

from aniseek.custom_exceptions import PlaylistError
from aniseek.editing.playlist import Playlist


@fixture
def play():
    videos = [Path(f'video-{x}.mp4') for x in range(1, 7)]
    playlist = Playlist(videos)
    yield playlist


def test_Playlist_com_lista_de_videos_vazia():
    videos = []
    expect = 'the video list is empty'
    with raises(PlaylistError) as excinfo:
        Playlist(videos)

    result = str(excinfo.value)
    assert expect == result


def test_video_name_com_1_video_na_lista():
    videos = [Path('video-1.mp4')]
    expect = videos[0]
    play = Playlist(videos)
    result = play.video_name()
    assert expect == result

# ################# Testes para o método `next_video`


def test_next_video_1x_com_lista_de_tamanho_1():
    videos = [Path('video-1.mp4')]
    expect = videos[0]

    play = Playlist(videos)
    play.next_video()
    result = play.video_name()

    assert expect == result


def test_next_video_1x_com_lista_de_tamanho_6(play):
    expect = Path('video-2.mp4')
    play.next_video()

    result = play.video_name()
    assert expect == result


def test_next_video_5x_com_lista_de_tamanho_6(play):
    expect = Path('video-6.mp4')

    [play.next_video() for _ in range(5)]
    result = play.video_name()
    assert expect == result


# ################# Testes para o método `prev_video`

def test_prev_video_1x_com_lista_de_tamanho_1():
    videos = [Path('video-1.mp4')]
    expect = videos[0]

    play = Playlist(videos)
    play.prev_video()
    result = play.video_name()
    assert expect == result


def test_prev_video_1x_com_lista_de_tamanho_6(play):
    expect = Path('video-1.mp4')

    # É necessario passar 1 vídeo para a frente para voltar
    play.next_video()
    play.prev_video()

    result = play.video_name()
    assert expect == result


def test_prev_video_5x_com_lista_de_tamanho_6(play):
    expect = Path('video-1.mp4')

    # É necessario passar 5x para a frente para voltar 5x
    [play.next_video() for _ in range(5)]
    [play.prev_video() for _ in range(5)]

    result = play.video_name()
    assert expect == result
