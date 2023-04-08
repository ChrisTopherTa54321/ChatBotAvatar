from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Tuple, Dict, Any, List

import gradio as gr
import numpy as np
from PIL import Image
from webuiapi import ControlNetUnit

from image_gen import ImageGen
from ui_backends.gradio_backend.component import GradioComponent
from ui_backends.gradio_backend.components.controlnet_settings import \
    ControlNetSettings
from ui_backends.gradio_backend.components.func_param_settings import \
    FuncParamSettings
from ui_backends.gradio_backend.utils.app_data import AppData
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
        with gr.Accordion(label="ControlNet Parameters") as controlnet_accordion:
            self._ui_controlnet_settings = ControlNetSettings()

        with gr.Accordion(label="Txt2Img Parameters") as txt2img_accordion:
            self._ui_txt2img_settings = FuncParamSettings(image_gen.get_txt2img_method())

        with gr.Accordion(label="Img2Img Parameters") as img2img_accordion:
            self._ui_img2img_settings = FuncParamSettings(image_gen.get_img2img_method())

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

        # The accordions need to be open to set their default values, so set up a relay to close them after the defaults are set.
        # The extra relay gives controlnet_settings.restore_state_relay a chance to run before closing the accordions
        accordions = [controlnet_accordion, txt2img_accordion, img2img_accordion]
        close_accordions_action_relay: EventWrapper = EventWrapper.create_wrapper(
            fn=lambda: len(accordions)*(gr.Accordion.update(open=False),), outputs=accordions)
        close_accordions_relay: EventWrapper = EventWrapper.create_wrapper(
            fn=lambda x: not x, inputs=close_accordions_action_relay, outputs=close_accordions_action_relay)

        # Schedule filling in defaults at client run. Use an EventRelay because for some reason Gradio won't trigger
        # the load event if any of the 'settings' instance data is in its input list
        set_defaults_relay: EventWrapper = EventWrapper.create_wrapper(fn=self._set_defaults,
                                                                       inputs=[self.instance_data, self._ui_controlnet_settings.instance_data, self._ui_txt2img_settings.instance_data,
                                                                               self._ui_img2img_settings.instance_data, self._ui_controlnet_settings.restore_state_relay, close_accordions_relay],
                                                                       outputs=[self._ui_controlnet_settings.restore_state_relay, close_accordions_relay])

        AppData.get_instance().app.load(fn=lambda x: not x, inputs=[set_defaults_relay], outputs=[set_defaults_relay])

    def _set_defaults(self, inst_data: ImageGenerator.StateData, controlnet_data: ControlNetSettings.StateData,
                      txt2img_data: FuncParamSettings.StateData, img2img_data: FuncParamSettings.StateData, controlnet_restore_relay: bool,
                      close_accordions_relay: bool) -> EventRelay:

        @dataclass
        class ControlNetDefault:
            model: str
            module: str
            params: Dict[str, Any]

        wanted_defaults: List[ControlNetDefault] = [
            ControlNetDefault(model="normal", module="normal_map", params={"weight": 0.4}),
            ControlNetDefault(model="depth", module="depth", params={"weight": 0.4}),
        ]
        image_gen_factory = ImageGenFactory.get_default_image_gen()
        models = image_gen_factory.get_controlnet_models()
        modules = image_gen_factory.get_controlnet_modules()

        item_idx: int = 0
        for idx, default in enumerate(wanted_defaults):
            if default.module and default.module not in modules:
                logger.warning(f"Default ControlNet module [{default.module}] not found")
                continue

            model_results = [x for x in models if default.model in x]
            if len(model_results) == 0:
                logger.warning(f"Default ControlNet model [{default.model}] not found")
                continue
            if len(model_results) > 1:
                logger.warning(f"Ambiguous default model [{default.model}], available. Could be: [{model_results}]")

            full_model_name = model_results[0]

            # Ensure there are enough controlnet units for the defaults
            if item_idx > len(controlnet_data.controlnet_items) - 1:
                controlnet_data.add_empty_unit()

            default_settings = {"model": full_model_name, "module": default.module}
            default_settings.update(default.params)

            item = controlnet_data.controlnet_items[item_idx]
            item.enabled = True
            item.func_params_state.init_args.update(default_settings)
            item_idx += 1

        return (not controlnet_restore_relay, not close_accordions_relay)

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
    def controlnet_settings(self) -> ControlNetSettings:
        return self._ui_controlnet_settings

    @property
    def txt2img_settings(self) -> FuncParamSettings:
        return self._ui_txt2img_settings

    @property
    def img2img_settings(self) -> FuncParamSettings:
        return self._ui_img2img_settings
