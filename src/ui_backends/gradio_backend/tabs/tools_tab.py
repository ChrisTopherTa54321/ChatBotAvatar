''' Tools interface tab '''
import logging
from typing import Tuple

import gradio as gr
import numpy as np
from typing_extensions import override

from ui_backends.gradio_backend.components.chat_box import ChatBox
from ui_backends.gradio_backend.components.image_generator import \
    ImageGenerator
from ui_backends.gradio_backend.components.lip_sync_ui import LipSyncUi
from ui_backends.gradio_backend.components.motion_matcher import MotionMatcher
from ui_backends.gradio_backend.components.tts_speaker import TtsSpeaker
from ui_backends.gradio_backend.tab import GradioTab
from ui_backends.gradio_backend.utils.helpers import audio_to_file_event

logger = logging.getLogger(__file__)


class ToolsTab(GradioTab):

    def __init__(self):
        self._ui_chatbox: ChatBox = None
        self._ui_image_gen: ImageGenerator = None
        self._ui_tts: TtsSpeaker = None
        self._ui_motion_matcher: MotionMatcher = None
        self._ui_lip_sync_ui: LipSyncUi = None

    @override
    def build_ui(self):
        with gr.Accordion("Image Generator", open=False):
            with gr.Box():
                self._ui_image_gen = ImageGenerator()
            send_image_to_motion_match_btn = gr.Button("Send Output to Motion Match Input")

        self._ui_lip_sync_input = gr.Video(label="Lip Sync Input", render=False)
        with gr.Accordion("Motion Match", open=False):
            gr.Markdown("""
            <p>
            Process Using <a href='https://github.com/yoyo-nb/Thin-Plate-Spline-Motion-Model'>Thin Plate Spline Motion Model</a>
            </p><p>
            Select an input image and a driving video. The video should be 256x256, and it is best if the image is in a similar pose as the first frame of the video.
            Click the Run Motion Match button and get the result in the output box. This output can then have Lip Sync applied to it.
            </p>
            """)
            with gr.Box():
                self._ui_motion_matcher = MotionMatcher()
            send_vid_to_lipsync: gr.Button = gr.Button("Send Output to Lip Sync Input")

        with gr.Accordion("Chat", open=False):
            self._ui_chatbox = ChatBox()
            send_chat_to_tts = gr.Button("Send Last Response to TTS Input")

        with gr.Accordion("Text to Speech", open=False):
            self._ui_tts = TtsSpeaker()
            send_audio_to_lipsync: gr.Button = gr.Button("Send Output to Lip Sync Input")

        with gr.Accordion("Lip Sync", open=False):
            gr.Markdown("""
                <p>
                Process using <a href='https://github.com/Rudrabha/Wav2Lip'>Wav2Lip</a>
                </p><p>
                Select a source input video or image (you can upload a still image in the 'video' box), and the audio to lip sync to, then click the Run Lip sync button.
                </p>
                """)
            self._ui_lip_sync_ui: LipSyncUi = LipSyncUi()

        send_image_to_motion_match_btn.click(fn=lambda x: x, inputs=[self._ui_image_gen.output_image], outputs=[
                                             self._ui_motion_matcher.input_image])
        send_vid_to_lipsync.click(fn=lambda x: x, inputs=[self._ui_motion_matcher.output_video], outputs=[
            self._ui_lip_sync_ui.input_video])
        send_audio_to_lipsync.click(fn=lambda filename, toggle: (audio_to_file_event(filename), not toggle),
                                    inputs=[self._ui_tts.output_audio, self._ui_lip_sync_ui.refresh_preview_relay],
                                    outputs=[self._ui_lip_sync_ui.input_audio_file, self._ui_lip_sync_ui.refresh_preview_relay])
        send_chat_to_tts.click(fn=lambda x: x, inputs=[self._ui_chatbox.chat_response], outputs=[self._ui_tts.prompt])
