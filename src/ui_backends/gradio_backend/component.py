''' Interface for a gradio component'''
import abc
from abc import abstractmethod
import gradio as gr
from typing import Any, List, Tuple
from gradio.components import Component


class GradioComponent(abc.ABC):
    pass
