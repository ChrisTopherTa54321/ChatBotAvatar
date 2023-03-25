from ui_backends.gradio_backend.component import GradioComponent
from typing_extensions import override
from typing import Any, Dict, Tuple, List
import gradio as gr
from gradio.components import Component

from utils.shared import Shared
from utils.voice_factory import VoiceFactory
from tts import Tts


class TtsSettings(GradioComponent):
    def __init__(self):
        self._ui_voice_dropdown: gr.Dropdown = None
        self._ui_voice_style_dropdown: gr.Dropdown = None
        self._ui_pitch_textbox: gr.Textbox = None
        self._ui_rate_textbox: gr.Textbox = None
        self._ui_update_trigger: gr.Checkbox = None
        self._voice: Tts.Voice = None
        self._component: Component = None
        self._inputs: List[Component] = []
        self._outputs: List[Component] = []

    @override
    def build_component(self) -> Component:
        voice_map = VoiceFactory.get_voices()
        voice_name_list = sorted(voice_map.keys())
        if len(voice_name_list) > 0:
            voice = VoiceFactory.get_voice(voice_name_list[0])
        else:
            voice = None

        style_list = voice.get_styles_available() if voice else []

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

        self._ui_update_trigger = gr.Checkbox(value=False, visible=False)

        self._inputs = [self._ui_voice_dropdown, self._ui_voice_style_dropdown,
                        self._ui_pitch_textbox, self._ui_rate_textbox, self._ui_update_trigger]
        self._outputs = self._inputs.copy()

        self._ui_update_trigger.change(fn=self._handle_update_trigger, inputs=self._inputs, outputs=self._inputs)
        return self._component

    # TODO: Standardize these triggers better. Pretty sure there is a bug here with update
    def _handle_update_trigger(self, *args, **kwargs):
        voice_name, voice_style, pitch, rate, update = args
        if not self.voice:
            self.voice = self.create_from_inputs(args)
        return (self.voice.get_name(), self.voice.get_style(), self.voice.get_pitch(), self.voice.get_rate(), update)

    @override
    def add_inputs(self, inputs: List[Component]) -> List[Component]:
        return self._inputs + inputs

    @override
    def consume_inputs(self, inputs: List[Any]) -> Tuple[List[Any], List[Any]]:
        pos = len(self._inputs)
        inputs, consumed_inputs = (inputs[pos:], inputs[:pos])

        return (inputs, consumed_inputs)

    def get_update_trigger(self) -> Component:
        return self._ui_update_trigger

    def create_from_inputs(self, inputs: List[Any]) -> Tts.Voice:
        ''' Given inputs from consume_inputs, return a configured voice'''
        voice_name, voice_style, voice_pitch, voice_rate, _ = inputs
        voice = VoiceFactory.get_voice(voice_name)
        voice.set_style(voice_style)
        if voice_pitch:
            voice.set_pitch(voice_pitch)
        if voice_rate:
            voice.set_rate(voice_rate)
        return voice

    def create_output_from_voice(self, voice: Tts.Voice) -> List[Any]:
        # name, style, pitch, rate, update_trigger
        pass

    def _on_voice_name_change(self, voice_name: str) -> Tuple[Dict]:
        ''' Updates the Styles list when the Voice Name changes '''
        self._voice = VoiceFactory.get_voices().get(voice_name, None)
        styles = self._voice.get_styles_available()
        return gr.Dropdown.update(choices=styles, interactive=True, value=styles[0])

    @property
    def voice(self) -> Tts.Voice:
        return self._voice

    @voice.setter
    def voice(self, new_voice: Tts.Voice):
        self._voice = new_voice

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
