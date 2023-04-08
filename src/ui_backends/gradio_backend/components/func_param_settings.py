''' A UI component for selecting function parameters '''

from __future__ import annotations

import inspect
import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple, Type, Union
from functools import partial

import gradio as gr
from gradio.components import Component
from PIL import Image

from ui_backends.gradio_backend.utils.event_wrapper import EventWrapper
from ui_backends.gradio_backend.component import GradioComponent
from ui_backends.gradio_backend.utils.app_data import AppData

logger = logging.getLogger(__file__)

''' A UI dialog box for selecting parameters for a Callable'''


class FuncParamSettings(GradioComponent):
    @dataclass
    class StateData:
        init_args: Dict[str, Any] = field(default_factory=dict)

    @dataclass
    class ComponentInfo:
        component: Component
        default_value: Any

    def __init__(self, func: Callable, dropdowns: Optional[Dict[str, Union[Callable, List[str]]]] = None):
        '''
        Initialize a FuncParamSettings

        Args:
            func (Callable): Callable for which to generate a settings dialog
            dropdowns (Dict[str, List[Union[str,Callable]]]): optional, list of parameter names to present as dropdown selections.
        '''
        self._ui_state: gr.State = None
        self._restore_state_relay: EventRelay = None
        self._dropdown_items: Dict[str,  Union[Callable, List[str]]] = dropdowns or {}

        # Inspect the function signature and then create a component for each parameter
        self._components: Dict[str, FuncParamSettings.ComponentInfo] = {}
        params = inspect.signature(func).parameters
        for param_name, param_info in params.items():
            param_component = self._get_component_for_param(param_info, render=False)
            if param_component:
                self._components[param_name] = FuncParamSettings.ComponentInfo(
                    component=param_component, default_value=param_info.default)

        self._build_component()

    def _build_component(self):
        self._ui_state = gr.State(value=FuncParamSettings.StateData)
        component_list: List[Component] = [comp.component for comp in self._components.values()]
        half_idx = len(component_list)//2
        with gr.Row():
            with gr.Column():
                for comp in component_list[:half_idx]:
                    comp.render()
            with gr.Column():
                for comp in component_list[half_idx:]:
                    comp.render()

        self._restore_state_relay = EventWrapper.create_wrapper(
            fn=self._restore_state, inputs=[self.instance_data], outputs=component_list)

        for comp_name, comp in self._components.items():
            comp.component.change(fn=partial(self._update_args_on_ui_change, comp_name,
                                             type(comp.component)), inputs=[self.instance_data, comp.component])

        # Schedule filling in the drop-down choices to occur on page load
        dropdown_outputs = [self._components[name].component for name in self._dropdown_items.keys()]
        AppData.get_instance().app.load(fn=self._refresh_dropdowns_handler, inputs=dropdown_outputs, outputs=dropdown_outputs)

    def _restore_state(self, state_data: FuncParamSettings.StateData):
        ret = []
        for name, component in self._components.items():
            if name in state_data.init_args:
                value = state_data.init_args[name]
            else:
                value = component.default_value
            ret.append(value)
        return ret

    def _refresh_dropdowns_handler(self, *args):
        '''
        Event handler for filling in drop-down choices.

        Args:
            *args: a variable length list of dropdown ui values
        Returns:
            a list of gradio updates
        '''
        inputs: List[str] = list(args)
        outputs: List[Dict[str, Any]] = []

        for value, choices in zip(inputs, self._dropdown_items.values()):
            if callable(choices):
                choices = choices()
            outputs.append(gr.Dropdown.update(value=value, choices=choices))

        return outputs

    def _update_args_on_ui_change(self, component_name: str, component_type: Type, inst_data: FuncParamSettings.StateData, value: Any):
        '''
        Store any changes made on the UI to the instance data

        Args:
            component_name (str): name of the component which changed
            component_type (Type): type of the component
            inst_data (FuncParamSettings.StateData): instance data
            value (Any): the new value for the ui component
        '''
        default_value = self._components[component_name].default_value
        if component_name in inst_data.init_args and type(default_value) == type(value) and default_value == value:
            del inst_data.init_args[component_name]
        else:
            if component_type is gr.Image and value is not None:
                value = Image.fromarray(value)
            inst_data.init_args[component_name] = value

    def _get_component_for_param(self, param: inspect.Parameter, **kwargs) -> Optional[Component]:
        '''
        Return a new component suitable for handling the passed in function parameter

        Args:
            param (inspect.Parameter): info on a parameter to create a component for

        Returns:
            Optional[Component]: a component suitable for modifying the parameter, or None
        '''
        new_component: Component = None
        # Determine component type by annotation or default value
        comp_type = param.annotation
        if comp_type is inspect._empty and param.default is not None:
            comp_type = type(param.default)

        if comp_type is Image:
            new_component = gr.Image(label=param.name, value=param.default, interactive=True, **kwargs)
        elif comp_type is str:
            if param.name in self._dropdown_items.keys():
                new_component = gr.Dropdown(label=param.name, value=param.default, interactive=True, **kwargs)
            else:
                new_component = gr.Textbox(
                    label=param.name, placeholder=param.default, interactive=True, **kwargs)
        elif comp_type is float:
            new_component = gr.Number(label=param.name, value=param.default, interactive=True, precision=2, **kwargs)
        elif comp_type is int:
            new_component = gr.Number(label=param.name, value=param.default, interactive=True, **kwargs)
        elif comp_type is bool:
            new_component = gr.Checkbox(label=param.name, value=param.default, interactive=True, **kwargs)
        elif param.name == "self":
            pass
        else:
            msg = f"Unable to display parameter [{param.name}]. Unhandled type: [{comp_type}]"
            new_component = gr.Markdown(msg, **kwargs)

        return new_component

    @property
    def instance_data(self) -> gr.State:
        return self._ui_state

    @property
    def restore_state_relay(self) -> Component:
        return self._restore_state_relay

    def get_component(self, name: str) -> Component:
        return self._components[name]
