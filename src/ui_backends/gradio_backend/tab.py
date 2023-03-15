''' Interface for a gradio backend tab '''
import abc
from abc import abstractmethod


class GradioTab(abc.ABC):
    @abstractmethod
    def build_ui(self):
        '''
        Build the gradio user interface
        '''
        pass
