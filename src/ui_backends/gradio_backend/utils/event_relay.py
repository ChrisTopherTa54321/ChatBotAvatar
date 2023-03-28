''' Helper to wrap a Gradio event callback within another function '''
from __future__ import annotations
from typing import Tuple, List, Callable
from typing_extensions import override
import gradio as gr
from gradio.components import Component
import logging

logger = logging.getLogger(__file__)


class EventRelay():
    @classmethod
    def wrap_event(cls, func: Callable, inputs: List[Component], outputs: List[Component], name: str = "TEST") -> Component:
        assert gr.context.Context.block is not None, "wrap_func must be called within a 'gr.Blocks' 'with' context"

        trigger_checkbox: gr.Checkbox = gr.Checkbox(value=False, visible=False)
        added_inputs = [trigger_checkbox]
        added_outputs = [trigger_checkbox]

        def wrapped_func(*wrapped_inputs):
            # Remove the added_inputs in reverse order
            wrapped_inputs = list(wrapped_inputs)
            checkbox_state = wrapped_inputs.pop()
            ret = func(*wrapped_inputs)
            return list(ret) + [checkbox_state]

        new_inputs = inputs + added_inputs
        new_outputs = outputs + added_outputs
        trigger_checkbox.change(fn=wrapped_func, inputs=new_inputs, outputs=new_outputs)

        return trigger_checkbox
