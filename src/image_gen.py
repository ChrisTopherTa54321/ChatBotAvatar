''' Interface for an Image Generator backend '''
import abc
from abc import abstractmethod
from typing import Optional, Tuple, List
from PIL import Image


class ImageGen(abc.ABC):

    @abstractmethod
    def gen_image(self, prompt: str, input_image: Image.Image = None, dimensions: Tuple[int, int] = (256, 256), match_img: bool = False, match_pose: bool = False, **kwargs) -> Optional[str]:
        '''
        Generate an image from a text prompt.

        Args:
            prompt (str): text prompt to generate image from
            input_image (Image.Image, optional): optional input image, can be used for img, pose or both
            dimensions (Tuple[int, int], optional): output image dimensions
            match_img (bool): use the input image as an img2img source
            match_pose (bool): use the input image as a pose source
            kwargs: additional arguments to pass to underlying Image Generator

        Returns:

        '''
