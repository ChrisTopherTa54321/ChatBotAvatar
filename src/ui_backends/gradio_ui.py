import gradio as gr
import logging
from chat import Chat
from tts import Tts
from ui import Ui
from utils.tts_queue import TtsQueue
from typing import Any, List, Tuple
from typing_extensions import override
from functools import partial
import time
import uuid
import numpy as np
import glob
import os
logger = logging.getLogger(__file__)

gradio_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), "gradio")


class GradioUi(Ui):
    def __init__(self, chat_interface: Chat, tts_interface: Tts, jobs: int = 3):
        self._app: gr.Blocks = None
        self._chat: Chat = chat_interface
        self._tts: Tts = tts_interface
        self._tts_queue: TtsQueue = TtsQueue(self._tts)

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
        self._job_cnt_arg = jobs

        self._buildInterface()
        self._injectScripts(glob.glob(os.path.join(gradio_dir, "js", "*.js")))

    def _buildInterface(self):
        with gr.Blocks(analytics_enabled=False) as app:
            self._create_interface()
            self._app = app

    def _create_interface(self):
        # Create the interface components
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
            voiceList = self._tts.get_voice_list()
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
                                                       elem_id="audio_trigger_relay", value=False, visible=False)
            self._ui_audio_poll_btn = gr.Button("Poll For Audio", elem_id="audio_poll_btn", visible=False)
        with gr.Group():
            self._ui_streaming_audio = gr.Audio(elem_id="tts_streaming_audio_player")
            self._ui_full_audio = gr.Audio(label="Final Audio")

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
        self._chat.clear()
        return []

    def _handleAudioRelayTriggered(self, *args, **kwargs):
        ''' Relay a signal to load the AudioPlayer '''
        logger.info("Handle Relay Triggered")
        state, = args

        # Get any new audio since the last call
        audio_buffer, sampling_rate = self._tts_queue.get_new_audio()
        if len(audio_buffer > 0):
            return (sampling_rate, audio_buffer), None

        # No new audio, maybe all audio is done?
        if self._tts_queue.is_done():
            logger.info("TTS queue is done! Return full audio clip")
            audio_buffer, sampling_rate = self._tts_queue.get_all_audio()
            if len(audio_buffer) > 0:
                return None, (sampling_rate, audio_buffer)

        logger.warn("No audio available, waiting...")
        if self._tts_queue.wait_for_new_audio(30):
            audio_buffer, sampling_rate = self._tts_queue.get_new_audio()
            if len(audio_buffer > 0):
                return (sampling_rate, audio_buffer), None

        logger.warning("HandleRelayTrigger called but no audio found!")
        return None, None

    def _handleSpeakButton(self, *args, **kwargs) -> Tuple[int, np.array]:
        ''' Kicks off speech synthesis, blocks until first samples arrive '''
        logger.info("handleSpeakButton pressed")
        state, response_text, voice, style, pitch, rate, relay_state = args
        voice = self._tts.get_voice(voice)
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
        voice = self._tts.get_voice(voiceName)
        styles = voice.get_styles_available()
        return gr.Dropdown.update(choices=styles, interactive=True, value=styles[0])

    def submitText(self, *args, **kwargs) -> Tuple[Tuple[str, str], str]:
        state, inputText, = args
        response = self._chat.send_text(inputText)

        history = self._chat.get_history()
        # Convert to Gradio's (user, ai) format
        chat_output: List[Tuple[str, str]] = []
        for role, response in history:
            msg = f"{role.upper()}: {response}"
            if role == Chat.Roles.AI:
                chat_output.append((None, msg))
            elif role == Chat.Roles.USER:
                chat_output.append((msg, None))
            elif role == Chat.Roles.SYSTEM:
                if False:
                    chat_output.append((msg, None))

        return chat_output, response

    def _injectScripts(self, pathList: List[str]):
        # Taken from AUTOMATIC1111 stable-diffusion-webui
        contents: str = ""
        for script in pathList:
            with open(script, "r", encoding="utf8") as file:
                contents += file.read()

        import gradio.routes

        def template_response(*args, **kwargs):
            res = gradio_routes_templates_response(*args, **kwargs)
            res.body = res.body.replace(b'</head>', f'<script>{contents}</script></head>'.encode("utf8"))
            res.init_headers()
            return res

        gradio_routes_templates_response = gradio.routes.templates.TemplateResponse
        gradio.routes.templates.TemplateResponse = template_response

    @ classmethod
    def triggerChangeEvent(cls) -> str:
        return uuid.uuid4().hex
