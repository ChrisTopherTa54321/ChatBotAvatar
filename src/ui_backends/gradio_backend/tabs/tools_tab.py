''' Tools interface tab '''
import logging
import os
import wave
from typing import List, Tuple
from PIL import Image
import uuid
import numpy as np

from utils.shared import Shared

import gradio as gr
import tempfile
from typing_extensions import override

from image_gen import ImageGen
from tts import Tts
from ui_backends.gradio_backend.tab import GradioTab
from ui_backends.gradio_backend.components.image_generator import ImageGenerator
from ui_backends.gradio_backend.components.tts_speaker import TtsSpeaker


logger = logging.getLogger(__file__)


class ToolsTab(GradioTab):

    def __init__(self):
        self._ui_lip_sync_btn: gr.Button = None
        self._ui_lip_sync_input: gr.Video = None
        self._ui_lip_sync_audio: gr.Audio = None
        self._ui_lip_sync_audio_file: gr.File = None
        self._ui_lip_sync_output_video: gr.Video = None

        self._ui_motion_match_btn: gr.Button = None
        self._ui_motion_match_input_image: gr.Image = None
        self._ui_motion_match_driving_video: gr.Video = None
        self._ui_motion_match_output_video: gr.Video = None

        self._ui_image_gen: ImageGenerator = None
        self._ui_tts: TtsSpeaker = None

        # self._ui_image_gen_textbox: gr.Textbox = None
        # self._ui_image_gen_btn: gr.Button = None
        # self._ui_image_gen_output: gr.Image = None

    @override
    def build_ui(self):
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
            with gr.Row():
                self._ui_motion_match_input_image = gr.Image(label="Motion Match Input Image")
                self._ui_motion_match_driving_video = gr.Video(label="Driving Video")
            with gr.Row():
                self._ui_motion_match_output_video = gr.Video(label="Motion Match Output", render=False)
                with gr.Column():
                    self._ui_motion_match_btn = gr.Button("Run Motion Match")
                    gr.Button("Send to Lip Sync").click(fn=lambda x: x, inputs=[
                        self._ui_motion_match_output_video], outputs=[self._ui_lip_sync_input])
                with gr.Column():
                    self._ui_motion_match_output_video.render()

        with gr.Accordion("Lip Sync", open=False):
            gr.Markdown("""
            <p>
            Process using <a href='https://github.com/Rudrabha/Wav2Lip'>Wav2Lip</a>
            </p><p>
            Select a source input video or image (you can upload a still image in the 'video' box), and the audio to lip sync to, then click the Run Lip sync button.
            </p>
            """)
            with gr.Row():
                self._ui_lip_sync_input.render()  # = gr.Video(label="Lip Sync Input")
                with gr.Column():
                    self._ui_lip_sync_audio = gr.Audio(label="Lip Sync Audio")
                    self._ui_lip_sync_audio_file = gr.File(label="Wav File")
            with gr.Row():
                self._ui_lip_sync_btn = gr.Button("Run Lip Sync")
                self._ui_lip_sync_output_video = gr.Video(label="Lip Sync Output")

        self._ui_image_gen = ImageGenerator()

        self._ui_lip_sync_btn.click(fn=self._handle_lip_sync_clicked, inputs=[
                                    self._ui_lip_sync_audio, self._ui_lip_sync_audio_file, self._ui_lip_sync_input], outputs=[self._ui_lip_sync_output_video])
        self._ui_motion_match_btn.click(fn=self._handle_motion_match_clicked, inputs=[
                                        self._ui_motion_match_driving_video, self._ui_motion_match_input_image], outputs=[self._ui_motion_match_output_video])

    def _handle_image_gen_clicked(self, prompt: str) -> Tuple[np.array]:
        image_gen = Shared.getInstance().image_gen
        result = image_gen.gen_image(prompt=prompt)
        return (result.image)

    def _handle_motion_match_clicked(self, driving_video: str, image_data: np.array) -> Tuple[str]:
        '''
        Handles the Motion Match button press. Runs Thin Plate Spline Motion Model demo  on the inputs

        Args:
            driving_video (str): path to the driving video for motion matching
            image_path (str): path to the image that should be applied to the video

        Returns:
            Tuple[str]: path to output video
        '''
        args = Shared.getInstance().args
        unique_id: str = uuid.uuid4().hex

        image_filename: str = os.path.join(args.temp_dir, f"{unique_id}_image.png")
        img: Image = Image.fromarray(image_data)
        img.save(image_filename)
        try:
            from avatar.motion_match import MotionMatch
            out_filename: str = os.path.join(args.temp_dir, f"{unique_id}_motion_matched_video.mp4")
            MotionMatch.render(source_image=image_filename, driving_video=driving_video, output_path=out_filename)
        except Exception as e:
            logger.error(e)
            out_filename = None

        return out_filename

    def _handle_lip_sync_clicked(self, audio_data: Tuple[int, np.array], audio_path: tempfile.NamedTemporaryFile, image_or_video_path: str) -> Tuple[str]:
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
        # Save to disk to have a filename for wav2lip
        if isinstance(audio_data, Tuple):
            sampling_rate, audio_buffer = audio_data
            audio_filename: str = os.path.join(args.temp_dir, f"{unique_id}_lipsync.wav")
            with wave.open(audio_filename, 'wb') as wav:
                wav.setframerate(sampling_rate)
                wav.setnchannels(1)
                wav.setsampwidth(2)
                wav.writeframesraw(audio_buffer)
        elif isinstance(audio_data, str):
            audio_filename = audio_data
        elif audio_path:
            audio_filename = audio_path.name
        else:
            raise Exception("Bad audio file")

        try:
            from avatar.lip_sync import LipSync
            out_filename: str = os.path.join(args.temp_dir, f"{unique_id}_synced_video.mp4")
            LipSync.render(image_or_video_path, audio_filename, out_filename)
        except Exception as e:
            logger.error(e)
            out_filename = None
        return out_filename
