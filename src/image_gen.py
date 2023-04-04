''' Interface for an Image Generator backend '''
import abc
from abc import abstractmethod
from typing import List, Optional, Tuple

from PIL import Image
from webuiapi import ControlNetUnit


class ImageGen(abc.ABC):

    @abstractmethod
    def gen_image(self, prompt: str, input_image: Image.Image = None, dimensions: Tuple[int, int] = (256, 256), controlnet_units: Optional[List[ControlNetUnit]] = None, **kwargs) -> Optional[str]:
        '''
        Generate an image from a text prompt.

        Args:
            prompt (str): text prompt to generate image from
            input_image (Image.Image, optional): optional input image, can be used for img, pose or both
            dimensions (Tuple[int, int], optional): output image dimensions
            controlnet_units (List[ControlNetUnits]): ControlNet models to use
            kwargs: additional arguments to pass to underlying Image Generator

        Returns:

        '''

    @abstractmethod
    def get_controlnet_models(self) -> List[str]:
        '''
        Returns a list of available ControlNet models
        '''

    @abstractmethod
    def get_controlnet_modules(self) -> List[str]:
        '''
        Returns a list of available ControlNet modules
        '''
