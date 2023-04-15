import logging
import os
import tempfile
import uuid
import wave
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

import gradio as gr
import numpy as np
from functools import partial
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
        self._run_lipsync_relay: EventWrapper = None
        self._job_done_relay: EventWrapper = None

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

        def set_buttons_state(enable: bool):
            if enable:
                return [gr.Button.update(interactive=True, variant="primary")]
            else:
                return [gr.Button.update(interactive=False, variant="secondary")]

        self._job_done_relay = EventWrapper.create_wrapper_list(
                wrapped_func_list=[
                    EventWrapper.WrappedFunc(fn=partial(set_buttons_state, True), outputs=[self._ui_submit_btn])
                    ])

        self._run_lipsync_relay = EventWrapper.create_wrapper_list(
            wrapped_func_list=[
                EventWrapper.WrappedFunc(fn=partial(set_buttons_state, False), outputs=[self._ui_submit_btn]),
                EventWrapper.WrappedFunc(fn=self._handle_lip_sync_clicked,
                                         inputs=[self._ui_input_audio_file, self._ui_input_video],
                                         outputs=[self._ui_output_video])
            ],
            finally_func=EventWrapper.WrappedFunc(**EventWrapper.get_event_args(self._job_done_relay))
        )

        self._ui_update_player_relay = EventWrapper.create_wrapper(lambda x: [persist_file_event(x)],
                                                                   inputs=[self._ui_input_audio_file], outputs=[self._ui_input_audio_player])


        self._ui_submit_btn.click(**EventWrapper.get_event_args(self._run_lipsync_relay))

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

        from avatar.lip_sync import LipSync
        out_filename: str = os.path.join(args.temp_dir, f"{unique_id}_synced_video.mp4")
        try:
            LipSync.render(image_or_video_path, audio_path.name, out_filename)
        except Exception as e:
            raise gr.Error("LipSync error. Is FFMPEG installed?")

        return out_filename

    @property
    def instance_data(self) -> gr.State:
        return self._ui_state

    @property
    def refresh_preview_relay(self) -> Component:
        return self._ui_update_player_relay

    @property
    def run_lipsync_relay(self) -> Component:
        return self._run_lipsync_relay

    @property
    def input_video(self) -> gr.Video:
        return self._ui_input_video

    @property
    def input_audio_file(self) -> gr.File:
        return self._ui_input_audio_file

    @property
    def output_video(self) -> gr.Video:
        return self._ui_output_video

    @property
    def job_done_event(self) -> Component:
        return self._job_done_relay
