''' Chat interface tab '''
import logging

import gradio as gr
from typing_extensions import override

from ui_backends.gradio_backend.components.chat_box import ChatBox
from ui_backends.gradio_backend.components.tts_settings import TtsSettings
from ui_backends.gradio_backend.components.tts_speaker import TtsSpeaker
from ui_backends.gradio_backend.tab import GradioTab

logger = logging.getLogger(__file__)


class ChatTab(GradioTab):
    def __init__(self):
        self._ui_voice_settings: TtsSettings = None
        self._ui_chatbox: ChatBox = None
        self._tts_speaker: TtsSpeaker = None

    @override
    def build_ui(self):
        with gr.Box():
            self. _ui_chatbox = ChatBox()

        with gr.Row():
            with gr.Box():
                self._ui_voice_settings = TtsSettings()
            with gr.Box():
                self._tts_speaker = TtsSpeaker(tts_settings=self._ui_voice_settings)

        self._ui_chatbox.chat_response.change(fn=lambda x:x, inputs=[self._ui_chatbox.chat_response], outputs=[self._tts_speaker.prompt] )
