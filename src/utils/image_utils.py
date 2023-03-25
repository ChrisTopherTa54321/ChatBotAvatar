''' Utilities for images '''

from typing import List, Callable, Tuple, Union
import numpy as np
import os


class ImageUtils:
    @classmethod
    def open_or_blank(cls, image_path: str, dimensions: Tuple[int, int] = (256, 256)) -> Union[str, np.ndarray]:
        '''
        Attempts to open an image and return it as an np.ndarray, or ar blank image on failure

        Args:
            image_path (str): path to image to open
            dimensions (Tuple[int, int], optional): dimensions of image on failure

        Returns:
            np.ndarray: output image as array
        '''
        if os.path.exists(image_path):
            return image_path
        return np.zeros(dimensions)
