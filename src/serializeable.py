''' Serializable Data'''
from __future__ import annotations
import abc
from abc import abstractmethod
from typing import Optional, Tuple, List, Optional, Dict, Any
import numpy as np


class Serializable(abc.ABC):
    '''
    An instance of a Serializable class
    '''

    @abstractmethod
    def from_dict(self, info: Dict[str, Any]) -> Any:
        ''' Returns a new object initialized with info '''
        pass

    @abstractmethod
    def as_dict(self) -> Dict[str, Any]:
        ''' Get a Dict representation of this class '''
        pass
