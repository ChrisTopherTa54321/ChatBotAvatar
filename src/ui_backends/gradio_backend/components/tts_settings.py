from ui_backends.gradio_backend.component import GradioComponent
from typing_extensions import override
from typing import Any, Dict, Tuple, List
import gradio as gr
from gradio.components import Component

from utils.shared import Shared
from tts import Tts


class TtsSettings(GradioComponent):
    def __init__(self):
        self._ui_voice_dropdown: gr.Dropdown = None
        self._ui_voice_style_dropdown: gr.Dropdown = None
        self._ui_pitch_textbox: gr.Textbox = None
        self._ui_rate_textbox: gr.Textbox = None
        self._component: Component = None
        self._inputs: List[Component] = []

    @override
    def build_component(self) -> Component:
        voice_list = Shared.getInstance().tts.get_voice_list()
        voice_name_list = [voice.get_name() for voice in voice_list]
        style_list = voice_list[0].get_styles_available() if len(voice_list) > 0 else []
        with gr.Accordion(label="Voice Settings") as component:
            with gr.Row():
                self._ui_voice_dropdown = gr.Dropdown(label="Voices", multiselect=False,
                                                      choices=voice_name_list, value=voice_name_list[0])
                self._ui_voice_style_dropdown = gr.Dropdown(label="Styles", multiselect=False,
                                                            choices=style_list, value=style_list[0])
            with gr.Row():
                self._ui_pitch_textbox = gr.Textbox(label="Pitch")
                self._ui_rate_textbox = gr.Textbox(label="Rate")
        self._component = component
        self._ui_voice_dropdown.change(self._on_voice_name_change, inputs=[
                                       self._ui_voice_dropdown], outputs=[self._ui_voice_style_dropdown])

        self._inputs = [self._ui_voice_dropdown, self._ui_voice_style_dropdown,
                        self._ui_pitch_textbox, self._ui_rate_textbox]
        return self._component

    @override
    def add_inputs(self, inputs: List[Component]) -> List[Component]:
        return self._inputs + inputs

    @override
    def consume_inputs(self, inputs: List[Any]) -> Tuple[List[Any], List[Any]]:
        pos = len(self._inputs)
        return (inputs[pos:], inputs[:pos])

    def create_from_inputs(self, inputs: List[Any]) -> Tts.Voice:
        ''' Given inputs from consume_inputs, return a configured voice'''
        voice_name, voice_style, voice_pitch, voice_rate = inputs
        voice = Shared.getInstance().tts.get_voice(voice_name)
        voice.set_style(voice_style)
        if voice_pitch:
            voice.set_pitch(voice_pitch)
        if voice_rate:
            voice.set_rate(voice_rate)
        return voice

    def _on_voice_name_change(self, voice_name: str) -> Tuple[Dict]:
        ''' Updates the Styles list when the Voice Name changes '''
        voice = Shared.getInstance().tts.get_voice(voice_name)
        styles = voice.get_styles_available()
        return gr.Dropdown.update(choices=styles, interactive=True, value=styles[0])

    @property
    def component(self) -> Component:
        return self._component

    @property
    def ui_voice_list(self) -> gr.Dropdown:
        return self._ui_voice_dropdown

    @property
    def ui_voice_style_list(self) -> gr.Dropdown:
        return self._ui_voice_style_dropdown

    @property
    def ui_pitch_textbox(self) -> gr.Textbox:
        return self._ui_pitch_textbox

    @property
    def ui_rate_textbox(self) -> gr.Textbox:
        return self._ui_rate_textbox
