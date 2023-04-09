''' Chat interface tab '''
import logging
from dataclasses import dataclass
from typing import Tuple

import gradio as gr
from typing_extensions import override

from avatar.manager import Manager, Profile
from ui_backends.gradio_backend.components.chat_box import ChatBox
from ui_backends.gradio_backend.components.tts_settings import TtsSettings
from ui_backends.gradio_backend.components.tts_speaker import TtsSpeaker
from ui_backends.gradio_backend.tab import GradioTab
from ui_backends.gradio_backend.utils.app_data import AppData
from ui_backends.gradio_backend.utils.event_wrapper import EventWrapper
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

    @override
    def build_ui(self):
        self._ui_state = gr.State(value=ChatTab.StateData)

        with gr.Box():
            self. _ui_chatbox = ChatBox()

        with gr.Box(visible=False):
            self._ui_voice_settings = TtsSettings()

        with gr.Row():
            with gr.Column(scale=1):
                self._avatar_gallery = gr.Gallery(label="Select Avatar").style(grid=3)
                refresh_btn = gr.Button("Refresh Avatars")
            with gr.Column(scale=3):
                with gr.Box():
                    self._ui_speaker_name_box = gr.Textbox(
                        label="Selected Avatar", placeholder="No avatar selected", interactive=False)
                    self._tts_speaker = TtsSpeaker(tts_settings=self._ui_voice_settings)

        self._refresh_gallery_relay = EventWrapper.create_wrapper(
            fn=self._handle_refresh, outputs=[self._avatar_gallery])
        refresh_btn.click(**EventWrapper.get_event_args(self._refresh_gallery_relay))

        self._ui_chatbox.chat_response.change(
            fn=lambda x: x, inputs=[self._ui_chatbox.chat_response], outputs=[self._tts_speaker.prompt])

        self._avatar_gallery.select(fn=self._handle_avatar_list_selection,
                                    inputs=[self.instance_data, self._ui_voice_settings.instance_data],
                                    outputs=[self._ui_speaker_name_box])

        AppData.get_instance().app.load(**EventWrapper.get_event_args(self._refresh_gallery_relay))

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
