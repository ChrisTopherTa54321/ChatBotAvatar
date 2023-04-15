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
    error_cnt: int = 0

    @dataclass
    class WrappedFunc:
        fn: Callable = None
        inputs: List[Component] = None
        outputs: List[Component] = None
        kwargs: Dict[str, Any] = None
        elem_id: str = None
        pre_delay: int = 0

        def __post_init__(self):
            self.inputs = self.inputs or []
            self.outputs = self.outputs or []
            self.kwargs = self.kwargs or {}

    @classmethod
    def create_wrapper_list(cls, wrapped_func_list: List[EventWrapper.WrappedFunc], error_func: EventWrapper.WrappedFunc = None,
                            finally_func: EventWrapper.WrappedFunc = None, name: str = None) -> Component:
        '''
        Creates an EventWrapper which executes a list of functions

        Args:
            wrapped_func_list (List[EventWrapper.WrappedFunc]): list of wrapped functions for this wrapper to execute
            error_func (EventWrapper.WrappedFunc, optional): function to call if a function throws an exception
            finally_func (EventWrapper.WrappedFunc, optional): clean up function, always called last even in error case
            name (str, optional): debug name for this wrapper

        Returns:
            Component: _description_
        '''
        assert gr.context.Context.block is not None, "wrap_func must be called within a 'gr.Blocks' 'with' context"

        if EventWrapper.fake_relay is None:
            EventWrapper.fake_relay = EventRelay.create_relay()

        caller_info = get_caller(exclude_func_prefixes=["event_"])
        if name is None:
            name = caller_info

        # Define a 'finally function' which always runs at the end of a wrapper. Useful for clean-up like re-enabling buttons
        if finally_func is not None:
            # Just put it on the end of the function list, then set up a handler to call it on the error path
            wrapped_func_list.append(finally_func)

            func_inputs = [EventWrapper.fake_relay, EventWrapper.fake_relay] + EventRelay.as_list(finally_func.inputs)
            func_outputs = [EventWrapper.fake_relay, EventWrapper.fake_relay] + EventRelay.as_list(finally_func.outputs)

            def finally_func_wrapper(func: EventWrapper.WrappedFunc, dummy1, dummy2, *input_args):
                # No error handling here. What would clean up the clean up function?
                finally_func_outputs = func.fn(*input_args, **func.kwargs) if func.fn else []
                return [dummy1, dummy2] + EventRelay.as_list(finally_func_outputs)
            error_finally_relay: Component = EventRelay.create_relay(fn=partial(finally_func_wrapper, finally_func), inputs=func_inputs,
                                                                     outputs=func_outputs, name=f"{name}_finally_func", **finally_func.kwargs)
        else:
            error_finally_relay = EventWrapper.fake_relay

        # Define an error handler function which updates the error message and triggers the 'finally' function

        error_txt_relay = gr.Textbox("", visible=False, label="Error Message")
        if error_func is None:
            error_func = EventWrapper.WrappedFunc()

        func_inputs = [error_finally_relay, error_txt_relay] + EventRelay.as_list(error_func.inputs)
        func_outputs = [error_finally_relay, error_txt_relay] + EventRelay.as_list(error_func.outputs)

        def error_func_wrapper(func: EventWrapper.WrappedFunc, finally_relay_toggle: bool, error_msg: str, *input_args):
            if error_msg == "":
                return [finally_relay_toggle, gr.Textbox.update(visible=False)] + [gr.update() for _ in func.outputs]
            error_func_outputs = func.fn(*input_args, **func.kwargs) if func.fn else []

            return [not finally_relay_toggle, gr.Textbox.update(visible=True, value=error_msg)] + EventRelay.as_list(error_func_outputs)

        error_txt_relay.change(fn=partial(error_func_wrapper, error_func), inputs=func_inputs, outputs=func_outputs)

        # Iterate over the functions, creating relays to run the function and then toggle the next function...
        next_relay: Component = EventWrapper.fake_relay

        def func_wrapper(func: EventWrapper.WrappedFunc, error_relay: str, relay_toggle: bool, *wrapped_inputs):
            error_relay = ""
            wrapped_inputs = list(wrapped_inputs)
            try:
                wrapped_func_outputs = func.fn(*wrapped_inputs) if func.fn else []
            except Exception as e:
                traceback.print_exception(e)
                EventWrapper.error_cnt += 1  # This ensures repeat errors have unique messages
                error_msg: str = f"{EventWrapper.error_cnt} - {name}: {e}"
                logger.error(error_msg)
                return [error_msg, relay_toggle] + [gr.update() for _ in func.outputs]
            return [error_relay, not relay_toggle] + EventRelay.as_list(wrapped_func_outputs)

        for idx, func in enumerate(reversed(wrapped_func_list)):
            func_inputs = [error_txt_relay, next_relay] + EventRelay.as_list(func.inputs)
            func_outputs = [error_txt_relay, next_relay] + EventRelay.as_list(func.outputs)

            func_relay: Component = EventRelay.create_relay(fn=partial(func_wrapper, func), inputs=func_inputs,
                                                            outputs=func_outputs, name=f"{name}_func{len(wrapped_func_list)-idx}", **func.kwargs)
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
        wrapped_funcs.append(EventWrapper.WrappedFunc(fn=pre_fn, inputs=pre_inputs,
                             outputs=pre_outputs, kwargs=pre_kwargs, pre_delay=pre_fn_delay))
        wrapped_funcs.append(EventWrapper.WrappedFunc(fn=fn, inputs=inputs,
                             outputs=outputs, kwargs=kwargs, pre_delay=fn_delay, elem_id=elem_id))
        wrapped_funcs.append(EventWrapper.WrappedFunc(fn=post_fn, inputs=post_inputs,
                             outputs=post_outputs, kwargs=post_kwargs, pre_delay=post_fn_delay))
        return EventWrapper.create_wrapper_list(wrapped_func_list=wrapped_funcs, name=name)

    @classmethod
    def get_event_args(cls, wrapper: Component) -> Dict[str, Any]:
        return {"fn": lambda x: not x,
                "inputs": [wrapper],
                "outputs": [wrapper]
                }
