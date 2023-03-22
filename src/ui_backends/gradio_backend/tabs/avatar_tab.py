''' Avatar interface tab '''
import logging
from typing import List, Tuple
import uuid

from utils.shared import Shared

import gradio as gr
from typing_extensions import override

from avatar.manager import Manager
from ui_backends.gradio_backend.tab import GradioTab

logger = logging.getLogger(__file__)


class AvatarTab(GradioTab):
    PREVIEW_IMAGE_COLUMN_CNT = 8

    def __init__(self, avatar_manager: Manager):
        self._manager: Manager = avatar_manager
        self._ui_refresh_btn: gr.Button = None
        self._ui_avatar_list_gallery: gr.Gallery = None

    @override
    def build_ui(self):
        self._ui_refresh_btn = gr.Button("Refresh")
        self._ui_avatar_list_gallery = gr.Gallery(show_label=False, elem_id="avatar_list_gallery").style(
            grid=AvatarTab.PREVIEW_IMAGE_COLUMN_CNT, preview=False)

        self._ui_refresh_btn.click(fn=self._handle_refresh_clicked, inputs=[], outputs=[self._ui_avatar_list_gallery])
        self._ui_avatar_list_gallery.select(fn=self._handle_avatar_list_selection, inputs=[], outputs=[])

    def _handle_refresh_clicked(self) -> Tuple[gr.Gallery]:
        ''' Refresh the gallery when the Refresh button is clicked'''
        self._manager.refresh()
        images = [(profile.preview_image, profile.name) for profile in self._manager.list_avatars()]
        return images

    def _handle_avatar_list_selection(self, event_data: gr.SelectData, *args, **kwargs) -> Tuple[None]:
        ''' Handles an avatar being selected from the list gallery '''
        self._manager.active_profile = self._manager.list_avatars()[event_data.index]
        return ()
