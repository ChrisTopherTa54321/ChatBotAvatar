''' A UI component for selecting function parameters '''

from __future__ import annotations

import inspect
import logging
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Union

import gradio as gr
from gradio.components import Component
from PIL import Image

from ui_backends.gradio_backend.component import GradioComponent
from ui_backends.gradio_backend.utils.app_data import AppData

logger = logging.getLogger(__file__)

''' A UI dialog box for selecting parameters for a Callable'''


class FuncParamSettings(GradioComponent):
    @dataclass
    class StateData:
        pass

    def __init__(self, func: Callable, dropdowns: Optional[Dict[str, Union[Callable, List[str]]]] = None):
        '''
        Initialize a FuncParamSettings

        Args:
            func (Callable): Callable for which to generate a settings dialog
            dropdowns (Dict[str, List[Union[str,Callable]]]): optional, list of parameter names to present as dropdown selections.
        '''
        self._ui_state: gr.State = None
        self._dropdown_items: Dict[str,  Union[Callable, List[str]]] = dropdowns or {}

        self._components: Dict[str, Component] = {}
        params = inspect.signature(func).parameters
        for param_name, param_info in params.items():
            param_component = self._get_component_for_annotations(
                param_info, dropdowns=dropdowns.keys() if dropdowns else None, render=False)
            if param_component:
                self._components[param_name] = param_component

        self._build_component()

    def _build_component(self):
        self._ui_state = gr.State(value=FuncParamSettings.StateData)
        component_list = list(self._components.values())
        with gr.Row():
            with gr.Column():
                for comp in component_list[::2]:
                    comp.render()
            with gr.Column():
                for comp in component_list[1::2]:
                    comp.render()

        dropdown_outputs = [self._components[name] for name in self._dropdown_items.keys()]
        AppData.get_instance().app.load(fn=self._refresh_ui, inputs=dropdown_outputs, outputs=dropdown_outputs)

    def _refresh_ui(self, *args):
        inputs: List[str] = list(args)
        outputs: List[Dict[str, Any]] = []

        for idx, (name, choices) in enumerate(self._dropdown_items.items()):
            if callable(choices):
                choices = choices()
            outputs.append(gr.Dropdown.update(choices=choices, value=inputs[idx]))

        return outputs

    def _get_component_for_annotations(self, param: inspect.Parameter, **kwargs) -> Optional[Component]:
        new_component: Component = None

        if param.annotation is Image:
            new_component = gr.Image(label=param.name, value=param.default, interactive=True, **kwargs)
        elif param.annotation in [str, float, int]:
            if param.name in self._dropdown_items.keys():
                new_component = gr.Dropdown(label=param.name, value=param.default, interactive=True, **kwargs)
            else:
                new_component = gr.Textbox(
                    label=param.name, placeholder=param.default, interactive=True, **kwargs)
        elif param.annotation is bool:
            new_component = gr.Checkbox(label=param.name, value=param.default, interactive=True, **kwargs)
        elif param.annotation is inspect._empty:
            pass
        else:
            logger.warn(f"Unhandled parameter type [{param.annotation}] for [{param.name}]")

        return new_component

    @property
    def instance_data(self) -> gr.State:
        return self._ui_state
