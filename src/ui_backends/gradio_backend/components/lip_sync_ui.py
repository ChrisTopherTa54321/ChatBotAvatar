import logging
import os
import tempfile
import uuid
import wave
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

import gradio as gr
import numpy as np
from gradio.components import Component

from ui_backends.gradio_backend.component import GradioComponent
from ui_backends.gradio_backend.utils.event_relay import EventRelay
from ui_backends.gradio_backend.utils.event_wrapper import EventWrapper
from ui_backends.gradio_backend.utils.helpers import persist_file_event
from utils.shared import Shared

logger = logging.getLogger(__file__)


class LipSyncUi(GradioComponent):
    @dataclass
    class StateData:
        pass

    def __init__(self):
        self._ui_submit_btn: gr.Button = None
        self._ui_input_video: gr.Video = None
        self._ui_input_audio_player: gr.Audio = None
        self._ui_input_audio_file: gr.File = None
        self._ui_output_video: gr.Video = None
        self._ui_update_player_relay: Component = None
        self._ui_state: gr.State = None

        self._build_component()

    def _build_component(self):
        with gr.Row():
            self._ui_input_video = gr.Video(label="Lip Sync Input")
            with gr.Column():
                self._ui_input_audio_player = gr.Audio(label="Audio Preview", interactive=False)
                self._ui_input_audio_file = gr.File(label="Audio File")
        with gr.Row():
            self._ui_submit_btn = gr.Button("Run Lip Sync", variant="primary")
            self._ui_output_video = gr.Video(label="Lip Sync Output")

        lipsync_wrapper = EventWrapper.create_wrapper(fn=self._handle_lip_sync_clicked,
                                                      inputs=[self._ui_input_audio_file, self._ui_input_video],
                                                      outputs=[self._ui_output_video],
                                                      pre_fn=lambda: (gr.Button.update(
                                                          interactive=False, variant="secondary")),
                                                      pre_outputs=[self._ui_submit_btn],
                                                      post_fn=lambda: (gr.Button.update(
                                                          interactive=True, variant="primary")),
                                                      post_outputs=[self._ui_submit_btn])

        self._ui_update_player_relay = EventWrapper.create_wrapper(lambda x: [persist_file_event(x)],
                                                                   inputs=[self._ui_input_audio_file], outputs=[self._ui_input_audio_player])

        self._ui_submit_btn.click(**EventWrapper.get_event_args(lipsync_wrapper))

        self._ui_input_audio_file.change(**EventWrapper.get_event_args(self._ui_update_player_relay))

    def _handle_lip_sync_clicked(self, audio_path: tempfile.NamedTemporaryFile, image_or_video_path: str) -> Tuple[str]:
        '''
        Handles the Lip Sync button press. Runs Wav2Lip on the inputs

        Args:
            audio_data (Tuple[int, np.array]): audio data to use
            image_or_video_path (str): path to image or video to apply lips to

        Returns:
            Tuple[str]: path to output video
        '''

        args = Shared.getInstance().args
        unique_id: str = uuid.uuid4().hex
        try:
            from avatar.lip_sync import LipSync
            out_filename: str = os.path.join(args.temp_dir, f"{unique_id}_synced_video.mp4")
            LipSync.render(image_or_video_path, audio_path.name, out_filename)
        except Exception as e:
            logger.error(e)
            out_filename = None
        return out_filename

    @property
    def instance_data(self) -> gr.State:
        return self._ui_state

    @property
    def refresh_preview_relay(self) -> Component:
        return self._ui_update_player_relay

    @property
    def input_video(self) -> gr.Video:
        return self._ui_input_video

    @property
    def input_audio_file(self) -> gr.File:
        return self._ui_input_audio_file

    @property
    def output_video(self) -> gr.Video:
        return self._ui_output_video
