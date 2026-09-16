from loguru import logger

from aniseek.manager import VideoManager
from aniseek.playlist import Playlist

fake = {
    'SECTIONS':
    [{'RANGE_FRAME_ID': (0, 1), 'REMOVED_FRAMES': [], 'BLACK_LIST': []},
     {'RANGE_FRAME_ID': (4704, 4901), 'REMOVED_FRAMES': [4750, 4751, 4752, 4753, 4754, 4755], 'BLACK_LIST': []},
     {'RANGE_FRAME_ID': (4902, 5023), 'REMOVED_FRAMES': [], 'BLACK_LIST': []}],
    'REMOVED': []
}


class VideoController:
    def __init__(self,
                 playlist: Playlist,
                 frames_mapping: list[int],
                 video_manager: VideoManager):

        # Abrindo o vídeo e atualizando informaçẽos do vídeo
        self.__player = None
        self.__mapper = None
        self.__trash = None
        self.__section_manager = None
        self.__playlist = playlist

        video_info = playlist.get_video_info()
        self.__open_video(video_manager, video_info)
        self.video_manager = video_manager

    def __open_video(self, video_manager: VideoManager, vinfo) -> None:
        """Método para abrir o vídeo e cofigurar a seção."""
        section_manager = video_manager.open(vinfo.path, vinfo.label, vinfo.format_file)
        video_manager.load_video_info(vinfo)
        player, mapper, trash = video_manager.get()
        self.__player = player
        self.__mapper = mapper
        self.__trash = trash
        self.__section_manager = section_manager

    def __save_section_manager(self):
        video_info = self.__playlist.get_video_info()
        label = video_info.label
        format_file = video_info.format_file
        file_path = video_info.path.with_suffix(format_file)
        self.video_manager.save_section(self.__section_manager, file_path, label)

    def set_pause(self):
        self.__player.set_pause()

    def rewind(self):
        self.__player.rewind()
        self.__player.set_read()

    def proceed(self):
        self.__player.proceed()
        self.__player.set_read()

    def set_quit(self):
        self.__save_section_manager()
        self.__player.set_quit()

    def increase_speed(self):
        self.__player.increase_speed()

    def decrease_speed(self):
        self.__player.decrease_speed()

    def pause_delay(self):
        self.__player.pause_delay()
        self.__player.disable_collect()

    def restore_delay(self):
        self.__player.restore_delay()

    def remove_frame(self):
        if isinstance(self.__player.frame_id, int):
            swap_buffer = self.__player.servant.is_task_complete()

            frame_id, frame = self.__player.remove_frame()
            self.__mapper.remove(frame_id)
            self.__trash.move(frame_id, frame)
            logger.debug(f'removido {frame_id}')

            # O swap do buffer deve ocorrer quando o frame a ser removido estiver em alguma das
            # extremidades (inicio ou final do vídeo) e o buffer estiver na direção da extremidade
            # em questão, pois ao remover tal frame, o servant passa a ficar vazio, e sua task deve,
            # ser iniciada na proxima leitura, onde start_frame == end_frame, que no caso é igual ao
            # primeiro frame_id no buffer master, assim ocorrendo um duplicação de frames.
            if swap_buffer:
                self.__player.swap()
            self.__player.set_read()
        else:
            # Criar um erro personalizado aqui
            ...

    def undo(self):
        if self.__trash.can_undo():
            self.__player.servant._buffer.end_task.set()
            self.__player.servant._buffer.wait_task()
            frame_id, frame = self.__trash.undo()
            logger.error(f'frame {frame_id} restored')
            self.__mapper.add(frame_id)
            self.__player.restore_frame(frame_id, frame)
            self.__player.undo_config()
        else:
            logger.debug('unable to undo removal')

    def next_video(self):
        playlist = self.__playlist
        if not playlist.is_end():
            self.__save_section_manager()
            self.__player.join()
            playlist.next_video()
            self.__open_video(self.video_manager, playlist.get_video_info())
            logger.info(f'next_video: {playlist.video_name()}')
        else:
            logger.debug("it's already at the end of the playlist")

    def prev_video(self):
        playlist = self.__playlist
        if not playlist.is_beginning():
            self.__save_section_manager()
            self.__player.join()
            playlist.prev_video()
            self.__open_video(self.video_manager, playlist.get_video_info())
            logger.info(f'prev_video: {playlist.video_name()}')
        else:
            logger.debug('is already at the beginning of the playlist')

    def split_section(self):
        logger.info('Dividindo a seção')
        frame_id = self.__player.frame_id
        self.__section_manager.split_section(frame_id, self.__trash)
        self.video_manager.create(self.__section_manager)

    def next_section(self):
        logger.info('Proxima seção')
        self.__section_manager.next_section(self.__trash)
        self.video_manager.create(self.__section_manager)

    def prev_section(self):
        logger.info('Seção  anterior')
        self.__section_manager.prev_section(self.__trash)
        self.video_manager.create(self.__section_manager)

    def remove_section(self):
        if self.__section_manager.remove_section(self.__trash):
            self.video_manager.create(self.__section_manager)

    def join_section(self):
        if self.__section_manager.join_section(self.__trash):
            logger.debug('Seções unidas com sucesso!')
            self.video_manager.create(self.__section_manager)
        else:
            logger.debug('Not the previous section to join')

    def undo_section(self):
        if self.__section_manager.restore_section():
            logger.info('Desfazendo.')
            self.video_manager.create(self.__section_manager)
        else:
            logger.info('Não foi possível desfazer.')

    def read(self):
        return self.__player.read()

    def quit(self):
        return self.__player.quit()

    def set_frame(self, frame_id: int):
        self.__player.servant.set(frame_id)
        self.__player.master.set(frame_id)
        # self.__player.servant.run()

    def join(self):
        self.__player.master.join()
        self.__player.servant.join()
        self.__trash.join()

    @property
    def frame_id(self):
        return self.__player.frame_id


class FakeVideoController(VideoController):
    def __init__(self,
                 playlist: Playlist,
                 frames_mapping: list[int],
                 video_manager: VideoManager):
        super().__init__(playlist, frames_mapping, video_manager)

    @property
    def player(self):
        return self._VideoController__player

    @property
    def mapper(self):
        return self._VideoController__mapper

    @property
    def trash(self):
        return self._VideoController__trash
