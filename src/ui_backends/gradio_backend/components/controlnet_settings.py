''' Component to customize ControlNet settings '''

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Union

import gradio as gr
from gradio.components import Component
from PIL import Image
from webuiapi import ControlNetUnit

from ui_backends.gradio_backend.component import GradioComponent
from ui_backends.gradio_backend.components.func_param_settings import \
    FuncParamSettings
from ui_backends.gradio_backend.utils.app_data import AppData
from ui_backends.gradio_backend.utils.event_relay import EventRelay
from utils.image_gen_factory import ImageGenFactory

logger = logging.getLogger(__file__)

''' A UI dialog box for selecting parameters for a Callable'''


class ControlNetSettings(GradioComponent):
    @dataclass
    class MultiControlNetItem:
        enabled: bool = False
        func_params_state: FuncParamSettings.StateData = field(default_factory=FuncParamSettings.StateData)

    @dataclass
    class StateData:
        controlnet_items: List[ControlNetSettings.MultiControlNetItem] = field(default_factory=list)
        selected_idx: int = 0
        ui_func_params_data: FuncParamSettings.StateData = None

        def __post_init__(self):
            self.controlnet_items.append(ControlNetSettings.MultiControlNetItem())

    def __init__(self):
        self._ui_state: gr.State = None
        self._ui_func_settings: FuncParamSettings = None
        self._ui_enabled_chkbox: gr.Checkbox = None
        self._ui_prev_btn: gr.Button = None
        self._ui_next_btn: gr.Button = None
        self._ui_idx_text: gr.Markdown = None
        self._build_component()

    def _build_component(self):
        self._ui_state = gr.State(value=ControlNetSettings.StateData)
        with gr.Box():
            self._ui_idx_text = gr.Markdown(ControlNetSettings._get_index_string(ControlNetSettings.StateData()))
            self._ui_prev_btn = gr.Button("Prev")
            self._ui_next_btn = gr.Button("Next", variant="primary")
        with gr.Row():
            self._ui_enabled_chkbox = gr.Checkbox(label="Enable")

        controlnet_dropdowns = {"model": ControlNetSettings._get_controlnet_models,
                                "module": ControlNetSettings._get_controlnet_modules}
        self._ui_func_settings = FuncParamSettings(ControlNetUnit.__init__, dropdowns=controlnet_dropdowns)

        self._ui_enabled_chkbox.change(fn=self._handle_enabled_change, inputs=[
                                       self.instance_data, self._ui_func_settings.instance_data, self._ui_enabled_chkbox], outputs=[self._ui_idx_text])

        self._ui_next_btn.click(fn=self._handle_next_controlnet,
                                inputs=[self.instance_data, self._ui_func_settings.instance_data, self._ui_enabled_chkbox,
                                        self._ui_func_settings.restore_state_relay],
                                outputs=[self._ui_prev_btn, self._ui_enabled_chkbox, self._ui_idx_text, self._ui_func_settings.restore_state_relay])

        self._ui_prev_btn.click(fn=self._handle_prev_controlnet,
                                inputs=[self.instance_data, self._ui_func_settings.instance_data, self._ui_enabled_chkbox,
                                        self._ui_func_settings.restore_state_relay],
                                outputs=[self._ui_prev_btn, self._ui_enabled_chkbox, self._ui_idx_text, self._ui_func_settings.restore_state_relay])

        # On page load link the FuncParamSettings with the ControlNetSettings
        AppData.get_instance().app.load(fn=self._get_param_state_data, inputs=[
            self.instance_data, self._ui_func_settings.instance_data])

    def _get_param_state_data(self, inst_data: ControlNetSettings.StateData, func_params_inst_data: FuncParamSettings.StateData):
        ''' Pass the FuncParamSettings instance data through to the ControlNetSettings instance data '''
        inst_data.ui_func_params_data = func_params_inst_data

    def _handle_next_controlnet(self, inst_data: ControlNetSettings.StateData, func_params_inst_data: FuncParamSettings.StateData, enabled: bool, restore_state_relay: bool) -> EventRelay:
        '''
        Handle the 'next' button to select the next ControlNet settings
        Args:
            inst_data (ControlNetSettings.StateData): instance data
            restore_state_relay (bool): relay to toggle in order to trigger FuncParamSettings to restore its settings

        Returns:
            List[gr.Button, bool, str, EventRelay]  previous button, enabled checkbox,  index string, and restore_state_relay
        '''

        # If already at the end of the list then add a new unit
        if inst_data.selected_idx == len(inst_data.controlnet_items) - 1:
            # Unless there were no changes to the current one, in which case ignore the click
            if len(func_params_inst_data.init_args) == 0:
                return [gr.Button.update(), enabled, ControlNetSettings._get_index_string(inst_data), restore_state_relay]

            # Add an empty unit to the list
            new_data = ControlNetSettings.MultiControlNetItem()
            inst_data.controlnet_items.append(new_data)

        # Save the current state and update func_params_state with the new state
        inst_data.controlnet_items[inst_data.selected_idx].func_params_state.__dict__.update(
            func_params_inst_data.__dict__)
        inst_data.controlnet_items[inst_data.selected_idx].enabled = enabled

        inst_data.selected_idx += 1

        func_params_inst_data.__dict__.update(
            inst_data.controlnet_items[inst_data.selected_idx].func_params_state.__dict__)
        enabled = inst_data.controlnet_items[inst_data.selected_idx].enabled

        # Toggle the relay to trigger a FuncParams ui update
        return [gr.Button.update(variant="secondary" if inst_data.selected_idx == 0 else "primary"), enabled, ControlNetSettings._get_index_string(inst_data), not restore_state_relay]

    def _handle_prev_controlnet(self, inst_data: ControlNetSettings.StateData, func_params_inst_data: FuncParamSettings.StateData, enabled: bool, restore_state_relay: bool) -> EventRelay:
        '''
        Handle the 'next' button to select the next ControlNet settings
        Args:
            inst_data (ControlNetSettings.StateData): instance data
            restore_state_relay (bool): relay to toggle in order to trigger FuncParamSettings to restore its settings

        Returns:
            List[gr.Button, bool, str, EventRelay]  previous button, enabled checkbox,  index string, and restore_state_relay
        '''
        if inst_data.selected_idx == 0:
            return [gr.Button.update(), enabled, ControlNetSettings._get_index_string(inst_data), restore_state_relay]

        # Save the current state and update func_params_state with the new state
        inst_data.controlnet_items[inst_data.selected_idx].func_params_state.__dict__.update(
            func_params_inst_data.__dict__)
        inst_data.controlnet_items[inst_data.selected_idx].enabled = enabled

        inst_data.selected_idx -= 1

        func_params_inst_data.__dict__.update(
            inst_data.controlnet_items[inst_data.selected_idx].func_params_state.__dict__)
        enabled = inst_data.controlnet_items[inst_data.selected_idx].enabled

        # Toggle the relay to trigger a FuncParams ui update
        return [gr.Button.update(variant="secondary" if inst_data.selected_idx == 0 else "primary"), enabled, ControlNetSettings._get_index_string(inst_data), not restore_state_relay]

    def _handle_enabled_change(self, inst_data: ControlNetSettings.StateData, func_params_inst_data: FuncParamSettings.StateData, enabled: bool):
        inst_data.controlnet_items[inst_data.selected_idx].enabled = enabled
        inst_data.controlnet_items[inst_data.selected_idx].func_params_state.__dict__.update(
            func_params_inst_data.__dict__)
        return ControlNetSettings._get_index_string(inst_data)

    @classmethod
    def _get_index_string(cls, inst_data: ControlNetSettings.StateData) -> str:
        enabled_cnt = len([x for x in inst_data.controlnet_items if x.enabled])
        return f"<p>Multi-Control Net: {inst_data.selected_idx+1}/{len(inst_data.controlnet_items)} ({enabled_cnt} active)</p>"

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
