''' Chat interface tab '''
import logging
from typing import Tuple

import gradio as gr
import numpy as np
from typing_extensions import override

from ui_backends.gradio_backend.components.chat_box import ChatBox
from ui_backends.gradio_backend.components.tts_settings import TtsSettings
from ui_backends.gradio_backend.tab import GradioTab
from utils.tts_queue import TtsQueue

logger = logging.getLogger(__file__)


class ChatTab(GradioTab):
    def __init__(self):
        self._tts_queue: TtsQueue = None

        self._ui_voice_settings: TtsSettings = None
        self._ui_chatbox: ChatBox = None

        self._ui_clear_btn: gr.Button = None

        self._ui_audio_trigger_relay: gr.Checkbox = None
        self._ui_audio_poll_btn: gr.Button = None
        self._ui_streaming_audio: gr.Audio = None
        self._ui_full_audio: gr.Audio = None

        self._ui_avatar_video: gr.Video = None
        self._ui_avatar_button: gr.Button = None

    @override
    def build_ui(self):
        with gr.Box():
            self. _ui_chatbox = ChatBox()

        with gr.Row():
            self._ui_speak_textbox = gr.Textbox(placeholder="Text To Speak", interactive=True)
        with gr.Row():
            self._ui_speak_btn = gr.Button("Speak")
            with gr.Box():
                self._ui_voice_settings = TtsSettings()

        # Hidden helpers for audio chunking
        with gr.Group():
            self._ui_audio_trigger_relay = gr.Checkbox(label="Audio Trigger Relay",
                                                       elem_id="audio_trigger_relay", value=False, visible=True)
            self._ui_audio_poll_btn = gr.Button("Poll For Audio", elem_id="audio_poll_btn", visible=True)
        with gr.Group():
            self._ui_streaming_audio = gr.Audio(elem_id="tts_streaming_audio_player")
            self._ui_full_audio = gr.Audio(label="Final Audio")

        with gr.Group():
            self._ui_avatar_video = gr.Video(label="Avatar", interactive=False)
            self._ui_avatar_button = gr.Button("Generate Video")

        self._ui_speak_btn.click(fn=self._clear_component, inputs=[], outputs=[self._ui_streaming_audio])
        self._ui_speak_btn.click(fn=None, _js="start_listen_for_audio_component_updates")
        self._ui_speak_btn.click(fn=self._handleSpeakButton, inputs=[
                                 self._ui_speak_textbox, self._ui_audio_trigger_relay, self._ui_voice_settings.instance_data], outputs=[self._ui_audio_trigger_relay])

        # Hack:
        # The 'AudioTriggerRelay' disconnects the Speak Button from the Audio Player. If the button output to
        # gr.Audio then the audio component would enter the loading state every time the poll button was clicked.
        # Instead, the AudioTriggerRelay has its change event hooked up to the Audio Player, and the button then
        # has the Relay set as its output. If the button changes the flips the relay state then the audio player will trigger,
        # otherwise if the relay state is unchanged then the audio player will not trigger. This allows the button to trigger
        # the Audio Player withot it being a direct output
        self._ui_audio_trigger_relay.change(fn=self._clear_component, inputs=[], outputs=[self._ui_streaming_audio])
        self._ui_audio_trigger_relay.change(fn=self._handleAudioRelayTriggered, inputs=[], outputs=[
                                            self._ui_streaming_audio, self._ui_full_audio])

    def _clear_component(self, *args, **kwargs):
        logger.info("Clearing component")
        return None

    def _handleAudioRelayTriggered(self, *args, **kwargs):
        ''' Relay a signal to load the AudioPlayer '''
        logger.info("Handle Relay Triggered")
        tries = 2

        while self._tts_queue and tries > 0:
            # Get any new audio since the last call
            new_audio_buffer, sampling_rate = self._tts_queue.get_new_audio()
            if len(new_audio_buffer) > 0:
                new_audio = (sampling_rate, new_audio_buffer)
            else:
                new_audio = None

            if self._tts_queue.is_done():
                all_audio_buffer, sampling_rate = self._tts_queue.get_all_audio()
                all_audio = (sampling_rate, all_audio_buffer)
                self._tts_queue = None
            else:
                all_audio = None

            if new_audio or all_audio:
                return new_audio, all_audio

            logger.warn("No audio available, waiting...")
            if self._tts_queue.wait_for_new_audio(30):
                tries -= 1
                continue
            break

        logger.warning("HandleRelayTrigger called but no audio found!")
        return None, None

    def _handleSpeakButton(self, prompt_text: str, relay_state: bool, tts_instance_data: TtsSettings.StateData) -> Tuple[int, np.array]:
        ''' Kicks off speech synthesis, blocks until first samples arrive '''
        if self._tts_queue:
            logger.warn("Already a TTS queue!")
            return relay_state

        self._tts_queue = TtsQueue()
        self._tts_queue.start_synthesis(prompt_text, tts_instance_data.voice)
        logger.info("Waiting for first samples...")
        success = self._tts_queue.wait_for_audio(timeout=240)

        if success:
            logger.info("First samples received! Triggering audio")
            return not relay_state
        logger.info("No samples received before timeout")
        return relay_state
