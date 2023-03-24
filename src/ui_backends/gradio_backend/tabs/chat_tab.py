''' Chat interface tab '''
import logging
from typing import List, Tuple

import gradio as gr
import numpy as np
from typing_extensions import override

from chat import Chat
from tts import Tts
from ui_backends.gradio_backend.tab import GradioTab
from utils.tts_queue import TtsQueue
from utils.shared import Shared

logger = logging.getLogger(__file__)


class ChatTab(GradioTab):
    def __init__(self, tts_queue: TtsQueue):
        # todo: manage access to these
        self._tts_queue = tts_queue

        self._ui_chatbot: gr.Chatbot = None
        self._ui_state: gr.State = None
        self._ui_speak_textbox: gr.Textbox = None
        self._ui_speak_btn: gr.Button = None
        # self._uiAutoPlay: gr.Checkbox = None
        self._ui_voice_dropdown: gr.Dropdown = None
        self._ui_voice_style_dropdown: gr.Dropdown = None
        self._ui_pitch_textbox: gr.Textbox = None
        self._ui_rate_textbox: gr.Textbox = None
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
        self._ui_state = gr.State({})
        with gr.Row():
            with gr.Column(scale=3):
                txt = gr.Textbox(show_label=False, placeholder="Enter text and press enter").style(container=False)
            with gr.Column(scale=1):
                with gr.Row():
                    submit_btn = gr.Button("Submit")
                    clear_btn = gr.Button("Clear")
        with gr.Row():
            self._ui_speak_textbox = gr.Textbox()
        with gr.Row():
            self._ui_speak_btn = gr.Button("Speak")
            voiceList = Shared.getInstance().tts.get_voice_list()
            voiceNameList = [voice.get_name() for voice in voiceList]
            styleList = voiceList[0].get_styles_available() if len(voiceList) > 0 else []
            # self._uiAutoPlay = gr.Checkbox(label="Speak Responses", value=False)
            self._ui_voice_dropdown = gr.Dropdown(label="Voices", multiselect=False,
                                                  choices=voiceNameList, value=voiceNameList[0])
            self._ui_voice_style_dropdown = gr.Dropdown(label="Styles", multiselect=False,
                                                        choices=styleList, value=styleList[0])
            self._ui_pitch_textbox = gr.Textbox(label="Pitch")
            self._ui_rate_textbox = gr.Textbox(label="Rate")

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
        submit_inputs: List[gr.Component] = [self._ui_state, txt]
        submit_outputs: List[Any] = [self._ui_chatbot, self._ui_speak_textbox]

        txt.submit(self.submitText, inputs=submit_inputs, outputs=submit_outputs)
        submit_btn.click(self.submitText, inputs=submit_inputs, outputs=submit_outputs)

        self._ui_voice_dropdown.change(self._handleVoiceNameChange, inputs=[
            self._ui_state, self._ui_voice_dropdown], outputs=[self._ui_voice_style_dropdown])
        clear_btn.click(fn=self._handleClearClick, inputs=[self._ui_state], outputs=[self._ui_chatbot])

        self._ui_speak_btn.click(fn=self._clear_component, inputs=[], outputs=[self._ui_streaming_audio])
        self._ui_speak_btn.click(fn=None, _js="start_listen_for_audio_component_updates")
        self._ui_speak_btn.click(self._handleSpeakButton,
                                 inputs=[self._ui_state, self._ui_speak_textbox, self._ui_voice_dropdown, self._ui_voice_style_dropdown,
                                         self._ui_pitch_textbox, self._ui_rate_textbox, self._ui_audio_trigger_relay],
                                 outputs=[self._ui_audio_trigger_relay])

        # Hack:
        # The 'AudioTriggerRelay' disconnects the Speak Button from the Audio Player. If the button output to
        # gr.Audio then the audio component would enter the loading state every time the poll button was clicked.
        # Instead, the AudioTriggerRelay has its change event hooked up to the Audio Player, and the button then
        # has the Relay set as its output. If the button changes the flips the relay state then the audio player will trigger,
        # otherwise if the relay state is unchanged then the audio player will not trigger. This allows the button to trigger
        # the Audio Player withot it being a direct output
        self._ui_audio_trigger_relay.change(fn=self._clear_component, inputs=[], outputs=[self._ui_streaming_audio])
        self._ui_audio_trigger_relay.change(fn=self._handleAudioRelayTriggered, inputs=[
            self._ui_state], outputs=[self._ui_streaming_audio, self._ui_full_audio])

    def _clear_component(self, *args, **kwargs):
        logger.info("Clearing component")
        return None

    @override
    def launch(self, listen: bool, port: int):
        ''' Launches the UI and blocks until complete '''
        if self._job_cnt_arg > 1:
            self._app.queue(concurrency_count=self._job_cnt_arg)

        server_name = "0.0.0.0" if listen else None
        self._app.launch(server_name=server_name, server_port=port)

    def _handleClearClick(self, *args, **kwargs):
        # TODO: Per-client reset
        Shared.getInstance().chat.reset()
        return [(None, None)]

    def _handleAudioRelayTriggered(self, *args, **kwargs):
        ''' Relay a signal to load the AudioPlayer '''
        logger.info("Handle Relay Triggered")
        state, = args

        tries = 2

        while tries > 0:
            # Get any new audio since the last call
            new_audio_buffer, sampling_rate = self._tts_queue.get_new_audio()
            if len(new_audio_buffer) > 0:
                new_audio = (sampling_rate, new_audio_buffer)
            else:
                new_audio = None

            if self._tts_queue.is_done():
                all_audio_buffer, sampling_rate = self._tts_queue.get_all_audio()
                all_audio = (sampling_rate, all_audio_buffer)
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
        logger.info("handleSpeakButton pressed")
        state, response_text, voice, style, pitch, rate, relay_state = args
        voice = Shared.getInstance().tts.get_voice(voice)
        voice.set_style(style)
        if pitch:
            voice.set_pitch(pitch)
        if rate:
            voice.set_rate(rate)

        self._tts_queue.start_synthesis(response_text, voice)
        logger.info("Waiting for first samples...")
        success = self._tts_queue.wait_for_audio(timeout=240)

        if success:
            logger.info("First samples received! Triggering audio")
            return not relay_state
        logger.info("No samples received before timeout")
        return relay_state

    def _handleVoiceNameChange(self, *args, **kwargs):
        state, voiceName, = args
        voice = Shared.getInstance().tts.get_voice(voiceName)
        styles = voice.get_styles_available()
        return gr.Dropdown.update(choices=styles, interactive=True, value=styles[0])

    def submitText(self, *args, **kwargs) -> Tuple[Tuple[str, str], str]:
        state, inputText, = args
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
