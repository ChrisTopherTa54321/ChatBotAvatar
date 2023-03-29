from ui_backends.gradio_backend.component import GradioComponent
from typing_extensions import override
from typing import Any, Dict, Tuple, List
import gradio as gr
from gradio.components import Component
from PIL import Image

from utils.shared import Shared
from image_gen import ImageGen
import numpy as np
from dataclasses import dataclass


class ImageGenerator(GradioComponent):
    @dataclass
    class StateData:
        pass

    def __init__(self):
        self._ui_image_in: gr.Image = None
        self._ui_image_out: gr.Image = None
        self._ui_image_prompt: gr.Textbox = None
        self._ui_image_prompt_neg: gr.Textbox = None
        self._ui_image_txt2img_btn: gr.Button = None
        self._ui_image_img2img_btn: gr.Button = None
        self._ui_image_posematch_btn: gr.Button = None
        self._ui_image_poseonlymatch_btn: gr.Button = None

        self._component: Component = None
        self._inputs: List[Component] = []
        self._outputs: List[Component] = []

        self._build_component()

    def _build_component(self):
        with gr.Box():
            with gr.Row():
                self._ui_image_in = gr.Image(label="Input", interactive=False).style(height=256, width=256)
                self._ui_image_out = gr.Image(label="Output", interactive=False).style(height=256, width=256)
            self._ui_image_prompt = gr.Textbox(placeholder="Prompt")
            self._ui_image_prompt_neg = gr.Textbox(placeholder="Negative Prompt")
            self._ui_image_txt2img_btn = gr.Button("Txt2Img")
            self._ui_image_img2img_btn = gr.Button("Img2Img")
            self._ui_image_posematch_btn = gr.Button("PoseMatch")
            self._ui_image_poseonlymatch_btn = gr.Button("PoseOnlyMatch")

        self._ui_image_txt2img_btn.click(fn=self._handle_txt2img_click,
                                         inputs=[self._ui_image_prompt, self._ui_image_prompt_neg], outputs=self._ui_image_out)

        self._ui_image_img2img_btn.click(fn=self._handle_img2img_click,
                                         inputs=[self._ui_image_in, self._ui_image_prompt, self._ui_image_prompt_neg], outputs=self._ui_image_out)
        self._ui_image_posematch_btn.click(fn=self._handle_posematch_click,
                                           inputs=[self._ui_image_in, self._ui_image_prompt, self._ui_image_prompt_neg], outputs=self._ui_image_out)

        self._ui_image_poseonlymatch_btn.click(fn=self._handle_poseonlymatch_click,
                                               inputs=[self._ui_image_in, self._ui_image_prompt, self._ui_image_prompt_neg], outputs=self._ui_image_out)

    def _handle_posematch_click(self, input_image: np.ndarray, prompt: str, negative_prompt: str) -> Tuple[np.array]:
        image_gen = Shared.getInstance().image_gen
        image = Image.fromarray(input_image)
        result = image_gen.gen_image(prompt=prompt, negative_prompt=negative_prompt,
                                     input_image=image, match_pose=True, match_img=True)
        return (result.image)

    def _handle_poseonlymatch_click(self, input_image: np.ndarray, prompt: str, negative_prompt: str) -> Tuple[np.array]:
        image_gen = Shared.getInstance().image_gen
        image = Image.fromarray(input_image)
        result = image_gen.gen_image(prompt=prompt, negative_prompt=negative_prompt,
                                     input_image=image, match_pose=True, match_img=False)
        return (result.image)

    def _handle_txt2img_click(self, prompt: str, negative_prompt: str) -> Tuple[np.array]:
        image_gen = Shared.getInstance().image_gen
        result = image_gen.gen_image(prompt=prompt, negative_prompt=negative_prompt)
        return (result.image)

    def _handle_img2img_click(self, input_image: np.ndarray, prompt: str, negative_prompt: str) -> Tuple[np.array]:
        image_gen = Shared.getInstance().image_gen
        image = Image.fromarray(input_image)
        result = image_gen.gen_image(prompt=prompt, negative_prompt=negative_prompt, input_image=image, match_img=True)
        return (result.image)

    @property
    def input_image(self) -> gr.Image:
        return self._ui_image_in
