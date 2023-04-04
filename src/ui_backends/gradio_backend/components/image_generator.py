from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

import gradio as gr
import numpy as np
from PIL import Image

from image_gen import ImageGen
from ui_backends.gradio_backend.component import GradioComponent
from ui_backends.gradio_backend.components.controlnet_settings import \
    ControlNetSettings
from ui_backends.gradio_backend.components.func_param_settings import \
    FuncParamSettings
from ui_backends.gradio_backend.utils.event_relay import EventRelay
from ui_backends.gradio_backend.utils.event_wrapper import EventWrapper
from utils.image_gen_factory import ImageGenFactory
from webuiapi import ControlNetUnit


class ImageGenerator(GradioComponent):
    @dataclass
    class StateData:
        image_gen: ImageGen = None

    def __init__(self):
        self._ui_image_in: gr.Image = None
        self._ui_image_out: gr.Image = None
        self._ui_prompt: gr.Textbox = None
        self._ui_prompt_neg: gr.Textbox = None
        self._ui_txt2img_btn: gr.Button = None
        self._ui_img2img_btn: gr.Button = None
        self._ui_controlnet_settings: ControlNetSettings = None
        self._ui_state: gr.State = None

        self._build_component()

    def _build_component(self):
        self._ui_state = gr.State(value=ImageGenerator.StateData)
        with gr.Row():
            self._ui_image_in = gr.Image(label="Input", interactive=True).style(height=256, width=256)
            self._ui_image_out = gr.Image(label="Output", interactive=False).style(height=256, width=256)
        self._ui_prompt = gr.Textbox(label="Prompt")
        self._ui_prompt_neg = gr.Textbox(label="Negative Prompt")
        self._ui_txt2img_btn = gr.Button("Txt2Img", variant="primary")
        self._ui_img2img_btn = gr.Button("Img2Img", variant="primary")

        with gr.Accordion(label="ControlNet Parameters", open=False):
            self._ui_controlnet_settings = ControlNetSettings()

        ui_btn_list = [self._ui_img2img_btn, self._ui_txt2img_btn]
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
                                                      inputs=[self.instance_data, self._ui_controlnet_settings.instance_data,
                                                              self._ui_prompt, self._ui_prompt_neg],
                                                      outputs=self._ui_image_out, **disable_btn_args)
        img2img_wrapper = EventWrapper.create_wrapper(fn=self._handle_img2img_click,
                                                      inputs=[self.instance_data, self._ui_controlnet_settings.instance_data,
                                                              self._ui_image_in, self._ui_prompt, self._ui_prompt_neg],
                                                      outputs=self._ui_image_out, **disable_btn_args)

        self._ui_txt2img_btn.click(**EventWrapper.get_event_args(txt2img_wrapper))
        self._ui_img2img_btn.click(**EventWrapper.get_event_args(img2img_wrapper))

    def _handle_txt2img_click(self, inst_data: ImageGenerator.StateData, controlnet_inst_data: ControlNetSettings.StateData, prompt: str, negative_prompt: str) -> Tuple[np.array]:
        if not inst_data.image_gen:
            inst_data.image_gen = ImageGenFactory.get_default_image_gen()

        if controlnet_inst_data.enabled:
            controlnet_units = [ControlNetUnit(**controlnet_inst_data.func_params_data.init_args)]
        else:
            controlnet_units = None

        result = inst_data.image_gen.gen_image(
            prompt=prompt, negative_prompt=negative_prompt, controlnet_units=controlnet_units)
        return (result.image)

    def _handle_img2img_click(self, inst_data: ImageGenerator.StateData, controlnet_inst_data: ControlNetSettings.StateData, input_image: np.ndarray, prompt: str, negative_prompt: str) -> Tuple[np.array]:
        if not inst_data.image_gen:
            inst_data.image_gen = ImageGenFactory.get_default_image_gen()

        if controlnet_inst_data.enabled:
            controlnet_units = [ControlNetUnit(controlnet_inst_data.func_params_data)]
        else:
            controlnet_units = None

        image = Image.fromarray(input_image)
        result = inst_data.image_gen.gen_image(
            prompt=prompt, negative_prompt=negative_prompt, input_image=image, controlnet_units=controlnet_units)
        return (result.image)

    @property
    def input_image(self) -> gr.Image:
        return self._ui_image_in

    @property
    def output_image(self) -> gr.Image:
        return self._ui_image_out

    @property
    def instance_data(self) -> gr.State:
        return self._ui_state
