''' Utilities for images '''

from pathlib import Path
from typing import Callable, Tuple, Union

import numpy as np
from PIL import Image


class ImageUtils:
    @classmethod
    def open_or_blank(cls, image: Union[Path, np.ndarray, Image.Image], dimensions: Tuple[int, int] = (256, 256)) -> Image.Image:
        '''
        Attempts to open an image and return it as an np.ndarray, or ar blank image on failure

        Args:
            image_path (str): path to image to open
            dimensions (Tuple[int, int], optional): dimensions of image on failure

        Returns:
            np.ndarray: output image as array
        '''
        try:
            return ImageUtils.image_data(image)
        except Exception as e:
            return Image.new("RGB", size=dimensions)

    @classmethod
    def copy_or_save(cls, image: Union[Path, np.ndarray, Image.Image], output_path: Path):
        '''
        Saves image to output_path

        Args:
            image (Union[Path, np.ndarray]): image to save, either a path to copy or a memory buffer to save
            output_path (Path): output file name
        '''
        output_path = Path(output_path)
        image_data = ImageUtils.image_data(image)
        image_data.save(output_path)

    @classmethod
    def image_data(cls, image: Union[Path, np.ndarray, Image.Image]) -> Image.Image:
        if isinstance(image, np.ndarray):
            return Image.fromarray(image)
        elif isinstance(image, Image.Image):
            return image
        image = Path(image)
        return Image.open(image)
