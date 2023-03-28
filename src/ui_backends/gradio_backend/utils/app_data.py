''' Shared Gradio app data '''
from __future__ import annotations
from dataclasses import dataclass
from utils.shared import Shared
import gradio as gr


@dataclass
class AppData:
    app: gr.Blocks = None

    @classmethod
    def get_instance(cls) -> AppData:
        return Shared.getInstance().get_data(gr, AppData)
