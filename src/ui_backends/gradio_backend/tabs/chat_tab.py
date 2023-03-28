''' Chat interface tab '''
import logging
from typing import List, Tuple

import gradio as gr
import numpy as np
from typing_extensions import override

from chat import Chat
from tts import Tts
from ui_backends.gradio_backend.tab import GradioTab
from ui_backends.gradio_backend.components.tts_settings import TtsSettings
from utils.tts_queue import TtsQueue
from utils.shared import Shared
from utils.voice_factory import VoiceFactory

logger = logging.getLogger(__file__)


class ChatTab(GradioTab):
    def __init__(self):
        self._tts_queue: TtsQueue = None

        self._ui_chatbot: gr.Chatbot = None
        self._ui_speak_textbox: gr.Textbox = None
        self._ui_speak_btn: gr.Button = None

        self._ui_voice_settings: TtsSettings = None

        self._ui_clear_btn: gr.Button = None

        self._ui_audio_trigger_relay: gr.Checkbox = None
        self._ui_audio_poll_btn: gr.Button = None
        self._ui_streaming_audio: gr.Audio = None
        self._ui_full_audio: gr.Audio = None

        self._ui_avatar_video: gr.Video = None
        self._ui_avatar_button: gr.Button = None

    @override
    def build_ui(self):
        self._ui_chatbot = gr.Chatbot()
        with gr.Row():
            with gr.Column(scale=3):
                txt = gr.Textbox(show_label=False, placeholder="Enter text and press enter").style(container=False)
            with gr.Column(scale=1):
                with gr.Row():
                    submit_btn = gr.Button("Submit")
                    clear_btn = gr.Button("Clear")
        with gr.Row():
            self._ui_speak_textbox = gr.Textbox(placeholder="Text To Speak", interactive=True)
        with gr.Row():
            self._ui_speak_btn = gr.Button("Speak")
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

        # Connect the interface components
        submit_inputs: List[gr.Component] = [txt]
        submit_outputs: List[Any] = [self._ui_chatbot, self._ui_speak_textbox]

        txt.submit(self.submitText, inputs=submit_inputs, outputs=submit_outputs)
        submit_btn.click(self.submitText, inputs=submit_inputs, outputs=submit_outputs)

        clear_btn.click(fn=self._handleClearClick, inputs=[], outputs=[self._ui_chatbot])

        self._ui_speak_btn.click(fn=self._clear_component, inputs=[], outputs=[self._ui_streaming_audio])
        self._ui_speak_btn.click(fn=None, _js="start_listen_for_audio_component_updates")
        # self._ui_speak_btn.click(self._handleSpeakButton,
        #                          inputs=self._ui_voice_settings.add_inputs(
        #                              [self._ui_state, self._ui_speak_textbox, self._ui_audio_trigger_relay]),
        #                          outputs=self._ui_voice_settings.add_outputs([self._ui_audio_trigger_relay]))
        self._ui_speak_btn.click(fn=self._handleSpeakButton, inputs=[self._ui_voice_settings.instance_data, ])

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

    def _handleClearClick(self, *args, **kwargs):
        # TODO: Per-client reset
        Shared.getInstance().chat.reset()
        return [(None, None)]

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

    def _handleSpeakButton(self, *args, **kwargs) -> Tuple[int, np.array]:
        ''' Kicks off speech synthesis, blocks until first samples arrive '''

        args, voice_inputs = self._ui_voice_settings.consume_inputs(args)
        voice = self._ui_voice_settings.create_from_inputs(voice_inputs)
        response_text, relay_state = args

        if self._tts_queue:
            logger.warn("Already a TTS queue!")
            return relay_state

        tts_backend = VoiceFactory.get_backend(voice)
        self._tts_queue = TtsQueue(tts=tts_backend)
        self._tts_queue.start_synthesis(response_text, voice)
        logger.info("Waiting for first samples...")
        success = self._tts_queue.wait_for_audio(timeout=240)

        if success:
            logger.info("First samples received! Triggering audio")
            return not relay_state
        logger.info("No samples received before timeout")
        return relay_state

    def submitText(self, *args, **kwargs) -> Tuple[Tuple[str, str], str]:
        inputText, = args
        response = Shared.getInstance().chat.send_text(inputText)

        history = Shared.getInstance().chat.get_history()
        # Convert to Gradio's (user, ai) format
        chat_output: List[Tuple[str, str]] = []
        for role, response in history:
            msg = f"{role.upper()}: {response}"
            if role == Chat.Roles.AI:
                chat_output.append((None, msg))
            elif role == Chat.Roles.USER:
                chat_output.append((msg, None))
            elif role == Chat.Roles.SYSTEM:
                chat_output.append((msg, None))

        return chat_output, response
