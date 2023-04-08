from dataclasses import dataclass
from typing import Any, Dict, List, Tuple, Callable
import os

import gradio as gr
from gradio.components import Component
from typing_extensions import override

from ui_backends.gradio_backend.component import GradioComponent
from ui_backends.gradio_backend.utils.event_wrapper import EventWrapper
from ui_backends.gradio_backend.utils.event_relay import EventRelay
from utils.image_utils import ImageUtils
from utils.shared import Shared

from avatar.video_info import VideoInfo


class VideoGallery(GradioComponent):
    @dataclass
    class StateData:
        selected_video: VideoInfo = None
        video_list: List[VideoInfo] = None

    def __init__(self, list_getter: Callable[[StateData], List[VideoInfo]], list_getter_inputs: List[Component] = None, label: str = "Video Gallery"):
        '''
        Initializes a Video Gallery component

        Args:
            list_getter (Callable[[StateData], List[VideoInfo]]): a function to be called to retrieve the list of videos for the gallery to display
            list_getter_inputs (List[Component], optional): additional inputs components to pass to the list_getter function
            label (str, optional): A label for this gallery instance
        '''
        list_getter_inputs = list_getter_inputs or []
        self._ui_image_gallery: gr.Gallery = None
        self._ui_refresh_btn: gr.Button = None
        self._select_event_relay: EventWrapper = None
        self._ui_state: gr.State = None
        self._list_getter: Callable[[VideoGallery.StateData], List[VideoInfo]] = list_getter
        self._list_getter_extra_inputs: List[Component] = list_getter_inputs

        self._component: Component = None
        self._build_component(label=label)

    def _build_component(self, label: str) -> None:
        with gr.Row():
            self._ui_image_gallery = gr.Gallery().style(grid=5)
        with gr.Row():
            self._ui_refresh_btn = gr.Button("Refresh")

        self._ui_state = gr.State(value=VideoGallery.StateData)

        self._select_event_relay = EventWrapper.create_wrapper(fn=None)

        gallery_change_inputs = [self.instance_data] + self._list_getter_extra_inputs
        gallery_change_outputs = [self._ui_image_gallery]
        self._ui_refresh_btn.click(fn=self._handle_refresh_btn, inputs=gallery_change_inputs,
                                   outputs=gallery_change_outputs)
        self._ui_image_gallery.select(fn=self._handle_gallery_selection,
                                      inputs=[self.instance_data, self._select_event_relay],
                                      outputs=[self._select_event_relay])

    def _handle_gallery_selection(self, event_data: gr.SelectData, ui_state: StateData, select_relay: bool) -> EventRelay:
        ''' Handles an avatar being selected from the list gallery '''
        ui_state.selected_video = ui_state.video_list[event_data.index]
        return not select_relay

        assert (os.path.basename(ui_state.selected_video.path) == event_data.value)

    def _handle_refresh_btn(self, ui_state: StateData, *args):
        assert (len(args) == len(self._list_getter_extra_inputs))
        if callable(self._list_getter):
            ui_state.video_list = self._list_getter(ui_state, *args)
        else:
            ui_state.video_list = []

        output = []
        for video in ui_state.video_list:
            output.append((ImageUtils.open_or_blank(video.thumbnail), os.path.basename(video.path)))
        return output

    @property
    def instance_data(self) -> gr.State:
        return self._ui_state

    @property
    def select_event_relay(self) -> Component:
        return self._select_event_relay

    @property
    def gallery_component(self) -> gr.Gallery:
        return self._ui_image_gallery
