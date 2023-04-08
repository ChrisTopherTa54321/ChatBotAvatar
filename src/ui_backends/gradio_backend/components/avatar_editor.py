from __future__ import annotations

import logging
import os
import shutil
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
from ui_backends.gradio_backend.components.controlnet_settings import \
    ControlNetSettings
from ui_backends.gradio_backend.components.image_generator import \
    ImageGenerator
from ui_backends.gradio_backend.components.motion_matcher import MotionMatcher
from ui_backends.gradio_backend.components.tts_settings import TtsSettings
from ui_backends.gradio_backend.components.video_gallery import VideoGallery
from ui_backends.gradio_backend.utils.app_data import AppData
from ui_backends.gradio_backend.utils.event_relay import EventRelay
from ui_backends.gradio_backend.utils.event_wrapper import EventWrapper
from utils.image_gen_factory import ImageGenFactory
from utils.shared import Shared

logger = logging.getLogger(__file__)


class AvatarEditor(GradioComponent):
    @dataclass
    class StateData:
        profile: Profile = None

    def __init__(self, label: str = "Avatar Editor"):
        self._ui_filename_textbox: gr.Textbox = None
        self._ui_name_textbox: gr.Textbox = None
        self._ui_profile_image: gr.Image = None
        self._ui_motion_matched_gallery: VideoGallery = None

        self._ui_new_driving_vid_gallery: VideoGallery = None
        self._ui_new_driving_src_imagegen: ImageGenerator = None

        self._ui_motion_matcher: MotionMatcher = None
        self._ui_out_video_name: gr.Textbox = None
        self._ui_save_video_btn: gr.Button = None

        self._ui_voice_settings: TtsSettings = None
        self._relay_update_ui: Component = None
        self._ui_state: gr.State = None

        self._ui_save_profile: gr.Button = None

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
                with gr.Tab("Create New"):
                    with gr.Row():
                        with gr.Column(scale=1):
                            with gr.Box():
                                gr.Markdown("Step 1: Select a driving video")
                                self._ui_new_driving_vid_gallery = VideoGallery(
                                    label="", list_getter=self._get_driving_videos)
                        with gr.Column(scale=1):
                            with gr.Box():
                                gr.Markdown("Step 2: Generate an image matching the driving video pose")
                                self._ui_new_driving_src_imagegen = ImageGenerator()
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
                with gr.Tab("Existing"):
                    self._ui_motion_matched_gallery = VideoGallery(label="Existing Motion Matched Videos", list_getter=self._get_motion_matched_video, list_getter_inputs=[
                        self.instance_data])

        refresh_components = [self._ui_filename_textbox, self._ui_name_textbox,
                              self.ui_profile_image, self._ui_voice_settings.update_ui_relay]
        refresh_inputs = refresh_components + [self._ui_voice_settings.instance_data, self.instance_data]
        refresh_outputs = refresh_components

        self._relay_update_ui = EventWrapper.create_wrapper(
            fn=self._handle_refresh_trigger, inputs=refresh_inputs, outputs=refresh_outputs, name="AvatarEditorWrapped")

        self._ui_save_profile.click(fn=self._handle_save_profile_clicked,
                                    inputs=[self._ui_filename_textbox, self._ui_name_textbox,
                                            self._ui_profile_image, self._ui_voice_settings.instance_data, self.instance_data], outputs=[])

        self._ui_save_video_btn.click(fn=self._handle_save_video_clicked, inputs=[
                                      self._ui_motion_matcher.output_video, self._ui_out_video_name, self.instance_data])

        self._ui_new_driving_src_imagegen.output_image.change(
            fn=lambda x: x, inputs=[self._ui_new_driving_src_imagegen.output_image], outputs=[self._ui_motion_matcher.input_image])

        controlnet_settings = self._ui_new_driving_src_imagegen.controlnet_settings
        self._ui_new_driving_vid_gallery.select_event_relay.change(fn=self._handle_driving_vid_select,
                                                                   inputs=[self._ui_new_driving_vid_gallery.instance_data,
                                                                           controlnet_settings.instance_data, self._ui_new_driving_src_imagegen.restore_state_relay],
                                                                   outputs=[self._ui_new_driving_src_imagegen.input_image, self._ui_motion_matcher.input_video, self._ui_out_video_name,
                                                                            self._ui_new_driving_src_imagegen.restore_state_relay])

        # Schedule filling in defaults at client run. Use two relays, because for some reason Gradio is passing a different controlnet_settings.instance_data the first
        # call so just let the first relay consume the incorrect data and trigger the real call
        set_defaults_relay2: EventWrapper = EventWrapper.create_wrapper(fn=self._set_controlnet_defaults,
                                                                        inputs=[controlnet_settings.instance_data],
                                                                        post_fn=lambda x: not x,
                                                                        post_inputs=[
                                                                            self._ui_new_driving_src_imagegen.restore_state_relay],
                                                                        post_outputs=[self._ui_new_driving_src_imagegen.restore_state_relay])

        # # the load event if any of the 'settings' instance data is in its input list
        set_defaults_relay: EventWrapper = EventWrapper.create_wrapper(fn=self._set_controlnet_defaults,
                                                                       inputs=[controlnet_settings.instance_data],
                                                                       post_fn=lambda x, y: (not x, not y),
                                                                       post_inputs=[
                                                                           self._ui_new_driving_src_imagegen.restore_state_relay, set_defaults_relay2],
                                                                       post_outputs=[self._ui_new_driving_src_imagegen.restore_state_relay, set_defaults_relay2])

        AppData.get_instance().app.load(fn=lambda x: not x, inputs=[set_defaults_relay], outputs=[set_defaults_relay])

    def _set_controlnet_defaults(self, controlnet_data: ControlNetSettings.StateData):
        @dataclass
        class ControlNetDefault:
            model: str
            module: str
            params: Dict[str, Any]

        wanted_defaults: List[ControlNetDefault] = [
            ControlNetDefault(model="normal", module="normal_map", params={"weight": 0.4}),
            ControlNetDefault(model="depth", module="depth", params={"weight": 0.4}),
        ]
        image_gen_factory = ImageGenFactory.get_default_image_gen()
        models = image_gen_factory.get_controlnet_models()
        modules = image_gen_factory.get_controlnet_modules()

        item_idx: int = 0
        for idx, default in enumerate(wanted_defaults):
            if default.module and default.module not in modules:
                logger.warning(f"Default ControlNet module [{default.module}] not found")
                continue

            model_results = [x for x in models if default.model in x]
            if len(model_results) == 0:
                logger.warning(f"Default ControlNet model [{default.model}] not found")
                continue
            if len(model_results) > 1:
                logger.warning(f"Ambiguous default model [{default.model}], available. Could be: [{model_results}]")

            full_model_name = model_results[0]

            # Ensure there are enough controlnet units for the defaults
            if item_idx > len(controlnet_data.controlnet_items) - 1:
                controlnet_data.add_empty_unit()

            default_settings = {"model": full_model_name, "module": default.module}
            default_settings.update(default.params)

            item = controlnet_data.controlnet_items[item_idx]
            item.enabled = True
            item.func_params_state.init_args.update(default_settings)
            item_idx += 1

        return

    def _handle_driving_vid_select(self, gallery_data: VideoGallery.StateData, controlnet_data: ControlNetSettings.StateData, imggen_restore_relay: bool) -> [gr.Image, gr.Video, gr.Textbox, EventRelay]:
        for unit in controlnet_data.controlnet_items:
            unit.func_params_state.init_args["input_image"] = gallery_data.selected_video.thumbnail

        return (gallery_data.selected_video.thumbnail, gallery_data.selected_video.path, os.path.basename(gallery_data.selected_video.path), not imggen_restore_relay)

    def _handle_save_video_clicked(self, input_video_path: str, output_video_name: str, editor_state_data: AvatarEditor.StateData):
        output_path = os.path.join(editor_state_data.profile.motion_matched_video_directory, output_video_name)
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        shutil.copyfile(input_video_path, output_path)
        editor_state_data.profile.refresh()

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
