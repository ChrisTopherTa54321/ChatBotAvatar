from __future__ import annotations
from dataclasses import dataclass
from typing import Any, List, Tuple

import gradio as gr
from gradio.components import Component

from chat import Chat
from ui_backends.gradio_backend.component import GradioComponent
from ui_backends.gradio_backend.utils.event_wrapper import EventWrapper
from utils.chat_factory import ChatFactory


class ChatBox(GradioComponent):
    @dataclass
    class StateData:
        chat: Chat = None

    def __init__(self):
        self._ui_chatbot: gr.Chatbot = None

        self._ui_chat_input: gr.Textbox = None
        self._ui_last_output: gr.Textbox = None
        self._ui_submit_btn: gr.Button = None
        self._ui_clear_btn: gr.Button = None
        self._ui_undo_btn: gr.Button = None
        self._ui_retry_btn: gr.Button = None
        self._ui_state: gr.State = None

        self._build_component()

    def _build_component(self):
        self._ui_state = gr.State(value=ChatBox.StateData)
        self._ui_chatbot = gr.Chatbot()
        with gr.Row():
            with gr.Column(scale=2):
                with gr.Row():
                    self._ui_chat_input = gr.Textbox(
                        show_label=False, placeholder="Enter text and press enter", ).style(container=False)
                with gr.Row():
                    self._ui_last_output = gr.Textbox(
                        show_label=False, placeholder="Most recent chat output", visible=False)
            with gr.Column(scale=1):
                self._ui_submit_btn = gr.Button("Submit", variant="primary")
                self._ui_clear_btn = gr.Button("Clear")
                with gr.Row():
                    self._ui_retry_btn = gr.Button("Retry Last")
                    self._ui_undo_btn = gr.Button("Remove Last")

   # Connect the interface components
        submit_inputs: List[Component] = [self._ui_chat_input, self.instance_data]
        submit_outputs: List[Any] = [self._ui_chatbot, self._ui_last_output]

        submit_prompt_wrapper = EventWrapper.create_wrapper(fn=self._submitText, inputs=submit_inputs, outputs=submit_outputs,
                                                            pre_fn=lambda: 4*(gr.update(interactive=False),), pre_outputs=[self._ui_submit_btn, self._ui_clear_btn, self._ui_retry_btn, self._ui_undo_btn],
                                                            post_fn=lambda: 4*(gr.update(interactive=True), ), post_outputs=[self._ui_submit_btn, self._ui_clear_btn, self._ui_retry_btn, self._ui_undo_btn])

        self._ui_submit_btn.click(**EventWrapper.get_event_args(submit_prompt_wrapper))
        self._ui_chat_input.submit(**EventWrapper.get_event_args(submit_prompt_wrapper))

        clear_list: List[Component] = [self._ui_chat_input, self._ui_last_output]
        self._ui_clear_btn.click(fn=self._handleClearClick, inputs=[
                                 self.instance_data] + clear_list, outputs=[self._ui_chatbot] + clear_list)

        self._ui_undo_btn.click(fn=self._handle_undo_click, inputs=[self.instance_data], outputs=self._ui_chatbot)
        self._ui_retry_btn.click(fn=self._handle_retry_click, inputs=[self.instance_data], outputs=[
                                 self._ui_chatbot, self._ui_last_output])

    def _handle_undo_click(self, chat_data: ChatBox.StateData) -> Tuple[str, str]:
        chat_data.chat.pop_history_item(-1)
        return ChatBox._chat_to_chatbot(chat_data.chat.get_history())

    def _handle_retry_click(self, chat_data: ChatBox.StateData) -> Tuple[str, str]:
        last_response = chat_data.chat.pop_history_item(-1)
        last_input = chat_data.chat.pop_history_item(-1)
        new_response = chat_data.chat.send_text(last_input[1])

        updated_history = chat_data.chat.get_history()
        chat_output = ChatBox._chat_to_chatbot(updated_history)

        return chat_output, new_response

    def _handleClearClick(self, chat_data: ChatBox.StateData, *args):
        '''
        Clears chat and components.

        Args:
            chat_data (ChatBox.StateData): instance data
            *args (List[Components]): List of components to clear

        '''
        if not chat_data.chat:
            chat_data.chat = ChatFactory.get_default_chat()
        chat_data.chat.reset()
        return [None, None] + len(args)*[None]

    def _submitText(self, input_text: str, chat_data: ChatBox.StateData) -> Tuple[Tuple[str, str], str]:
        if not chat_data.chat:
            chat_data.chat = ChatFactory.get_default_chat()

        response = chat_data.chat.send_text(input_text)
        history = chat_data.chat.get_history()
        chat_output = ChatBox._chat_to_chatbot(history)

        return chat_output, response

    @classmethod
    def _chat_to_chatbot(cls, chat_history: List[Tuple[str, str]]) -> Tuple[str, str]:
        # Convert to Gradio's (user, ai) format
        chat_output: List[Tuple[str, str]] = []
        for role, response in chat_history:
            msg = f"{role.upper()}: {response}"
            if role == Chat.Roles.AI:
                chat_output.append((None, msg))
            elif role == Chat.Roles.USER:
                chat_output.append((msg, None))
            elif role == Chat.Roles.SYSTEM:
                chat_output.append((msg, None))
        return chat_output

    @property
    def instance_data(self) -> gr.State:
        return self._ui_state

    @property
    def chat_response(self) -> gr.Textbox:
        return self._ui_last_output
