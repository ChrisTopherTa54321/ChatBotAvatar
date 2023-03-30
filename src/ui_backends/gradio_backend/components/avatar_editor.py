from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

import gradio as gr
from gradio.components import Component
from PIL import Image
from typing_extensions import override

from avatar.profile import Profile
from avatar.video_info import VideoInfo
from tts import Tts
from ui_backends.gradio_backend.component import GradioComponent
from ui_backends.gradio_backend.components.image_generator import \
    ImageGenerator
from ui_backends.gradio_backend.components.motion_matcher import MotionMatcher
from ui_backends.gradio_backend.components.tts_settings import TtsSettings
from ui_backends.gradio_backend.components.video_gallery import VideoGallery
from ui_backends.gradio_backend.utils.event_relay import EventRelay
from utils.image_utils import ImageUtils
from utils.shared import Shared
import shutil


class AvatarEditor(GradioComponent):
    @dataclass
    class StateData:
        profile: Profile = None

    def __init__(self, label: str = "Avatar Editor"):
        self._ui_filename_textbox: gr.Textbox = None
        self._ui_name_textbox: gr.Textbox = None
        self._ui_profile_image: gr.Image = None
        self._ui_motion_matched_gallery: VideoGallery = None

        self._ui_create_avail_driving_video_gallery: VideoGallery = None
        self._ui_create_driving_src_imagegen: ImageGenerator = None

        self._ui_motion_matcher: MotionMatcher = None
        self._ui_out_video_name: gr.Textbox = None
        self._ui_save_video_btn: gr.Button = None

        self._ui_voice_settings: TtsSettings = None
        self._relay_update_ui: Component = None
        self._ui_state: gr.State = None

        self._ui_save_profile: gr.Button = None
        self._inputs: List[Component] = []
        self._outputs: List[Component] = []

        self._build_component(label=label)

    def _build_component(self, label: str):
        self._ui_state = gr.State(value=AvatarEditor.StateData)
        with gr.Box():
            with gr.Row():
                self._ui_filename_textbox = gr.Textbox(label="Profile Name", interactive=False)
                self._ui_name_textbox = gr.Textbox(label="Avatar Name")
            with gr.Row():
                with gr.Column(scale=1):
                    self._ui_profile_image = gr.Image(label="Profile Image")
                with gr.Column(scale=2):
                    self._ui_voice_settings = TtsSettings()

            with gr.Row():
                self._ui_save_profile = gr.Button("Save Profile")

            with gr.Accordion(label="Motion Matched Videos"):
                with gr.Tab("Existing"):
                    self._ui_motion_matched_gallery = VideoGallery(label="Existing Motion Matched Videos", list_getter=self._get_motion_matched_video, list_getter_inputs=[
                        self.instance_data])
                with gr.Tab("Create New"):
                    with gr.Row():
                        with gr.Column(scale=1):
                            with gr.Box():
                                gr.Markdown("Step 1: Select a driving video")
                                self._ui_create_avail_driving_video_gallery = VideoGallery(
                                    label="", list_getter=self._get_driving_videos)
                        with gr.Column(scale=1):
                            with gr.Box():
                                gr.Markdown("Step 2: Generate an image matching the driving video pose")
                                self._ui_create_driving_src_imagegen = ImageGenerator()
                    with gr.Row():
                        with gr.Column(scale=1):
                            with gr.Box():
                                gr.Markdown("Step 3: Generate a motion-matched video using the generated image")
                                self._ui_motion_matcher = MotionMatcher()
                        with gr.Column(scale=1):
                            with gr.Box():
                                gr.Markdown("Step 4: Save the video to the Avatar's profile")
                                self._ui_out_video_name = gr.Textbox(
                                    label="Video Name", placeholder="Name for video within Avatar profile")
                                self._ui_save_video_btn = gr.Button("Save Video")

        self._inputs = [self._ui_filename_textbox, self._ui_name_textbox, self.ui_profile_image]
        self._outputs = [self._ui_filename_textbox, self._ui_name_textbox, self._ui_profile_image]

        refresh_components = [self._ui_filename_textbox, self._ui_name_textbox,
                              self.ui_profile_image, self._ui_voice_settings.update_ui_relay]
        refresh_inputs = refresh_components + [self._ui_voice_settings.instance_data, self.instance_data]
        refresh_outputs = refresh_components

        self._relay_update_ui = EventRelay.wrap_event(
            func=self._handle_refresh_trigger, inputs=refresh_inputs, outputs=refresh_outputs, name="AvatarEditorWrapped")

        self._ui_save_profile.click(fn=self._handle_save_profile_clicked,
                                    inputs=[self._ui_filename_textbox, self._ui_name_textbox,
                                            self._ui_profile_image, self._ui_voice_settings.instance_data, self.instance_data], outputs=[])

        self._ui_save_video_btn.click(fn=self._handle_save_video_clicked, inputs=[
                                      self._ui_motion_matcher.output_video, self._ui_out_video_name, self.instance_data])

        self._ui_create_driving_src_imagegen.output_image.change(
            fn=lambda x: x, inputs=[self._ui_create_driving_src_imagegen.output_image], outputs=[self._ui_motion_matcher.input_image])

        self._ui_create_avail_driving_video_gallery.gallery_component.select(fn=self._handle_driving_vid_select, inputs=[
                                                                             self._ui_create_avail_driving_video_gallery.instance_data], outputs=[self._ui_create_driving_src_imagegen.input_image, self._ui_motion_matcher.input_video, self._ui_out_video_name])

    def _handle_driving_vid_select(seof, gallery_data: VideoGallery.StateData):
        return (gallery_data.selected_video.thumbnail, gallery_data.selected_video.path, os.path.basename(gallery_data.selected_video.path))

    def _handle_save_video_clicked(self, input_video_path: str, output_video_name: str, editor_state_data: AvatarEditor.StateData):
        output_path = os.path.join(editor_state_data.profile.motion_matched_video_directory, output_video_name)
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        shutil.copyfile(input_video_path, output_path)
        editor_state_data.profile.refresh()

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

    def _handle_save_profile_clicked(self, filename: str, friendly_name: str, profile_image, voice_state_data: TtsSettings.StateData, editor_state_data: AvatarEditor.StateData):

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
