from dataclasses import dataclass
from typing import Tuple

import gradio as gr
import numpy as np
from PIL import Image

from ui_backends.gradio_backend.component import GradioComponent
from ui_backends.gradio_backend.utils.event_wrapper import EventWrapper
from ui_backends.gradio_backend.utils.event_relay import EventRelay
from utils.shared import Shared


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

        self._build_component()

    def _build_component(self):
        with gr.Row():
            self._ui_image_in = gr.Image(label="Input", interactive=True).style(height=256, width=256)
            self._ui_image_out = gr.Image(label="Output", interactive=False).style(height=256, width=256)
        self._ui_image_prompt = gr.Textbox(label="Prompt")
        self._ui_image_prompt_neg = gr.Textbox(label="Negative Prompt")
        self._ui_image_txt2img_btn = gr.Button("Txt2Img", variant="primary")
        self._ui_image_img2img_btn = gr.Button("Img2Img", variant="primary")
        self._ui_image_posematch_btn = gr.Button("PoseMatch", variant="primary")
        self._ui_image_poseonlymatch_btn = gr.Button("PoseOnlyMatch", variant="primary")
        gr.Markdown(value="<p>TODO: Make these buttons better</p>")

        ui_btn_list = [self._ui_image_img2img_btn, self._ui_image_posematch_btn,
                       self._ui_image_poseonlymatch_btn, self._ui_image_txt2img_btn]
        disable_btn_ret = [gr.Button.update(interactive=False, variant="secondary")]
        enable_btn_ret = [gr.Button.update(interactive=True, variant="primary")]

        disable_buttons_relay = EventRelay.create_relay(
            lambda: (disable_btn_ret)*len(ui_btn_list), outputs=ui_btn_list, name="Disable Buttons")
        enable_buttons_relay = EventRelay.create_relay(
            lambda: (enable_btn_ret)*len(ui_btn_list), outputs=ui_btn_list, name="Enable Buttons")
        disable_btn_args = {"pre_fn": lambda x: not x,
                            "pre_inputs": [disable_buttons_relay],
                            "pre_outputs": [disable_buttons_relay],
                            "post_fn": lambda x: not x,
                            "post_inputs": [enable_buttons_relay],
                            "post_outputs": [enable_buttons_relay]}

        txt2img_wrapper = EventWrapper.create_wrapper(fn=self._handle_txt2img_click,
                                                      inputs=[self._ui_image_prompt, self._ui_image_prompt_neg], outputs=self._ui_image_out, **disable_btn_args)
        img2img_wrapper = EventWrapper.create_wrapper(fn=self._handle_img2img_click,
                                                      inputs=[self._ui_image_in, self._ui_image_prompt, self._ui_image_prompt_neg], outputs=self._ui_image_out, **disable_btn_args)
        posematch_wrapper = EventWrapper.create_wrapper(fn=self._handle_posematch_click,
                                                        inputs=[self._ui_image_in, self._ui_image_prompt, self._ui_image_prompt_neg], outputs=self._ui_image_out, **disable_btn_args, name="posematch")
        posematch_only_wrapper = EventWrapper.create_wrapper(fn=self._handle_poseonlymatch_click,
                                                             inputs=[self._ui_image_in, self._ui_image_prompt, self._ui_image_prompt_neg], outputs=self._ui_image_out, **disable_btn_args)

        self._ui_image_txt2img_btn.click(**EventWrapper.get_event_args(txt2img_wrapper))
        self._ui_image_img2img_btn.click(**EventWrapper.get_event_args(img2img_wrapper))
        self._ui_image_posematch_btn.click(**EventWrapper.get_event_args(posematch_wrapper))
        self._ui_image_poseonlymatch_btn.click(**EventWrapper.get_event_args(posematch_only_wrapper))

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

    @property
    def output_image(self) -> gr.Image:
        return self._ui_image_out
