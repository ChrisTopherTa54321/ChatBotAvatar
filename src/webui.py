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

    def buildInterface(self):
        with gr.Blocks(analytics_enabled=False) as interface:
            self._uiChatbot = gr.Chatbot()
            self._uiState = gr.State([])
            with gr.Row():
                with gr.Column(scale=4):
                    txt = gr.Textbox(show_label=False, placeholder="Enter text and press enter").style(container=False)
                with gr.Column(scale=1):
                    submit_btn = gr.Button("Submit")
                    self._uiAutoPlay = gr.Checkbox(label="Speak Responses", value=True)
            with gr.Row():
                self._uiSpeakText = gr.Textbox()
                self._uiAudio = gr.Audio(elem_id="audioplayer", interactive=False)

        submit_inputs: List[gr.Component] = [txt]
        submit_outputs: List[Any] = [self._uiChatbot, self._uiSpeakText]

        txt.submit(self.submitText, inputs=submit_inputs, outputs=submit_outputs)
        submit_btn.click(self.submitText, inputs=submit_inputs, outputs=submit_outputs)

        self._uiSpeakText.change(self.handleSpeakResponse, inputs=[
                                 self._uiSpeakText, self._uiAutoPlay], outputs=[self._uiAudio])

    def submitText(self, *args, **kwargs) -> Tuple[Tuple[str, str], str]:
        inputText, = args
        response = self._chat.sendText(inputText)
        return self._chat.getHistory(), response

    def handleSpeakResponse(self, *args, **kwargs) -> Tuple[int, np.array]:
        response_text, speak_response = args
        if not speak_response:
            return [None, None]
        audio_data, sample_rate = self._tts.synthesize(response_text)
        return (sample_rate, audio_data)

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
