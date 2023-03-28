from __future__ import annotations
from ui_backends.gradio_backend.component import GradioComponent
from ui_backends.gradio_backend.components.tts_settings import TtsSettings
from ui_backends.gradio_backend.utils.event_relay import EventRelay
from typing_extensions import override
from typing import Any, Dict, Tuple, List
import gradio as gr
from gradio.components import Component
from PIL import Image

from dataclasses import dataclass
from utils.shared import Shared
from utils.image_utils import ImageUtils
from avatar.profile import Profile
from tts import Tts


class AvatarEditor(GradioComponent):
    @dataclass
    class StateData:
        profile: Profile = None

    def __init__(self):
        self._ui_filename_textbox: gr.Textbox = None
        self._ui_name_textbox: gr.Textbox = None
        self._ui_profile_image: gr.Image = None
        self._ui_voice_settings: TtsSettings = None
        self._relay_update_ui: Component = None
        self._ui_state: gr.State = None

        self._ui_save_btn: gr.Button = None
        self._inputs: List[Component] = []
        self._outputs: List[Component] = []

        self._build_component()

    def _build_component(self):
        with gr.Accordion(label="Avatar Editor"):
            with gr.Row():
                self._ui_filename_textbox = gr.Textbox(interactive=False)
                self._ui_name_textbox = gr.Textbox(placeholder="Avatar Name")
            with gr.Row():
                with gr.Column(scale=1):
                    self._ui_profile_image = gr.Image(label="Profile Image")
                with gr.Column(scale=2):
                    self._ui_voice_settings = TtsSettings()

            with gr.Row():
                self._ui_save_btn = gr.Button("Save")

        self._ui_state = gr.State(value=AvatarEditor.StateData)

        self._inputs = [self._ui_filename_textbox, self._ui_name_textbox, self.ui_profile_image]
        self._outputs = [self._ui_filename_textbox, self._ui_name_textbox, self._ui_profile_image]

        refresh_components = [self._ui_filename_textbox, self._ui_name_textbox,
                              self.ui_profile_image, self._ui_voice_settings.update_ui_relay]
        refresh_inputs = refresh_components + [self._ui_voice_settings.instance_data, self.instance_data]
        refresh_outputs = refresh_components

        self._relay_update_ui = EventRelay.wrap_event(
            func=self._handle_refresh_trigger, inputs=refresh_inputs, outputs=refresh_outputs, name="AvatarEditorWrapped")

        self._ui_save_btn.click(fn=self._handle_save_clicked,
                                inputs=[self._ui_filename_textbox, self._ui_name_textbox,
                                        self._ui_profile_image, self._ui_voice_settings.instance_data, self.instance_data], outputs=[])

    @override
    def add_inputs(self, inputs: List[Component]) -> List[Component]:
        return self._inputs + inputs

    @override
    def consume_inputs(self, inputs: List[Any]) -> Tuple[List[Any], List[Any]]:
        pos = len(self._inputs)
        return (inputs[pos:], inputs[:pos])

    @property
    def update_ui_relay(self) -> Component:
        return self._relay_update_ui

    @property
    def instance_data(self) -> gr.State:
        return self._ui_state

    def _handle_refresh_trigger(self, filename: str, name: str, image, refresh_trigger: bool, tts_state_data: TtsSettings.StateData, editor_state_data):
        tts_state_data.voice = editor_state_data.profile.voice
        # Outputs: name: str, profile: image, voice_refresh_trigger
        return (editor_state_data.profile.name, editor_state_data.profile.friendly_name, editor_state_data.profile.preview_image, not refresh_trigger)

    def _handle_save_clicked(self, filename: str, friendly_name: str, profile_image, voice_state_data: TtsSettings.StateData, editor_state_data: AvatarEditor.StateData):

        editor_state_data.profile.friendly_name = friendly_name
        editor_state_data.profile.preview_image = profile_image
        editor_state_data.profile.voice = voice_state_data.voice
        Shared.getInstance().avatar_manager.save_profile(editor_state_data.profile, overwrite=True)

    @property
    def ui_name_textbox(self) -> gr.Textbox:
        return self._ui_name_textbox

    @property
    def ui_profile_image(self) -> gr.Image:
        return self._ui_profile_image

    @property
    def ui_voice_settings(self) -> TtsSettings:
        return self._ui_voice_settings
