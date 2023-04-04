''' Handles creating Chat instances '''
from dataclasses import dataclass
from typing import Callable, Dict

from image_gen import ImageGen

# TODO: Deal with same name in different backends


class ImageGenFactory:
    @dataclass
    class ImageGenInfo:
        factory: Callable = None
    _image_gen_map: Dict[str, ImageGenInfo] = {}
    _default_image_gen: ImageGenInfo = None

    @classmethod
    def register_image_gen(cls, name: str, factory_func: Callable):
        '''
        Registers a new image generator backend.

        Args:
            name (str): name of the chat backend
            factory_func (Callable): a Callable which returns a new instance of the Image Gen
        '''
        cls._image_gen_map.setdefault(name, ImageGenFactory.ImageGenInfo()).factory = factory_func

    @classmethod
    def get_image_gen_list(cls):
        return sorted(cls._image_gen_map.keys())

    @classmethod
    def set_default_image_gen(cls, name: str):
        cls._default_image_gen = cls._image_gen_map[name]

    @classmethod
    def get_default_image_gen(cls) -> ImageGen:
        if cls._default_image_gen is None and cls._image_gen_map:
            cls._default_image_gen = next(iter(cls._image_gen_map.values()))
        return cls._default_image_gen.factory()
