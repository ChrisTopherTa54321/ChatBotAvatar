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

    @abstractmethod
    def get_history(self) -> List[Tuple[str, str]]:
        '''
        Returns the complete chat history

        Returns:
            List[Tuple[str, str]]: List of (role, message) pairs
        '''

    @abstractmethod
    def pop_history_item(self, idx: int) -> Tuple[str, str]:
        '''
        Removes and returns an item from the history, by indexx

        Args:
            idx (int): index of history item to remove

        Returns:
            Tuple[str, str]: the item removed
        '''

    @abstractmethod
    def reset(self) -> None:
        '''
        Resets chat to its initial state
        '''
