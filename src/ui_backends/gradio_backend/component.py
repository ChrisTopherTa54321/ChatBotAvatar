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
        Build the gradio user interface
        '''
        pass

    @abstractmethod
    def add_inputs(self, inputs: List[Component]) -> List[Component]:
        '''
        If using this component in a gradio event use this function to
        add the necessary inputs to the event handler's Input list. On the
        handler side use 'consume_inputs' to remove the additional inputs

        Returns:
            List[Component]: new input list with any additional components added
        '''
        return inputs

    @abstractmethod
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
