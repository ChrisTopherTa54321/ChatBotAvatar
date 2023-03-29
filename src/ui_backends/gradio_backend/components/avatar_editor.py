from __future__ import annotations
from ui_backends.gradio_backend.component import GradioComponent
from ui_backends.gradio_backend.components.tts_settings import TtsSettings
from ui_backends.gradio_backend.components.video_gallery import VideoGallery
from ui_backends.gradio_backend.components.image_generator import ImageGenerator
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
from avatar.video_info import VideoInfo
from tts import Tts


class AvatarEditor(GradioComponent):
    @dataclass
    class StateData:
        profile: Profile = None

    def __init__(self, label: str = "Avatar Editor", open: bool = False):
        self._ui_filename_textbox: gr.Textbox = None
        self._ui_name_textbox: gr.Textbox = None
        self._ui_profile_image: gr.Image = None
        self._ui_motion_matched_gallery: VideoGallery = None

        self._ui_create_avail_driving_video_gallery: VideoGallery = None
        self._ui_create_driving_src_imagegen: ImageGenerator = None

        self._ui_voice_settings: TtsSettings = None
        self._relay_update_ui: Component = None
        self._ui_state: gr.State = None

        self._ui_save_btn: gr.Button = None
        self._inputs: List[Component] = []
        self._outputs: List[Component] = []

        self._build_component(label=label, open=open)

    def _build_component(self, label: str, open: bool):
        self._ui_state = gr.State(value=AvatarEditor.StateData)

        with gr.Accordion(label=label, open=open):
            with gr.Row():
                self._ui_filename_textbox = gr.Textbox(interactive=False)
                self._ui_name_textbox = gr.Textbox(placeholder="Avatar Name")
            with gr.Row():
                with gr.Column(scale=1):
                    self._ui_profile_image = gr.Image(label="Profile Image")
                with gr.Column(scale=2):
                    self._ui_voice_settings = TtsSettings()

            with gr.Accordion(label="Motion Matched Videos"):
                with gr.Tab("Existing"):
                    self._ui_motion_matched_gallery = VideoGallery(label="Existing Motion Matched Videos", list_getter=self._get_motion_matched_video, list_getter_inputs=[
                                                                   self.instance_data])
                with gr.Tab("Create New"):
                    gr.Markdown("Select a driving video to motion match to")
                    with gr.Row():
                        with gr.Column(scale=1):
                            self._ui_create_avail_driving_video_gallery = VideoGallery(
                                label="", list_getter=self._get_driving_videos)
                        with gr.Column(scale=1):
                            self._ui_create_driving_src_imagegen = ImageGenerator()

            with gr.Row():
                self._ui_save_btn = gr.Button("Save")

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

        self._ui_create_avail_driving_video_gallery.gallery_component.select(fn=self._handle_driving_video, inputs=[
                                                                             self._ui_create_avail_driving_video_gallery.instance_data], outputs=[self._ui_create_driving_src_imagegen.input_image])

    def _handle_driving_video(seof, gallery_data: VideoGallery.StateData):
        return gallery_data.selected_video.thumbnail

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

    def _get_driving_videos(self, gallery_data: VideoGallery.StateData) -> List[VideoInfo]:
        return Shared.getInstance().avatar_manager.list_driving_videos().copy()

    def _get_motion_matched_video(self, gallery_data: VideoGallery.StateData, editor_data: AvatarEditor.StateData) -> List[VideoInfo]:
        return editor_data.profile.list_motion_matched_videos()

    @property
    def ui_name_textbox(self) -> gr.Textbox:
        return self._ui_name_textbox

    @property
    def ui_profile_image(self) -> gr.Image:
        return self._ui_profile_image

    @property
    def ui_voice_settings(self) -> TtsSettings:
        return self._ui_voice_settings
