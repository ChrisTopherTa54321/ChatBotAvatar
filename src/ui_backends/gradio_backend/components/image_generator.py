from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

import gradio as gr
import numpy as np
from gradio.components import Component
from PIL import Image
from webuiapi import ControlNetUnit

from image_gen import ImageGen
from ui_backends.gradio_backend.component import GradioComponent
from ui_backends.gradio_backend.components.controlnet_settings import \
    ControlNetSettings
from ui_backends.gradio_backend.components.func_param_settings import \
    FuncParamSettings
from ui_backends.gradio_backend.utils.event_relay import EventRelay
from ui_backends.gradio_backend.utils.event_wrapper import EventWrapper
from utils.image_gen_factory import ImageGenFactory

logger = logging.getLogger(__file__)


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
        self._ui_txt2img_settings: FuncParamSettings = None
        self._ui_img2img_settings: FuncParamSettings = None
        self._ui_state: gr.State = None
        self._ui_restore_state_relay: EventWrapper = None

        self._build_component()

    def _build_component(self):
        image_gen: ImageGen = ImageGenFactory.get_default_image_gen()
        if not image_gen:
            gr.Markdown("No image generator detected")
            return

        self._ui_state = gr.State(value=ImageGenerator.StateData)
        with gr.Row():
            self._ui_image_in = gr.Image(label="Input", interactive=True).style(height=256, width=256)
            self._ui_image_out = gr.Image(label="Output", interactive=False).style(height=256, width=256)
        self._ui_prompt = gr.Textbox(label="Prompt")
        self._ui_prompt_neg = gr.Textbox(label="Negative Prompt")
        self._ui_txt2img_btn = gr.Button("Txt2Img", variant="primary")
        self._ui_img2img_btn = gr.Button("Img2Img", variant="primary")

        # These Accordions must start Open to trigger proper gradio load events
        with gr.Accordion(label="ControlNet Parameters", open=False) as controlnet_accordion:
            self._ui_controlnet_settings = ControlNetSettings()

        with gr.Accordion(label="Txt2Img Parameters", open=False) as txt2img_accordion:
            self._ui_txt2img_settings = FuncParamSettings(image_gen.get_txt2img_method())

        with gr.Accordion(label="Img2Img Parameters", open=False) as img2img_accordion:
            self._ui_img2img_settings = FuncParamSettings(image_gen.get_img2img_method())

        accordions = [controlnet_accordion, txt2img_accordion, img2img_accordion]
        self._ui_restore_state_relay = EventWrapper.create_wrapper(fn=self._restore_state,
                                                                   inputs=[self.instance_data, self._ui_controlnet_settings.instance_data, self._ui_controlnet_settings.restore_state_relay,
                                                                           self._ui_txt2img_settings.instance_data, self._ui_txt2img_settings.restore_state_relay,
                                                                           self._ui_img2img_settings.instance_data, self._ui_img2img_settings.restore_state_relay],
                                                                   outputs=[self._ui_controlnet_settings.restore_state_relay, self._ui_txt2img_settings.restore_state_relay,
                                                                            self._ui_img2img_settings.restore_state_relay],
                                                                   pre_fn=lambda: len(accordions)*(gr.Accordion.update(open=True),), pre_outputs=accordions,
                                                                   post_fn=lambda: len(accordions)*(gr.Accordion.update(open=False),), post_outputs=accordions,
                                                                   fn_delay=5, post_fn_delay=5)

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
                                                      inputs=[self.instance_data, self._ui_controlnet_settings.instance_data, self._ui_txt2img_settings.instance_data,
                                                              self._ui_prompt, self._ui_prompt_neg],
                                                      outputs=self._ui_image_out, **disable_btn_args)
        img2img_wrapper = EventWrapper.create_wrapper(fn=self._handle_img2img_click,
                                                      inputs=[self.instance_data, self._ui_controlnet_settings.instance_data, self._ui_img2img_settings.instance_data,
                                                              self._ui_image_in, self._ui_prompt, self._ui_prompt_neg],
                                                      outputs=self._ui_image_out, **disable_btn_args)

        self._ui_txt2img_btn.click(**EventWrapper.get_event_args(txt2img_wrapper))
        self._ui_img2img_btn.click(**EventWrapper.get_event_args(img2img_wrapper))

    def _restore_state(self, inst_data: ImageGenerator.StateData, controlnet_data: ControlNetSettings.StateData, controlnet_refresh_relay: bool,
                       txt2img_data: FuncParamSettings.StateData, txt2img_refresh_relay: bool, img2img_data: FuncParamSettings.StateData, img2img_refresh_relay: bool):
        # Trigger refresh on any components with data set

        controlnet_item = controlnet_data.controlnet_items[controlnet_data.selected_idx] if controlnet_data.selected_idx < len(
            controlnet_data.controlnet_items) else None
        if controlnet_item is not None and len(controlnet_item.func_params_state.init_args) > 0:
            controlnet_refresh_relay = not controlnet_refresh_relay
        if len(txt2img_data.init_args) > 0:
            txt2img_refresh_relay = not txt2img_refresh_relay
        if len(img2img_data.init_args) > 0:
            img2img_refresh_relay = not img2img_refresh_relay

        return (controlnet_refresh_relay, txt2img_refresh_relay, img2img_refresh_relay)

    def _handle_txt2img_click(self, inst_data: ImageGenerator.StateData, controlnet_inst_data: ControlNetSettings.StateData,
                              txt2img_inst_data: FuncParamSettings.StateData, prompt: str, negative_prompt: str) -> Tuple[np.array]:
        if not inst_data.image_gen:
            inst_data.image_gen = ImageGenFactory.get_default_image_gen()

        controlnet_units = [ControlNetUnit(**info.func_params_state.init_args)
                            for info in controlnet_inst_data.controlnet_items if info.enabled]
        result = inst_data.image_gen.gen_image(
            prompt=prompt, negative_prompt=negative_prompt, controlnet_units=controlnet_units, **txt2img_inst_data.init_args)
        return (result.image)

    def _handle_img2img_click(self, inst_data: ImageGenerator.StateData, controlnet_inst_data: ControlNetSettings.StateData,
                              img2img_inst_data: FuncParamSettings.StateData, input_image: np.ndarray, prompt: str, negative_prompt: str) -> Tuple[np.array]:
        if not inst_data.image_gen:
            inst_data.image_gen = ImageGenFactory.get_default_image_gen()

        controlnet_units = [ControlNetUnit(**info.func_params_state.init_args)
                            for info in controlnet_inst_data.controlnet_items if info.enabled]

        image = Image.fromarray(input_image)
        result = inst_data.image_gen.gen_image(
            prompt=prompt, negative_prompt=negative_prompt, input_image=image, controlnet_units=controlnet_units, **img2img_inst_data.init_args)
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

    @property
    def restore_state_relay(self) -> Component:
        return self._ui_restore_state_relay

    @property
    def controlnet_settings(self) -> ControlNetSettings:
        return self._ui_controlnet_settings

    @property
    def txt2img_settings(self) -> FuncParamSettings:
        return self._ui_txt2img_settings

    @property
    def img2img_settings(self) -> FuncParamSettings:
        return self._ui_img2img_settings
