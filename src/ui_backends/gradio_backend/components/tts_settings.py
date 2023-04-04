from __future__ import annotations
from typing import Any, Dict, List, Tuple

import gradio as gr
from gradio.components import Component
from typing_extensions import override

from tts import Tts
from ui_backends.gradio_backend.component import GradioComponent
from ui_backends.gradio_backend.utils.event_relay import EventRelay
from ui_backends.gradio_backend.utils.app_data import AppData
from utils.voice_factory import VoiceFactory
from dataclasses import dataclass
import logging

logger = logging.getLogger(__file__)


class TtsSettings(GradioComponent):
    @dataclass
    class StateData:
        voice: Tts.Voice = None

    def __init__(self):
        self._ui_voice_dropdown: gr.Dropdown = None
        self._ui_voice_style_dropdown: gr.Dropdown = None
        self._ui_pitch_textbox: gr.Textbox = None
        self._ui_rate_textbox: gr.Textbox = None
        self._ui_state: gr.State = None
        self._relay_update_ui: Component = None

        self._build_component()

    def _build_component(self):
        voice_map = VoiceFactory.get_voices()
        voice_name_list = sorted(voice_map.keys())
        if len(voice_name_list) > 0:
            voice = VoiceFactory.get_voice(voice_name_list[0])
            style_list = voice.get_styles_available()
        else:
            voice = None
            voice_name_list = ["None"]
            style_list = ["None"]

        with gr.Row():
            self._ui_voice_dropdown = gr.Dropdown(label="Voices", multiselect=False,
                                                  choices=voice_name_list, value=voice_name_list[0])
            self._ui_voice_style_dropdown = gr.Dropdown(label="Styles", multiselect=False,
                                                        choices=style_list, value=style_list[0])
        with gr.Row():
            self._ui_pitch_textbox = gr.Textbox(label="Pitch")
            self._ui_rate_textbox = gr.Textbox(label="Rate")

        self._ui_state = gr.State(value=TtsSettings.StateData)

        refresh_outputs = [self._ui_voice_dropdown, self._ui_voice_style_dropdown,
                           self._ui_pitch_textbox, self._ui_rate_textbox]
        refresh_inputs = refresh_outputs + [self.instance_data]

        self._relay_update_ui = EventRelay.create_relay(
            fn=self._handle_refresh_trigger, inputs=refresh_inputs, outputs=refresh_outputs, name="TtsSettingsWrapped")

        self._ui_voice_dropdown.change(self._on_voice_name_change, inputs=[
                                       self._ui_voice_dropdown, self.instance_data], outputs=[self._ui_voice_style_dropdown])
        self._ui_voice_style_dropdown.change(self._on_voice_style_change, inputs=[
                                             self._ui_voice_style_dropdown, self.instance_data], outputs=[])
        self._ui_pitch_textbox.change(self._on_pitch_change, inputs=[
                                      self._ui_pitch_textbox, self.instance_data], outputs=[])
        self._ui_rate_textbox.change(self._on_rate_change, inputs=[
                                     self._ui_rate_textbox, self.instance_data], outputs=[])

        AppData.get_instance().app.load(fn=self._read_current_ui, inputs=refresh_inputs)

    def _handle_refresh_trigger(self, voice_name: str, voice_style: str, voice_pitch: str, voice_rate: str, state_data: TtsSettings.StateData):
        if state_data.voice:
            return (state_data.voice.get_name(), state_data.voice.get_style(), state_data.voice.get_pitch(), state_data.voice.get_rate())
        else:
            return (voice_name, voice_style, voice_pitch, voice_rate)

    @property
    def update_ui_relay(self) -> Component:
        return self._relay_update_ui

    @property
    def instance_data(self) -> gr.State:
        return self._ui_state

    def _read_current_ui(self, voice_name: str, voice_style: str, voice_pitch: str, voice_rate: str, state_data: TtsSettings.StateData) -> None:
        '''
        When triggered, reads the current UI selections in to the state data

        Args:
            voice_name (str): voice name dropdown selection
            voice_style (str): style dropdown selection
            voice_pitch (str): pitch textbox input
            voice_rate (str): rate textbox input
            state_data (TtsSettings.StateData): instance state data
        '''
        voice = VoiceFactory.get_voice(voice_name)
        if voice:
            voice.set_style(voice_style)
            if voice_pitch:
                voice.set_pitch(voice_pitch)
            if voice_rate:
                voice.set_rate(voice_rate)
        state_data.voice = voice

    def _on_voice_name_change(self, voice_name: str, state_data: TtsSettings.StateData) -> Tuple[Dict]:
        ''' Updates the Styles list when the Voice Name changes '''
        if state_data.voice and state_data.voice.get_name() == voice_name:
            logger.info(f"Voice name didn't change: {voice_name}")
            return gr.Dropdown.update(value=state_data.voice.get_style())
        state_data.voice = VoiceFactory.get_voices().get(voice_name, None)
        styles = state_data.voice.get_styles_available()
        return gr.Dropdown.update(choices=styles, interactive=True, value=state_data.voice.get_style())

    def _on_voice_style_change(self, style_name: str, state_data: TtsSettings.StateData) -> None:
        ''' Updates the Styles list when the Voice Name changes '''
        state_data.voice.set_style(style_name)

    def _on_pitch_change(self, pitch: str, state_data: TtsSettings.StateData) -> None:
        ''' Updates the Voice Pitch the textbox changes '''
        state_data.voice.set_pitch(pitch)

    def _on_rate_change(self, rate: str, state_data: TtsSettings.StateData) -> None:
        ''' Updates the Voice Rate when the textbox changes '''
        state_data.voice.set_rate(rate)

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
