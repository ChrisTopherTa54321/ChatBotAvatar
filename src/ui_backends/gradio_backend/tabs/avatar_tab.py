''' Avatar interface tab '''
import logging
from typing import List, Tuple
from ui_backends.gradio_backend.tab import GradioTab
import gradio as gr

from typing_extensions import override

logger = logging.getLogger(__file__)


class AvatarTab(GradioTab):
    def __init__(self):
        self._btn: gr.Button = None

    @override
    def build_ui(self):
        self._btn = gr.Button("Test")
