''' Chat interface tab '''
import logging
from dataclasses import dataclass
from typing import Tuple, List
import numpy as np
import gradio as gr
import random
from typing_extensions import override
from functools import partial

from avatar.manager import Manager, Profile
from ui_backends.gradio_backend.components.chat_box import ChatBox
from ui_backends.gradio_backend.components.tts_settings import TtsSettings
from ui_backends.gradio_backend.components.tts_speaker import TtsSpeaker
from ui_backends.gradio_backend.tab import GradioTab
from ui_backends.gradio_backend.utils.app_data import AppData
from ui_backends.gradio_backend.utils.event_wrapper import EventWrapper
from ui_backends.gradio_backend.components.lip_sync_ui import LipSyncUi
from ui_backends.gradio_backend.utils.helpers import audio_to_file_event
from utils.shared import Shared

logger = logging.getLogger(__file__)


class ChatTab(GradioTab):
    @dataclass
    class StateData:
        profile: Profile = None

    def __init__(self):
        self._ui_voice_settings: TtsSettings = None
        self._ui_chatbox: ChatBox = None
        self._tts_speaker: TtsSpeaker = None
        self._avatar_gallery: gr.Gallery = None
        self._refresh_gallery_relay: EventWrapper = None
        self._ui_state: gr.State = None
        self._ui_speaker_name_box: gr.Textbox = None
        self._ui_video: gr.Video = None
        self._lip_sync_ui: LipSyncUi = None

    @override
    def build_ui(self):
        self._ui_state = gr.State(value=ChatTab.StateData)

        gen_lipsync_label: str = "Generate Video From Last Speech"

        with gr.Box():
            self. _ui_chatbox = ChatBox()

        with gr.Box(visible=False):
            self._ui_voice_settings = TtsSettings()
            self._lip_sync_ui = LipSyncUi()

        with gr.Row():
            with gr.Column(scale=1):
                self._avatar_gallery = gr.Gallery(label="Select Avatar").style(grid=3)
                refresh_btn = gr.Button("Refresh Avatars")
            with gr.Column(scale=3):
                with gr.Box():
                    self._ui_speaker_name_box = gr.Textbox(
                        label="Selected Avatar", placeholder="No avatar selected", interactive=False)
                    self._tts_speaker = TtsSpeaker(tts_settings=self._ui_voice_settings)
            with gr.Column(scale=1):
                self._ui_video = gr.Video()
                gen_video_btn = gr.Button(gen_lipsync_label)

        self._refresh_gallery_relay = EventWrapper.create_wrapper(
            fn=self._handle_refresh, outputs=[self._avatar_gallery])
        refresh_btn.click(**EventWrapper.get_event_args(self._refresh_gallery_relay))

        def set_lipsync_buttons_state(enable: bool):
            if enable:
                msg = gen_lipsync_label
            else:
                msg = "Generating Video..."
            return [gr.Button.update(interactive=enable, value=msg)]

        sync_lipsync_relay = EventWrapper.create_wrapper_list(
            wrapped_func_list=[
                EventWrapper.WrappedFunc(fn=partial(set_lipsync_buttons_state, False), outputs=[gen_video_btn]),
                EventWrapper.WrappedFunc(fn=self._run_lipsync,
                                         inputs=[self.instance_data, self._tts_speaker.output_audio],
                                         outputs=[self._lip_sync_ui.input_audio_file, self._lip_sync_ui.input_video]),
                EventWrapper.WrappedFunc(**EventWrapper.get_event_args(self._lip_sync_ui.run_lipsync_relay))
            ],
            error_func=EventWrapper.WrappedFunc(fn=partial(set_lipsync_buttons_state, True), outputs=[gen_video_btn]),
        )

        self._lip_sync_ui.job_done_event.change(
            fn=lambda x: (x, gr.Button.update(value=gen_lipsync_label, interactive=True)), inputs=[self._lip_sync_ui.output_video], outputs=[self._ui_video, gen_video_btn])

        gen_video_btn.click(**EventWrapper.get_event_args(sync_lipsync_relay))

        self._ui_chatbox.chat_response.change(
            fn=lambda x: x, inputs=[self._ui_chatbox.chat_response], outputs=[self._tts_speaker.prompt])

        self._avatar_gallery.select(fn=self._handle_avatar_list_selection,
                                    inputs=[self.instance_data, self._ui_voice_settings.instance_data],
                                    outputs=[self._ui_speaker_name_box])

        AppData.get_instance().app.load(**EventWrapper.get_event_args(self._refresh_gallery_relay))

    def _run_lipsync(self, inst_data: StateData, audio_data: Tuple[int, np.ndarray]) -> Tuple[gr.Audio, gr.Video]:
        audio_filename: str = audio_to_file_event(audio_data)
        motion_videos = inst_data.profile._get_matched_videos()
        if len(motion_videos) > 0:
            video_path = random.choice(motion_videos).path
        else:
            video_path = None
        return (audio_filename, video_path)

    def _handle_gen_video(self, inst_data: StateData, audio, *args):
        pass

    def _handle_refresh(self) -> Tuple[gr.Gallery]:
        ''' Refresh the gallery '''
        manager: Manager = Shared.getInstance().avatar_manager
        manager.refresh()

        images = [(profile.preview_image, profile.friendly_name)
                  for profile in manager.list_avatars()]
        return [images]

    def _handle_avatar_list_selection(self, event_data: gr.SelectData, inst_data: StateData, tts_data: TtsSettings.StateData) -> Tuple[None]:
        ''' Handles an avatar being selected from the list gallery '''
        manager: Manager = Shared.getInstance().avatar_manager
        inst_data.profile: Profile = manager.list_avatars()[event_data.index]
        tts_data.voice = inst_data.profile.voice
        return inst_data.profile.friendly_name

    @property
    def instance_data(self) -> gr.State:
        return self._ui_state
