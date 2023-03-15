import gradio as gr
import logging
from .chat import Chat
from .tts import Tts
from .tts_queue import TtsQueue
from typing import Any, List, Tuple
from functools import partial
import time
import uuid
import numpy as np
logger = logging.getLogger(__file__)


class WebUI:
    def __init__(self, chatInterface: Chat, ttsInterface: Tts):
        self._app: gr.Blocks = None
        self._chat: Chat = chatInterface
        self._tts: Tts = ttsInterface
        self._tts_queue: TtsQueue = TtsQueue(self._tts)

        self._uiChatbot: gr.Chatbot = None
        self._uiState: gr.State = None
        self._uiSpeakText: gr.Textbox = None
        self._uiSpeakBtn: gr.Button = None
        self._uiPollAudio: gr.Textbox = None
        # self._uiAutoPlay: gr.Checkbox = None
        self._uiVoicesList: gr.Dropdown = None
        self._uiStylesList: gr.Dropdown = None
        self._uiPitchText: gr.Textbox = None
        self._uiRateText: gr.Textbox = None
        self._clearButton: gr.Button = None

        self._uiAudioTriggerRelay: gr.Checkbox = None
        self._uiAudioPollBtn: gr.Button = None
        self._uiAudioPlayer: gr.Audio = None

    def buildInterface(self):
        with gr.Blocks(analytics_enabled=False) as app:
            self._create_interface()
            self._app = app

    def _create_interface(self):
        # Create the interface components
        self._uiChatbot = gr.Chatbot()
        self._uiState = gr.State({})
        with gr.Row():
            with gr.Column(scale=3):
                txt = gr.Textbox(show_label=False, placeholder="Enter text and press enter").style(container=False)
            with gr.Column(scale=1):
                with gr.Row():
                    submit_btn = gr.Button("Submit")
                    clear_btn = gr.Button("Clear")
        with gr.Row():
            self._uiSpeakText = gr.Textbox()
        with gr.Row():
            self._uiSpeakBtn = gr.Button("Speak")
            voiceList = self._tts.get_voice_list()
            voiceNameList = [voice.get_name() for voice in voiceList]
            styleList = voiceList[0].get_styles_available() if len(voiceList) > 0 else []
            # self._uiAutoPlay = gr.Checkbox(label="Speak Responses", value=False)
            self._uiVoicesList = gr.Dropdown(label="Voices", multiselect=False,
                                             choices=voiceNameList, value=voiceNameList[0])
            self._uiStylesList = gr.Dropdown(label="Styles", multiselect=False,
                                             choices=styleList, value=styleList[0])
            self._uiPitchText = gr.Textbox(label="Pitch")
            self._uiRateText = gr.Textbox(label="Rate")

        with gr.Group():
            self._uiAudioTriggerRelay = gr.Checkbox(label="Audio Trigger Relay",
                                                    elem_id="audio_trigger_relay", value=False)
            self._uiAudioPollBtn = gr.Button("Poll For Audio", elem_id="audio_poll_btn")
            self._uiAudioPlayer = gr.Audio(elem_id="tts_streaming_audio_player")

        # Connect the interface components
        submit_inputs: List[gr.Component] = [self._uiState, txt]
        submit_outputs: List[Any] = [self._uiChatbot, self._uiSpeakText]

        txt.submit(self.submitText, inputs=submit_inputs, outputs=submit_outputs)
        submit_btn.click(self.submitText, inputs=submit_inputs, outputs=submit_outputs)

        self._uiVoicesList.change(self._handleVoiceNameChange, inputs=[
            self._uiState, self._uiVoicesList], outputs=[self._uiStylesList])
        clear_btn.click(lambda state: self._chat.clear(), inputs=[self._uiState], outputs=[])

        self._uiSpeakBtn.click(fn=self._clear_component, inputs=[], outputs=[self._uiAudioPlayer])
        self._uiSpeakBtn.click(fn=None, _js="start_listen_for_audio_component_updates")
        self._uiSpeakBtn.click(self._handleSpeakButton,
                               inputs=[self._uiState, self._uiSpeakText, self._uiVoicesList, self._uiStylesList,
                                       self._uiPitchText, self._uiRateText, self._uiAudioTriggerRelay],
                               outputs=[self._uiAudioTriggerRelay])

        # Hack:
        # The 'AudioTriggerRelay' disconnects the Poll Button from the Audio Player. If the Poll Button output to
        # gr.Audio then the audio component would enter the loading state every time the poll button was clicked.
        # Instead, the AudioTriggerRelay has its change event hooked up to the Audio Player, and the Poll Button
        # has the Relay set as its output. If the Poll Button changes the Relay state then the audio player will trigger,
        # otherwise if the Relay state is unchanged then the audio player will not trigger. So Poll Button can trigger
        # the Audio Player withot it being a direct output
        self._uiAudioTriggerRelay.change(fn=self._handleAudioRelayTriggered, inputs=[
            self._uiState], outputs=[self._uiAudioPlayer])

    def _clear_component(self, *args, **kwargs):
        logger.info("Clearing component")
        return None

    def run(self, listen: bool, port: int, jobs: int):
        ''' Launches the UI and blocks until complete '''
        if jobs > 1:
            self._app.queue(concurrency_count=jobs)

        server_name = "0.0.0.0" if listen else None
        self._app.launch(server_name=server_name, server_port=port)

    def _handleAudioRelayTriggered(self, *args, **kwargs):
        ''' Relay a signal to load the AudioPlayer '''
        logger.info("Handle Relay Triggered")
        state, = args

        # Get any new audio since the last call
        audio_buffer, sampling_rate = self._tts_queue.get_new_audio()
        if len(audio_buffer > 0):
            return (sampling_rate, audio_buffer)

        # No new audio, maybe all audio is done?
        if self._tts_queue.is_done():
            logger.info("TTS queue is done! Return full audio clip")
            audio_buffer, smapling_rate = self._tts_queue.get_all_audio()
            if len(audio_buffer) > 0:
                return (sampling_rate, audio_buffer)

        logger.warning("HandleRelayTrigger called but no audio found!")
        return None

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
        retries = 100
        logger.info("Waiting for first samples...")
        while retries > 0 and not self._tts_queue.has_audio():
            logger.info(f"Waiting for first sample... {retries}")
            time.sleep(0.1)
            retries -= 1
        if retries > 0:
            logger.info("First samples received! Triggering audio")
            return not relay_state
        logger.info("No samples received before timeout")
        return relay_state

    def _handleVoiceNameChange(self, *args, **kwargs):
        state, voiceName, = args
        voice = self._tts.get_voice(voiceName)
        styles = voice.get_styles_available() if styles else [""]
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

    def injectScripts(self, pathList: List[str]):
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
