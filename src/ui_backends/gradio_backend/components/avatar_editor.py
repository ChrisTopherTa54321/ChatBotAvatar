from ui_backends.gradio_backend.component import GradioComponent
from ui_backends.gradio_backend.components.tts_settings import TtsSettings
from typing_extensions import override
from typing import Any, Dict, Tuple, List
import gradio as gr
from gradio.components import Component
from PIL import Image

from utils.shared import Shared
from utils.image_utils import ImageUtils
from avatar.profile import Profile
from tts import Tts


class AvatarEditor(GradioComponent):
    def __init__(self):
        self._ui_filename_textbox: gr.Textbox = None
        self._ui_name_textbox: gr.Textbox = None
        self._ui_profile_image: gr.Image = None
        self._ui_voice_settings: TtsSettings = None
        self._ui_update_trigger: gr.Checkbox = None
        self._ui_save_btn: gr.Button = None
        self._component: Component = None
        self._inputs: List[Component] = []
        self._outputs: List[Component] = []
        self._profile: Profile = None

    @override
    def build_component(self) -> Component:
        with gr.Accordion(label="Avatar Editor") as component:
            with gr.Row():
                self._ui_filename_textbox = gr.Textbox(interactive=False)
                self._ui_name_textbox = gr.Textbox(placeholder="Avatar Name")
            with gr.Row():
                with gr.Column(scale=1):
                    self._ui_profile_image = gr.Image(label="Profile Image")
                with gr.Column(scale=2):
                    self._ui_voice_settings = TtsSettings()
                    self._ui_voice_settings.build_component()

            with gr.Row():
                self._ui_save_btn = gr.Button("Save")

        self._profile_fields = [self._ui_filename_textbox, self._ui_name_textbox, self.ui_profile_image]
        self._outputs = [self._ui_filename_textbox, self._ui_name_textbox,
                         self._ui_profile_image, self._ui_voice_settings.get_update_trigger()]

        self._ui_update_trigger = gr.Checkbox(value=False, label="Update Trigger", visible=False)

        self._ui_update_trigger.change(fn=self._handle_update_trigger, inputs=self._outputs, outputs=self._outputs)

        self._ui_save_btn.click(fn=self._handle_save_clicked,
                                inputs=self._ui_voice_settings.add_inputs(self._profile_fields), outputs=[])

        self._component = component
        return self._component

    @override
    def add_inputs(self, inputs: List[Component]) -> List[Component]:
        return self._inputs + inputs

    @override
    def consume_inputs(self, inputs: List[Any]) -> Tuple[List[Any], List[Any]]:
        pos = len(self._inputs)
        return (inputs[pos:], inputs[:pos])

    def get_update_trigger(self) -> Component:
        return self._ui_update_trigger

    def _handle_update_trigger(self, *args, **kwargs):
        orig_filename, orig_name, orig_image, orig_updater = args
        self._ui_voice_settings.voice = self._profile.voice
        # Outputs: name: str, profile: image, voice_settings_updater
        image = ImageUtils.open_or_blank(self._profile.preview_image_path)
        return (self._profile.directory, self._profile.name, image, not orig_updater)

    def _handle_save_clicked(self, *args, **kwargs):
        args, consumed_inputs = self._ui_voice_settings.consume_inputs(args)
        voice = self._ui_voice_settings.create_from_inputs(consumed_inputs)
        directory, name, profile_image = args

        profile = Profile(profile_dir=directory, name=name)
        profile.voice = voice
        profile.preview_image = profile_image
        Shared.getInstance().avatar_manager.save(profile)

    def load_profile(self, profile: Profile):
        ''' Fills in the AvatarEditor settings from a Profile '''
        self._profile = profile

    @property
    def component(self) -> Component:
        return self._component

    @property
    def ui_name_textbox(self) -> gr.Textbox:
        return self._ui_name_textbox

    @property
    def ui_profile_image(self) -> gr.Image:
        return self._ui_profile_image

    @property
    def ui_voice_settings(self) -> TtsSettings:
        return self._ui_voice_settings
