''' Component to customize ControlNet settings '''

from __future__ import annotations

import inspect
import logging
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Union

import gradio as gr
from gradio.components import Component
from PIL import Image

from ui_backends.gradio_backend.component import GradioComponent
from ui_backends.gradio_backend.components.func_param_settings import \
    FuncParamSettings
from ui_backends.gradio_backend.utils.app_data import AppData
from utils.image_gen_factory import ImageGenFactory

from webuiapi import ControlNetUnit

logger = logging.getLogger(__file__)

''' A UI dialog box for selecting parameters for a Callable'''


class ControlNetSettings(GradioComponent):
    @dataclass
    class StateData:
        enabled: bool = False
        func_params_data: FuncParamSettings.StateData = None

    def __init__(self):
        self._ui_state: gr.State = None
        self._ui_func_settings: FuncParamSettings = None
        self._ui_enabled_chkbox: gr.Checkbox = None
        self._build_component()

    def _build_component(self):
        self._ui_state = gr.State(value=ControlNetSettings.StateData)
        self._ui_enabled_chkbox = gr.Checkbox(label="Enable ControlNet")
        controlnet_dropdowns = {"model": ControlNetSettings._get_controlnet_models,
                                "module": ControlNetSettings._get_controlnet_modules}
        self._ui_func_settings = FuncParamSettings(ControlNetUnit.__init__, dropdowns=controlnet_dropdowns)

        self._ui_enabled_chkbox.change(fn=self._handle_enabled_change, inputs=[
                                       self.instance_data, self._ui_enabled_chkbox])

        AppData.get_instance().app.load(fn=self._get_param_state_data, inputs=[
            self.instance_data, self._ui_func_settings.instance_data])

    def _get_param_state_data(self, inst_data: ControlNetSettings.StateData, func_params_inst_data: FuncParamSettings.StateData):
        ''' Pass the FuncParamSettings instance data through to the ControlNetSettings instance data '''
        inst_data.func_params_data = func_params_inst_data

    def _handle_enabled_change(self, inst_data: ControlNetSettings.StateData, enabled: bool):
        inst_data.enabled = enabled

    @classmethod
    def _get_controlnet_models(cls):
        return ImageGenFactory.get_default_image_gen().get_controlnet_models()

    @classmethod
    def _get_controlnet_modules(cls):
        return ImageGenFactory.get_default_image_gen().get_controlnet_modules()

    @property
    def instance_data(self) -> gr.State:
        return self._ui_state

    @property
    def models_dropdown(self) -> gr.Dropdown:
        return self._ui_func_settings.get_component("model")

    @property
    def modules_dropdown(self) -> gr.Dropdown:
        return self._ui_func_settings.get_component("module")
