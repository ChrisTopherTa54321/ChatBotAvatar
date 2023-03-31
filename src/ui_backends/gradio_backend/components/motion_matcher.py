import os
import uuid
from dataclasses import dataclass
from tempfile import TemporaryDirectory
from typing import Any, Dict, List

import gradio as gr
import numpy as np
from gradio.components import Component

from avatar.motion_match import MotionMatch
from ui_backends.gradio_backend.component import GradioComponent
from utils.image_utils import ImageUtils
from utils.shared import Shared


class MotionMatcher(GradioComponent):
    class Filenames:
        IMAGE_IN = "input_image.png"
        OUTPUT_VID = "motion_matched.mp4"

    @dataclass
    class StateData:
        pass

    def __init__(self):
        self._ui_image_in: gr.Image = None
        self._ui_video_in: gr.Video = None
        self._ui_video_out: gr.Video = None
        self._ui_generate_btn: gr.Button = None
        self._ui_state: gr.State = None

        self._build_component()

    def _build_component(self):
        with gr.Row():
            self._ui_image_in = gr.Image(label="Input Image", interactive=True).style(height=256, width=256)
            self._ui_video_in = gr.Video(label="Input Video", interactive=True).style(height=256, width=256)
        with gr.Row():
            self._ui_generate_btn = gr.Button("Generate Output")
            self._ui_video_out = gr.Video(label="Output Video", interactive=False).style(height=256, width=256)

        self._ui_generate_btn.click(fn=self._handle_generate_click, inputs=[
                                    self._ui_image_in, self._ui_video_in], outputs=[self._ui_video_out])

    def _handle_generate_click(self, image_in: np.ndarray, video_path_in: str) -> None:
        # Must save image_in to filesystem
        tmpdir = Shared.getInstance().args.temp_dir
        unique_id: str = uuid.uuid4().hex
        image_filename = os.path.join(tmpdir, f"{unique_id}_{MotionMatcher.Filenames.IMAGE_IN}")
        output_video_filename = os.path.join(tmpdir, f"{unique_id}_{MotionMatcher.Filenames.OUTPUT_VID}")
        ImageUtils.copy_or_save(image=image_in, output_path=image_filename)
        MotionMatch.render(source_image=image_filename, driving_video=video_path_in, output_path=output_video_filename)
        return output_video_filename

    @ property
    def input_image(self) -> gr.Image:
        return self._ui_image_in

    @ property
    def input_video(self) -> gr.Video:
        return self._ui_video_in

    @ property
    def output_video(self) -> gr.Video:
        return self._ui_video_out

    @ property
    def instance_data(self) -> gr.State:
        return self._ui_state
