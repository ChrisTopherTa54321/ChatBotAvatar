import gradio as gr
import logging
from .chatgpt import ChatGpt
from .azuretts import AzureTts
from typing import Any, List, Tuple
import uuid
import numpy as np
logger = logging.getLogger(__file__)


class WebUI:
    def __init__(self, chatInterface: ChatGpt, ttsInterface: AzureTts, args):
        self._chat: ChatGpt = chatInterface
        self._tts: AzureTts = ttsInterface
        self._uiChatbot: gr.Chatbot = None
        self._uiState: gr.State = None
        self._uiSpeakText: gr.Textbox = None
        self._uiAudio: gr.Audio = None
        self._uiAutoPlay: gr.Checkbox = None
        self._uiDummyObj: gr.Textbox = None
        self._uiVoicesList: gr.Dropdown = None
        self._uiStylesList: gr.Dropdown = None
        self._pitchText: gr.Textbox = None
        self._rateText: gr.Textbox = None
        self._clearButton: gr.Button = None

    def buildInterface(self):
        with gr.Blocks(analytics_enabled=False) as interface:
            self._uiChatbot = gr.Chatbot()
            self._uiState = gr.State([])
            with gr.Row():
                with gr.Column(scale=4):
                    txt = gr.Textbox(show_label=False, placeholder="Enter text and press enter").style(container=False)
                with gr.Column(scale=1):
                    submit_btn = gr.Button("Submit")
                    clear_btn = gr.Button("Clear")
            with gr.Row():
                self._uiSpeakText = gr.Textbox()
                self._uiAudio = gr.Audio(elem_id="audioplayer", interactive=False)
                self._uiDummyObj = gr.Textbox(visible=False)
            with gr.Row():
                voiceList = self._tts.getVoices()
                self._uiAutoPlay = gr.Checkbox(label="Speak Responses", value=True)
                self._uiVoicesList = gr.Dropdown(label="Voices", multiselect=False, choices=voiceList, value=voiceList[0])
                self._uiStylesList = gr.Dropdown(label="Styles", multiselect=False)
                self._pitchText = gr.Textbox(label="Pitch")
                self._rateText = gr.Textbox(label="Rate")

        submit_inputs: List[gr.Component] = [txt]
        submit_outputs: List[Any] = [self._uiChatbot, self._uiSpeakText]

        txt.submit(self.submitText, inputs=submit_inputs, outputs=submit_outputs)
        submit_btn.click(self.submitText, inputs=submit_inputs, outputs=submit_outputs)

        self._uiSpeakText.change(self.handleSpeakResponse, inputs=[
                                 self._uiSpeakText, self._uiAutoPlay], outputs=[self._uiDummyObj, self._uiAudio])
        self._uiDummyObj.change(self.handleDummyChange, _js="check_for_audio", inputs=[self._uiAudio, self._uiDummyObj], outputs=[self._uiDummyObj])
        self._uiVoicesList.change(self.handleVoiceNameChange, inputs=[self._uiVoicesList], outputs=[self._uiStylesList])
        self._uiStylesList.change(self.handleStyleChange, inputs=[self._uiStylesList])
        self._pitchText.change(lambda x: self._tts.setPitch(x), inputs=[self._pitchText])
        self._rateText.change(lambda x: self._tts.setRate(x), inputs=[self._rateText])
        clear_btn.click(lambda: self._chat.clear(), inputs=[], outputs=[] )

    def handleDummyChange(self, *args, **kwargs):
        audio, dummy = args
        if audio:
            return dummy
        else:
            logger.info("Audio not ready, retrying")
            return WebUI.triggerChangeEvent(),


    def handleVoiceNameChange(self, *args, **kwargs):
        voiceName, = args
        self._tts.setVoice(voiceName)
        styles = self._tts.getStyles()
        return gr.Dropdown.update(choices=styles, interactive=True, value=styles[0])

    def handleStyleChange(self, *args, **kwargs) -> List:
        styleName, = args
        self._tts.setStyle(styleName)
        return []

    def submitText(self, *args, **kwargs) -> Tuple[Tuple[str, str], str]:
        inputText, = args
        response = self._chat.sendText(inputText)
        return self._chat.getHistory(), response

    def handleSpeakResponse(self, *args, **kwargs) -> Tuple[int, np.array]:
        response_text, speak_response = args
        if not speak_response:
            return [None, None]
        audio_data, sample_rate = self._tts.synthesize(response_text)
        return WebUI.triggerChangeEvent(), (sample_rate, audio_data)

    # Taken from AUTOMATIC1111 stable-diffusion-webui

    def injectScripts(self, pathList: List[str]):
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


if __name__ == "__main__":
    demo.launch()
