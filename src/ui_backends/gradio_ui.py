''' Gradio backend for a user interface '''
import glob
import logging
import os
import pathlib
from typing import List, Dict

import gradio as gr
import numpy as np
from typing_extensions import override

from chat import Chat
from tts import Tts
from ui import Ui
from ui_backends.gradio_backend.tab import GradioTab
from ui_backends.gradio_backend.tabs.chat_tab import ChatTab
from ui_backends.gradio_backend.tabs.avatar_tab import AvatarTab
from avatar.manager import Manager
from utils.tts_queue import TtsQueue

logger = logging.getLogger(__file__)

script_dir = pathlib.Path(__file__).parent.resolve()
gradio_dir = os.path.join(script_dir, "gradio_backend")


class GradioUi(Ui):
    def __init__(self, chat_interface: Chat, tts_interface: Tts, avatar_manager: Manager, jobs: int = 3):
        self._app: gr.Blocks = None
        self._chat: Chat = chat_interface
        self._tts: Tts = tts_interface
        self._tts_queue: TtsQueue = TtsQueue(self._tts)
        self._job_cnt_arg = jobs

        self._chat_tab: ChatTab = ChatTab(chat_interface=self._chat, tts_interface=self._tts, tts_queue=self._tts_queue)
        self._avatar_tab: AvatarTab = AvatarTab(avatar_manager=avatar_manager)

        self._tabs: Dict[str, GradioTab] = {"Chat": self._chat_tab, "Avatars": self._avatar_tab}

        self._buildInterface()
        self._injectScripts(glob.glob(os.path.join(gradio_dir, "js", "*.js")))

    def _buildInterface(self):
        with gr.Blocks(analytics_enabled=False) as app:
            for name, tab in self._tabs.items():
                with gr.Tab(name):
                    tab.build_ui()
        self._app = app

    @override
    def launch(self, listen: bool, port: int):
        ''' Launches the UI and blocks until complete '''
        if self._job_cnt_arg > 1:
            self._app.queue(concurrency_count=self._job_cnt_arg)

        server_name = "0.0.0.0" if listen else None
        self._app.launch(server_name=server_name, server_port=port)

    def _injectScripts(self, pathList: List[str]):
        # Taken from AUTOMATIC1111 stable-diffusion-webui
        contents: str = ""
        for script in pathList:
            with open(script, "r", encoding="utf8") as file:
                contents += file.read()

        import gradio.routes

        def template_response(*args, **kwargs):
            res = gradio_routes_templates_response(*args, **kwargs)
            res.body = res.body.replace(b'</head>', f'<script>{contents}</script></head>'.encode("utf8"))
            res.init_headers()
            return res

        gradio_routes_templates_response = gradio.routes.templates.TemplateResponse
        gradio.routes.templates.TemplateResponse = template_response
