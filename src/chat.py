''' Interface for a Chat backend '''
import abc
from typing import Optional, Tuple, List


class Chat(abc.ABC):
    class Roles:
        SYSTEM = "system"
        USER = "user"
        AI = "ai"

    def send_text(self, text: str) -> Optional[str]:
        '''
        Sends a prompt and returns the reply

        Args:
            text (str): the entire prompt to send to the chat interface

        Returns:
            Optional[str]: the chat interface's response
        '''
        pass

    def get_history(self) -> List[Tuple[str, str]]:
        '''
        Returns the complete chat history

        Returns:
            List[Tuple[str, str]]: List of (role, message) pairs
        '''
        raise NotImplementedError()

    def reset(self) -> None:
        '''
        Resets chat to its initial state
        '''
        raise NotImplementedError()
