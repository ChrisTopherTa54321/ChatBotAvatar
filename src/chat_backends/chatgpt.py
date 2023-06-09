''' ChatGPT interface '''
import os
import openai
import re
from typing import List, Dict, Tuple, Optional
from typing_extensions import override
import logging
from dataclasses import dataclass

from chat import Chat
from utils.text_utils import TextUtils
logger = logging.getLogger(__file__)


class ChatGpt(Chat):
    BACKEND_NAME: str = "ChatGpt"

    disclaimerRe: re.Pattern = re.compile(r'(disclaimer.*?\n+)', re.IGNORECASE)
    ROLE_MAP: Dict[str, str] = {Chat.Roles.SYSTEM: "system", Chat.Roles.USER: "user", Chat.Roles.AI: "assistant"}

    @dataclass
    class HistoryItem:
        role: str = None
        message: str = None

        def asChatGpt(self) -> Dict[str, str]:
            ''' returns HistoryItem as a ChatGpt item '''
            return {"role": ChatGpt.ROLE_MAP[self.role.lower()],
                    "content": self.message}

        def __post_init__(self):
            # An unknown speaker is probably just a colon in the prompt... assign it to user
            if self.role not in ChatGpt.ROLE_MAP:
                self.message = f"{self.role}: {self.message}"
                self.role = ChatGpt.Roles.USER

    def __init__(self, api_key: str, chat_model: str = "gpt-3.5-turbo", initial_instructions: Optional[str] = None):
        super().__init__()
        openai.api_key = api_key
        self._model: str = chat_model
        self._role: str = Chat.Roles.USER
        self._history: List[ChatGpt.HistoryItem] = []

        if initial_instructions:
            self._history.append(ChatGpt.HistoryItem(role=Chat.Roles.SYSTEM, message=initial_instructions))

    @override
    def reset(self):
        role = self._history.pop(0)
        self._history.clear()
        self._history.append(role)

    @override
    def pop_history_item(self, idx: int) -> Tuple[str, str]:
        item = self._history.pop(idx)
        return (item.role, item.message)

    @override
    def send_text(self, text: str) -> str:
        message_list = TextUtils.split_speakers(text, initial_speaker=Chat.Roles.USER)
        has_user = False
        for speaker, msg in message_list:
            if speaker == Chat.Roles.USER:
                has_user = True
            self._history.append(ChatGpt.HistoryItem(role=speaker, message=msg))

        converted_msgs = [item.asChatGpt() for item in self._history]

        if not has_user:
            return ""

        completion = openai.ChatCompletion.create(model=self._model, messages=converted_msgs)

        response = completion.choices[0].message.content
        response = self.preProc(response)

        self._history.append(ChatGpt.HistoryItem(role=Chat.Roles.AI, message=response))
        logger.info(f"ChatGPT response: {response}")
        return response

    def preProc(self, text: str) -> str:
        '''
        run any preprocessing on the string returned by the AI

        Args:
            text (str): string to process

        Returns:
            str: preprocessed text
        '''
        text = ChatGpt.disclaimerRe.sub('', text)
        return text

    @override
    def get_history(self) -> List[Tuple[str, str]]:
        return [(item.role, item.message) for item in self._history]
