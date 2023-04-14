''' Wraps a Gradio event with pre- and post- events '''
from __future__ import annotations

import logging
import traceback
from dataclasses import dataclass
from functools import partial
from typing import Any, Callable, Dict, List

import gradio as gr
from gradio.components import Component

from ui_backends.gradio_backend.utils.event_relay import EventRelay
from utils.stack_info import get_caller

logger = logging.getLogger(__file__)


class EventWrapper():
    # Sometimes to trick gradio into behaving we need placeholder inputs or outputs. Share fake_relay for this.
    fake_relay: EventRelay = None

    @dataclass
    class WrappedFunc:
        func: Callable = None
        inputs: List[Component] = None
        outputs: List[Component] = None
        kwargs: Dict[str, Any] = None
        elem_id: str = None
        pre_delay: int = 0

    @classmethod
    def create_wrapper_list(cls, wrapped_func_list: List[EventWrapper.WrappedFunc], name: str = None) -> Component:
        assert gr.context.Context.block is not None, "wrap_func must be called within a 'gr.Blocks' 'with' context"

        if EventWrapper.fake_relay is None:
            EventWrapper.fake_relay = EventRelay.create_relay()

        caller_info = get_caller(exclude_func_prefixes=["event_"])
        if name is None:
            name = caller_info

        # Iterate over the functions, creating relays to run the function and then toggle the next function...
        next_relay: Component = EventWrapper.fake_relay

        def func_wrapper(func: EventWrapper.WrappedFunc, dummy, relay_toggle: bool, *wrapped_inputs):
            wrapped_inputs = list(wrapped_inputs)
            try:
                wrapped_func_outputs = func.func(*wrapped_inputs) if func.func else []
            except Exception as e:
                wrapped_func_outputs = [gr.update() for _ in func.outputs]
                traceback.print_exception(e)
                logger.error(f"{name} {caller_info}: {e}")
            return [dummy, not relay_toggle] + EventRelay.as_list(wrapped_func_outputs)

        for idx, func in enumerate(reversed(wrapped_func_list)):
            func_inputs = [EventWrapper.fake_relay, next_relay] + EventRelay.as_list(func.inputs)
            func_outputs = [EventWrapper.fake_relay, next_relay] + EventRelay.as_list(func.outputs)

            func_relay: Component = EventRelay.create_relay(fn=partial(func_wrapper, func), inputs=func_inputs,
                                                            outputs=func_outputs, name=f"{name}_func{len(wrapped_func_list)-idx}")
            next_relay = func_relay

            # TODO: Make this a single count down textbox?
            for i in range(func.pre_delay):
                next_relay = EventRelay.create_relay(fn=lambda dummy, relay: (dummy, not relay),
                                                     inputs=[EventWrapper.fake_relay, next_relay], outputs=[EventWrapper.fake_relay, next_relay])

        return next_relay

    @classmethod
    def create_wrapper(cls,
                       fn: Callable = None, inputs: List[Component] = None, outputs: List[Component] = None,
                       pre_fn: Callable = None, pre_inputs: List[Component] = None, pre_outputs: List[Component] = None, pre_kwargs: Dict[str, Any] = None,
                       post_fn: Callable = None, post_inputs: List[Component] = None, post_outputs: List[Component] = None, post_kwargs: Dict[str, Any] = None,
                       pre_fn_delay: int = 0, fn_delay: int = 0, post_fn_delay: int = 0,
                       elem_id: str = None, name: str = None, **kwargs) -> Component:
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
            pre_fn_delay (int, optional): number of extra hops to insert before calling pre_fn
            fn_delay (int, optional): number of extra hops to insert between pre_fn and fn
            post_fn_delay (int, optional): number of extra hops to insert between fn and post_fn
            elem_id (str, optional): Element Id to give the primary function call's dummy object.
            name (str, optional): Description for debugging purposes

        Returns:
            Component: dummy component. When passed as an input and output to a Gradio Event, returning !input will trigger the wrapped functions
        '''

        wrapped_funcs: List[EventWrapper.WrappedFunc] = []
        wrapped_funcs.append(EventWrapper.WrappedFunc(func=pre_fn, inputs=pre_inputs,
                             outputs=pre_outputs, kwargs=pre_kwargs, pre_delay=pre_fn_delay))
        wrapped_funcs.append(EventWrapper.WrappedFunc(func=fn, inputs=inputs,
                             outputs=outputs, kwargs=kwargs, pre_delay=fn_delay, elem_id=elem_id))
        wrapped_funcs.append(EventWrapper.WrappedFunc(func=post_fn, inputs=post_inputs,
                             outputs=post_outputs, kwargs=post_kwargs, pre_delay=post_fn_delay))
        return EventWrapper.create_wrapper_list(wrapped_func_list=wrapped_funcs, name=name)

    @classmethod
    def get_event_args(cls, wrapper: Component) -> Dict[str, Any]:
        return {"fn": lambda x: not x,
                "inputs": [wrapper],
                "outputs": [wrapper]
                }
