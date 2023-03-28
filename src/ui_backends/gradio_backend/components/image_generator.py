from ui_backends.gradio_backend.component import GradioComponent
from typing_extensions import override
from typing import Any, Dict, Tuple, List
import gradio as gr
from gradio.components import Component

from utils.shared import Shared
from image_gen import ImageGen
import numpy as np


class ImageGenerator(GradioComponent):
    def __init__(self):
        self._ui_image_out: gr.Image = None
        self._ui_image_prompt: gr.Textbox = None
        self._ui_image_prompt_neg: gr.Textbox = None
        self._ui_image_txt2img_btn: gr.Button = None

        self._component: Component = None
        self._inputs: List[Component] = []
        self._outputs: List[Component] = []

        self._build_component()

    def _build_component(self):
        with gr.Accordion(label="Image Generator"):
            with gr.Row():
                self._ui_image_out = gr.Image(label="Output", interactive=False).style(height=256, width=256)
            with gr.Row():
                with gr.Column(scale=3):
                    with gr.Row():
                        self._ui_image_prompt = gr.Textbox(placeholder="Prompt")
                    with gr.Row():
                        self._ui_image_prompt_neg = gr.Textbox(placeholder="Negative Prompt")
                with gr.Column(scale=1):
                    self._ui_image_txt2img_btn = gr.Button("Txt2Img")

        self._inputs = [self._ui_image_prompt, self._ui_image_prompt_neg]
        self._outputs = self._inputs.copy()

        self._ui_image_txt2img_btn.click(fn=self._handle_image_gen_clicked,
                                         inputs=self._inputs, outputs=self._ui_image_out)

    @override
    def add_inputs(self, inputs: List[Component]) -> List[Component]:
        return self._inputs + inputs

    @override
    def consume_inputs(self, inputs: List[Any]) -> Tuple[List[Any], List[Any]]:
        pos = len(self._inputs)
        inputs, consumed_inputs = (inputs[pos:], inputs[:pos])

        return (inputs, consumed_inputs)

    def _handle_image_gen_clicked(self, prompt: str, prompt_neg: str) -> Tuple[np.array]:
        image_gen = Shared.getInstance().image_gen
        result = image_gen.gen_image(prompt=prompt, negative_prompt=prompt_neg)
        return (result.image)
