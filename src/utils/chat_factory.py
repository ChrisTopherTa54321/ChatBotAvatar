''' Handles creating Chat instances '''
from typing import Callable, Dict, Any, Optional
from chat import Chat
from dataclasses import dataclass
# TODO: Deal with same name in different backends


class ChatFactory:
    @dataclass
    class ChatInfo:
        gen: Callable = None
    _chat_map: Dict[str, ChatInfo] = {}
    _default_chat: ChatInfo = None

    @classmethod
    def register_chat(cls, name: str, create_chat_func: Callable):
        '''
        Registers a new chat backend.

        Args:
            name (str): name of the chat backend
            create_chat_func (Callable): a Callable which returns a new instance of the Chat
        '''
        cls._chat_map.setdefault(name, ChatFactory.ChatInfo()).gen = create_chat_func

    @classmethod
    def get_chat_list(cls):
        return sorted(cls._chat_map.keys())

    @classmethod
    def set_default_chat(cls, name: str):
        cls._default_chat = cls._chat_map[name]

    @classmethod
    def get_default_chat(cls) -> Chat:
        if cls._default_chat is None and cls._chat_map:
            cls._default_chat = next(iter(cls._chat_map.values()))
        return cls._default_chat.gen()
