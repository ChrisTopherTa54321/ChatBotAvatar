''' Interface for a UI backend '''
from __future__ import annotations
import abc
from abc import abstractmethod


class Ui(abc.ABC):
    '''
    An instance of a UI backend
    '''
    @abstractmethod
    def launch(self, listen: bool, port: int) -> None:
        '''
        Launches the user interface

        Args:
            listen (bool): If true allow connections from other hosts
            port (int): port to listen on
        '''
        pass
