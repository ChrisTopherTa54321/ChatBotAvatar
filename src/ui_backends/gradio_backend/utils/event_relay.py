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
    def create_relay(cls, fn: Callable = None, inputs: List[Component] = None, outputs: List[Component] = None, elem_id: str = None, name: str = "WrappedEvent", **kwargs) -> Component:
        '''
        Helper to create gradio input/output targets.

        This creates a dummy component that can trigger other gradio inputs, which can be used
        to isolate Components from their outputs.

        Passing the returned Component as a bool 'input' and 'output' to a gradio event handler
        allows the function to trigger the relay. If the handler returns 'not input' as the output
        (changed the state of the relay) then the relay will fire.

        Args:
            fn (Callable, optional): passed to gr.EventListener
            inputs (List[Component], optional): passed to gr.EventListener
            outputs (List[Component], optional): passed to gr.EventListener
            elem_id (str, optional): element id to set on the dummy object
            name (str, optional): debug name given to the EventRelay itself
            kwargs: additional arguments are passed to gr.EventListener

        Returns:
            Component: a dummy component to be used as an event relay
        '''
        assert gr.context.Context.block is not None, "wrap_func must be called within a 'gr.Blocks' 'with' context"

        trigger_checkbox: gr.Checkbox = gr.Checkbox(label=name, elem_id=elem_id, value=False, visible=False)
        added_inputs = [trigger_checkbox]
        added_outputs = [trigger_checkbox]

        def wrapped_func(*wrapped_inputs):
            # Remove the added_inputs in reverse order
            wrapped_inputs = list(wrapped_inputs)
            checkbox_state = wrapped_inputs.pop()
            ret = fn(*wrapped_inputs)
            return list(ret) + [checkbox_state]

        new_inputs = (inputs if inputs else []) + added_inputs
        new_outputs = (outputs if outputs else []) + added_outputs
        trigger_checkbox.change(fn=wrapped_func if fn else None, inputs=new_inputs, outputs=new_outputs, **kwargs)

        return trigger_checkbox
