''' Wraps a Gradio event with pre- and post- events '''
from __future__ import annotations

import logging
from typing import Callable, List, Tuple

import gradio as gr
from gradio.components import Component

from ui_backends.gradio_backend.utils.event_relay import EventRelay

logger = logging.getLogger(__file__)


class EventWrapper():
    @classmethod
    def create_wrapper(cls,
                       fn: Callable = None, inputs: List[Component] = None, outputs: List[Component] = None,
                       pre_fn: Callable = None, pre_inputs: List[Component] = None, pre_outputs: List[Component] = None,
                       post_fn: Callable = None, post_inputs: List[Component] = None, post_outputs: List[Component] = None,
                       elem_id: str = None, name: str = "WrappedEvent", **kwargs) -> Component:
        '''
        Helper to wrap a gradio event with pre- and post events.

        This can be used to, for example, disable and re-enable the Submit button before and after an actual event

        Args:
            fn (Callable, optional): primary event function call to wrap
            inputs (List[Component], optional): list of inputs for primary function call
            outputs (List[Component], optional): list of outputs for primary function call
            pre_fn (Callable, optional): Function to call before calling primary function
            pre_inputs (List[Component], optional): list of inputs for the pre-function call
            pre_outputs (List[Component], optional): list of outputs for the pre-function call
            post_fn (Callable, optional): Function to call after calling the primary function
            post_inputs (List[Component], optional): list of inputs for the pre-function call
            post_outputs (List[Component], optional): list of outputs for the post-function call
            elem_id (str, optional): Element Id to give the primary function call's dummy object.
            name (str, optional): Description for debugging purposes

        Returns:
            Component: dummy component. When passed as an input and output to a Gradio Event, returning !input will trigger the wrapped functions
        '''
        assert gr.context.Context.block is not None, "wrap_func must be called within a 'gr.Blocks' 'with' context"

        def pre_func_wrapper(relay_toggle: bool, *pre_inputs):
            pre_inputs = list(pre_inputs)
            outputs = pre_fn(*pre_inputs)
            return [not relay_toggle] + EventWrapper.as_list(outputs)

        def call_func_wrapper(relay_toggle: bool, *call_inputs):
            call_inputs = list(call_inputs)
            outputs = fn(*call_inputs)
            return [not relay_toggle] + EventWrapper.as_list(outputs)

        def post_func_wrapper(*post_inputs):
            post_inputs = list(post_inputs)
            outputs = post_fn(*post_inputs)
            return EventWrapper.as_list(outputs)

        post_relay: EventRelay = EventRelay.create_relay(
            fn=post_func_wrapper, inputs=post_inputs, outputs=post_outputs, name=f"post_{name}_relay")

        call_inputs = [post_relay] + (inputs or [])
        call_outputs = [post_relay] + (outputs or [])
        call_relay: EventRelay = EventRelay.create_relay(
            fn=call_func_wrapper, inputs=call_inputs, outputs=call_outputs, name=f"call_{name}_relay", elem_id=elem_id, **kwargs)

        pre_inputs = [call_relay] + (pre_inputs or [])
        pre_outputs = [call_relay] + (pre_outputs or [])
        pre_relay: EventRelay = EventRelay.create_relay(
            fn=pre_func_wrapper, inputs=pre_inputs, outputs=pre_outputs, name=f"pre_{name}_relay")

        return pre_relay

    @classmethod
    def as_list(cls, obj):
        if isinstance(obj, tuple):
            return list(obj)
        if isinstance(obj, list):
            return obj
        return [obj]
