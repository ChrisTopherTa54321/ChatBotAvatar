''' Interface for an Image Generator backend '''
import abc
from abc import abstractmethod
from typing import Optional, Tuple, List


class ImageGen(abc.ABC):

    @abstractmethod
    def gen_image(self, prompt: str) -> Optional[str]:
        pass
