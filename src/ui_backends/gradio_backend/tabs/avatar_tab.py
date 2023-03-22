''' Avatar interface tab '''
import logging
import os
import wave
from tempfile import TemporaryDirectory, NamedTemporaryFile
from typing import List, Tuple
import uuid

from utils.shared import Shared

import gradio as gr
from typing_extensions import override

from avatar.manager import Manager
from ui_backends.gradio_backend.tab import GradioTab

logger = logging.getLogger(__file__)


class AvatarTab(GradioTab):
    PREVIEW_IMAGE_COLUMN_CNT = 8

    def __init__(self, avatar_manager: Manager):
        self._manager: Manager = avatar_manager
        self._ui_refresh_btn: gr.Button = None
        self._ui_avatar_list_gallery: gr.Gallery = None
        self._ui_lip_sync_btn: gr.Button = None
        self._ui_lip_sync_audio: gr.Audio = None
        self._ui_lip_sync_video: gr.Video = None

    @override
    def build_ui(self):
        with gr.Row():
            self._ui_refresh_btn = gr.Button("Refresh")
        with gr.Row():
            self._ui_avatar_list_gallery = gr.Gallery(show_label=False, elem_id="avatar_list_gallery").style(
                grid=AvatarTab.PREVIEW_IMAGE_COLUMN_CNT, preview=False)
        with gr.Row():
            self._ui_lip_sync_btn = gr.Button("Lip Sync")
            self._ui_lip_sync_audio = gr.Audio(label="Lip Sync Audio", elem_id="lip_sync_audio")
        with gr.Row():
            self._ui_lip_sync_video = gr.Video(label="Lip Sync Output", elem_id="lip_sync_video")

        self._ui_refresh_btn.click(fn=self._handle_refresh_clicked, inputs=[], outputs=[self._ui_avatar_list_gallery])
        self._ui_avatar_list_gallery.select(fn=self._handle_avatar_list_selection, inputs=[], outputs=[])

        self._ui_lip_sync_btn.click(fn=self._handle_lip_sync_btn, inputs=[
                                    self._ui_lip_sync_audio], outputs=[self._ui_lip_sync_video])

    def _handle_refresh_clicked(self) -> Tuple[gr.Gallery]:
        ''' Refresh the gallery when the Refresh button is clicked'''
        self._manager.refresh()
        images = [(profile.preview_image, profile.name) for profile in self._manager.list_avatars()]
        return images

    def _handle_avatar_list_selection(self, event_data: gr.SelectData, *args, **kwargs) -> Tuple[None]:
        ''' Handles an avatar being selected from the list gallery '''
        self._manager.active_profile = self._manager.list_avatars()[event_data.index]
        return ()

    def _handle_lip_sync_btn(self, audio_data) -> Tuple[gr.Video]:
        args = Shared.getInstance().args
        unique_id: str = uuid.uuid4().hex
        if isinstance(audio_data, Tuple):
            sampling_rate, audio_buffer = audio_data
            filename: str = os.path.join(args.temp_dir, f"{unique_id}_lipsync.wav")
            with wave.open(filename, 'wb') as wav:
                wav.setframerate(sampling_rate)
                wav.setnchannels(1)
                wav.setsampwidth(2)
                wav.writeframesraw(audio_buffer)
        elif isinstance(audio_data, str):
            filename = audio_data
        else:
            raise Exception("Bad audio file")

        try:
            from avatar.lip_sync import LipSync
            lip_syncer = LipSync(self._manager.active_profile, filename)
            out_filename: str = os.path.join(args.temp_dir, f"{unique_id}_synced_video.mp4")
            lip_syncer.render(output_path=out_filename)
        except Exception as e:
            logger.error(e)
            out_filename = None

        return out_filename
