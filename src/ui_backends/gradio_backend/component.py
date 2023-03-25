''' Interface for a gradio component'''
import abc
from abc import abstractmethod
import gradio as gr
from typing import Any, List, Tuple
from gradio.components import Component


class GradioComponent(abc.ABC):

    @abstractmethod
    def build_component(self) -> Component:
        '''
        Build the gradio user interface.
        '''
        pass

    def add_inputs(self, inputs: List[Component]) -> List[Component]:
        '''
        If using this component in a gradio event use this function to
        add the necessary inputs to the event handler's Input list. On the
        handler side use 'consume_inputs' to remove the additional inputs

        Returns:
            List[Component]: new input list with any additional components added
        '''
        return inputs

    def consume_inputs(self, inputs: List[Any]) -> Tuple[List[Any], List[Any]]:
        '''
        Opposite of add_inputs, this takes the Inputs received by the callback
        and removes the ones added by get_inputs

        Args:
            inputs (List[Any]): list of inputs passed to the callback

        Returns:
            Tuple[List[Any],List[Any]]: returns a tuple of
                (args remaining, args consumed)
        '''
        return inputs

    def add_outputs(self, outputs: List[Component]) -> List[Component]:
        '''
        If using this component in a gradio event use this function to
        add the necessary outputs to the event handler's Output list. On
        the handler side use 'add_handler_outputs' to add the needed
        additional outputs to the handler side
        '''
        return outputs

    def add_handler_outputs(self, outputs: List[Any], trigger_update: bool = False) -> Tuple[List[Any], List[Any]]:
        '''
        Opposite of add_outputs, this adds in the outputs the handler must return for this component.

        Args:
            consumed_inputs (List[Any]): consumed inputs returned from consume_inputs
            outputs (List[Any]): original list of outputs from the handler
            trigger_update (bool, optional): If True, triggers the components 'update' function

        Returns:
            Tuple[List[Any], List[Any]]: Tuple of (new output list, newly added outputs)
        '''
        pass
