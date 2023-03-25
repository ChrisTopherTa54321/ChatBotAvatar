''' Avatar interface tab '''
import logging
from typing import List, Tuple


import gradio as gr
import numpy as np
from typing_extensions import override

from avatar.manager import Manager, Profile
from ui_backends.gradio_backend.tab import GradioTab
from ui_backends.gradio_backend.components.avatar_editor import AvatarEditor
from utils.shared import Shared
from utils.image_utils import ImageUtils
import os

logger = logging.getLogger(__file__)


class AvatarTab(GradioTab):
    PREVIEW_IMAGE_COLUMN_CNT = 8

    def __init__(self):
        self._manager: Manager = Shared.getInstance().avatar_manager
        self._ui_refresh_btn: gr.Button = None
        self._ui_avatar_list_gallery: gr.Gallery = None
        self._ui_avatar_editor: AvatarEditor = None
        self._ui_new_btn: gr.Button = None

    @override
    def build_ui(self):
        with gr.Row():
            self._ui_avatar_list_gallery = gr.Gallery(show_label=False, elem_id="avatar_list_gallery").style(
                grid=AvatarTab.PREVIEW_IMAGE_COLUMN_CNT, preview=False)
        with gr.Row():
            self._ui_refresh_btn = gr.Button("Refresh Avatar List")
            self._ui_new_btn = gr.Button("Create New Avatar")
        with gr.Row():
            self._ui_avatar_editor = AvatarEditor()
            self._ui_avatar_editor.build_component()

        hidden_name_box: gr.Textbox = gr.Textbox(visible=False)
        self._ui_new_btn.click(fn=self._handle_new_avatar_clicked,
                               _js='prompt_for_name', inputs=[hidden_name_box], outputs=[hidden_name_box])
        self._ui_refresh_btn.click(fn=self._handle_refresh_clicked, inputs=[], outputs=[self._ui_avatar_list_gallery])
        self._ui_avatar_list_gallery.select(fn=self._handle_avatar_list_selection, inputs=[self._ui_avatar_editor.get_update_trigger()], outputs=[
                                            self._ui_avatar_editor.get_update_trigger()])

    def _handle_new_avatar_clicked(self, new_name: str):
        logger.info(f"Create new avatar: {new_name}")
        profile: Profile = self._manager.create_new_profile(profile_path=new_name)

    def _handle_refresh_clicked(self) -> Tuple[gr.Gallery]:
        ''' Refresh the gallery when the Refresh button is clicked'''
        self._manager.refresh()
        images = [[ImageUtils.open_or_blank(profile.preview_image_path), profile.name]
                  for profile in self._manager.list_avatars()]
        return images

    def _handle_avatar_list_selection(self, event_data: gr.SelectData, update_trigger: bool) -> Tuple[None]:
        ''' Handles an avatar being selected from the list gallery '''
        self._manager.active_profile = self._manager.list_avatars()[event_data.index]
        self._ui_avatar_editor.load_profile(self._manager.active_profile)
        return (not update_trigger)
