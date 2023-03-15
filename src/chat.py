''' Interface for a Chat backend '''
import abc
from abc import abstractmethod
from typing import Optional, Tuple, List


class Chat(abc.ABC):
    class Roles:
        SYSTEM = "system"
        USER = "user"
        AI = "ai"

    @abstractmethod
    def send_text(self, text: str) -> Optional[str]:
        '''
        Sends a prompt and returns the reply

        Args:
            text (str): the entire prompt to send to the chat interface

        Returns:
            Optional[str]: the chat interface's response
        '''
        pass

    @abstractmethod
    def get_history(self) -> List[Tuple[str, str]]:
        '''
        Returns the complete chat history

        Returns:
            List[Tuple[str, str]]: List of (role, message) pairs
        '''
        pass

    @abstractmethod
    def reset(self) -> None:
        '''
        Resets chat to its initial state
        '''
        pass
