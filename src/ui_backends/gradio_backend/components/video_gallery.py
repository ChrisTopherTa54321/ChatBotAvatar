from dataclasses import dataclass
from typing import Any, Dict, List, Tuple
import os

import gradio as gr
from gradio.components import Component
from typing_extensions import override

from ui_backends.gradio_backend.component import GradioComponent
from utils.image_utils import ImageUtils
from utils.shared import Shared

from avatar.video_info import VideoInfo


class VideoGallery(GradioComponent):
    @dataclass
    class StateData:
        selected_video: VideoInfo = None
        video_list: List[VideoInfo] = None

    def __init__(self):
        self._ui_image_gallery: gr.Gallery = None
        self._ui_refresh_btn: gr.Button = None
        self._ui_create_preview: gr.Button = None
        self._ui_state: gr.State = None

        self._component: Component = None
        self._build_component()

    def _build_component(self) -> None:
        with gr.Accordion(label="Video Gallery"):
            with gr.Row():
                self._ui_image_gallery = gr.Gallery().style(grid=5)
            with gr.Row():
                self._ui_refresh_btn = gr.Button("Refresh")
                self._ui_create_preview = gr.Button("Create Preview")

        self._ui_state = gr.State(value=VideoGallery.StateData)

        # preview.click and refresh_btn.click must have the same input/output list
        gallery_change_inputs = [self.instance_data]
        gallery_change_outputs = [self._ui_image_gallery]
        self._ui_create_preview.click(fn=self._handle_create_preview_btn,
                                      inputs=gallery_change_inputs, outputs=gallery_change_outputs)
        self._ui_refresh_btn.click(fn=self._handle_refresh_btn, inputs=gallery_change_inputs,
                                   outputs=gallery_change_outputs)
        self._ui_image_gallery.select(fn=self._handle_gallery_selection, inputs=[
                                      self.instance_data], outputs=[])

    def _handle_gallery_selection(self, event_data: gr.SelectData, ui_state: StateData) -> None:
        ''' Handles an avatar being selected from the list gallery '''
        ui_state.selected_video = ui_state.video_list[event_data.index]

        assert (os.path.basename(ui_state.selected_video.path) == event_data.value)

    def _handle_refresh_btn(self, ui_state: StateData):
        manager = Shared.getInstance().avatar_manager
        ui_state.video_list = manager.list_driving_videos().copy()
        output = []
        for video in ui_state.video_list:
            output.append((ImageUtils.open_or_blank(video.thumbnail), os.path.basename(video.path)))
        return output

    def _handle_create_preview_btn(self, ui_state: StateData):
        ui_state.selected_video.refresh_thumbnail()
        return self._handle_refresh_btn(ui_state)

    @property
    def instance_data(self) -> gr.State:
        return self._ui_state
