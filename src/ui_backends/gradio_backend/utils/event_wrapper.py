''' Wraps a Gradio event with pre- and post- events '''
from __future__ import annotations

import logging
import traceback
from typing import Any, Callable, Dict, List

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

        def pre_func_wrapper(relay_toggle: bool, *wrapped_pre_inputs):
            wrapped_pre_inputs = list(wrapped_pre_inputs)
            try:
                func_outputs = pre_fn(*wrapped_pre_inputs) if pre_fn else []
            except Exception as e:
                func_outputs = [None]*len(EventRelay.as_list(pre_outputs))
                traceback.print_exception(e)
                logger.error(e)

            return [not relay_toggle] + EventRelay.as_list(func_outputs)

        def call_func_wrapper(relay_toggle: bool, *wrapped_call_inputs):
            wrapped_call_inputs = list(wrapped_call_inputs)
            try:
                func_outputs = fn(*wrapped_call_inputs) if fn else []
            except Exception as e:
                func_outputs = [None]*len(EventRelay.as_list(outputs))
                traceback.print_exception(e)
                logger.error(e)

            return [not relay_toggle] + EventRelay.as_list(func_outputs)

        def post_func_wrapper(relay_toggle: bool, *wrapped_post_inputs):
            wrapped_post_inputs = list(wrapped_post_inputs)
            try:
                func_outputs = post_fn(*wrapped_post_inputs) if post_fn else []
            except Exception as e:
                func_outputs = [None]*len(EventRelay.as_list(post_outputs))
                traceback.print_exception(e)
                logger.error(e)

            return [relay_toggle] + EventRelay.as_list(func_outputs)

        # I don't know why this is needed, but if post_func_wrapper() doesn't have an output then Gradio calls it infinitely,
        # so we'll just stick a dummy component at the end of the list
        fake_relay: EventRelay = EventRelay.create_relay()

        post_inputs = [fake_relay] + EventRelay.as_list(post_inputs)
        post_outputs = [fake_relay] + EventRelay.as_list(post_outputs)
        post_relay: EventRelay = EventRelay.create_relay(
            fn=post_func_wrapper, inputs=post_inputs, outputs=post_outputs, name=f"post_{name}_relay")

        call_inputs = [post_relay] + EventRelay.as_list(inputs)
        call_outputs = [post_relay] + EventRelay.as_list(outputs)
        call_relay: EventRelay = EventRelay.create_relay(
            fn=call_func_wrapper, inputs=call_inputs, outputs=call_outputs, name=f"call_{name}_relay", elem_id=elem_id, **kwargs)

        pre_inputs = [call_relay] + EventRelay.as_list(pre_inputs)
        pre_outputs = [call_relay] + EventRelay.as_list(pre_outputs)
        pre_relay: EventRelay = EventRelay.create_relay(
            fn=pre_func_wrapper, inputs=pre_inputs, outputs=pre_outputs, name=f"pre_{name}_relay")

        return pre_relay

    @classmethod
    def get_event_args(cls, wrapper: Component) -> Dict[str, Any]:
        return {"fn": lambda x: not x,
                "inputs": [wrapper],
                "outputs": [wrapper]
                }
