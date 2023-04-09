''' Avatar interface tab '''
import logging
import os
from dataclasses import dataclass
from typing import List, Tuple

import gradio as gr
import numpy as np
from gradio.components import Component
from typing_extensions import override

from avatar.manager import Manager, Profile
from ui_backends.gradio_backend.components.avatar_editor import AvatarEditor
from ui_backends.gradio_backend.tab import GradioTab
from ui_backends.gradio_backend.utils.app_data import AppData
from ui_backends.gradio_backend.utils.event_wrapper import EventWrapper
from utils.shared import Shared

logger = logging.getLogger(__file__)


class AvatarTab(GradioTab):
    PREVIEW_IMAGE_COLUMN_CNT = 8

    @dataclass
    class StateData:
        profile: Profile = None

    def __init__(self):
        self._manager: Manager = Shared.getInstance().avatar_manager
        self._ui_refresh_btn: gr.Button = None
        self._ui_avatar_list_gallery: gr.Gallery = None
        self._ui_avatar_editor: AvatarEditor = None
        self._ui_new_btn: gr.Button = None
        self._ui_del_btn: gr.Button = None
        self._ui_refresh_relay: EventWrapper = None
        self._ui_state: gr.State = None

    @override
    def build_ui(self):
        with gr.Row():
            self._ui_avatar_list_gallery = gr.Gallery(show_label=False, elem_id="avatar_list_gallery").style(
                grid=AvatarTab.PREVIEW_IMAGE_COLUMN_CNT, preview=False)
        with gr.Row():
            self._ui_refresh_btn = gr.Button("Refresh Avatar List")
            self._ui_new_btn = gr.Button("Create New Avatar")
            self._ui_del_btn = gr.Button("Delete Avatar")
        with gr.Row():
            self._ui_avatar_editor = AvatarEditor()

        self._ui_state = gr.State(value=AvatarTab.StateData)

        self._ui_refresh_relay = EventWrapper.create_wrapper(
            fn=self._handle_refresh, outputs=[self._ui_avatar_list_gallery])

        # The final 'input' disappears somewhere on the way through _js ton to _handle_new_avatar_clicked, so make it a dummy
        dummy_component: gr.Textbox = gr.Textbox(visible=False)
        self._ui_new_btn.click(fn=self._handle_new_avatar_clicked,
                               _js='prompt_for_name', inputs=[self._ui_refresh_relay, dummy_component],
                               outputs=[self._ui_refresh_relay])

        delete_relay = EventWrapper.create_wrapper(fn=self._handle_delete,
                                                   inputs=[self.instance_data, self._ui_refresh_relay],
                                                   outputs=[self._ui_refresh_relay])

        self._ui_del_btn.click(fn=None, _js="relay_confirm_prompt",
                               inputs=[delete_relay], outputs=[delete_relay])
        self._ui_refresh_btn.click(**EventWrapper.get_event_args(self._ui_refresh_relay))
        self._ui_avatar_list_gallery.select(fn=self._handle_avatar_list_selection,
                                            inputs=[self._ui_avatar_editor.update_ui_relay,
                                                    self._ui_avatar_editor.instance_data, self._ui_state, self._ui_refresh_relay],
                                            outputs=[self._ui_avatar_editor.update_ui_relay, self._ui_refresh_relay])

        AppData.get_instance().app.load(**EventWrapper.get_event_args(self._ui_refresh_relay))

    def _handle_new_avatar_clicked(self, new_name: str, refresh_relay: bool):
        logger.info(f"Create new avatar: {new_name}")
        self._manager.create_new_profile(profile_name=new_name)
        return not refresh_relay

    def _handle_delete(self, inst_data, refresh_relay: bool):
        self._manager.delete_profile(inst_data.profile)
        inst_data.profile = None
        self._manager.refresh()
        return not refresh_relay

    def _handle_refresh(self) -> Tuple[gr.Gallery]:
        ''' Refresh the gallery '''
        self._manager.refresh()

        images = [(profile.preview_image, profile.friendly_name)
                  for profile in self._manager.list_avatars()]
        return [images]

    def _handle_avatar_list_selection(self, event_data: gr.SelectData, update_trigger: bool, editor_instance_data: AvatarEditor.StateData, inst_data: StateData, refresh_relay: bool) -> Tuple[None]:
        ''' Handles an avatar being selected from the list gallery '''
        inst_data.profile = self._manager.list_avatars()[event_data.index]
        editor_instance_data.profile = inst_data.profile
        return (not update_trigger, not refresh_relay)

    @property
    def instance_data(self) -> gr.State:
        return self._ui_state
