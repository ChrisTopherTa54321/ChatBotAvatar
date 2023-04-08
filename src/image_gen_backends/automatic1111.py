import webuiapi
from image_gen import ImageGen
from typing_extensions import override
from typing import Optional, Tuple, List, Callable
from PIL import Image
import webuiapi
from webuiapi import ControlNetUnit
import inspect


class Automatic1111(ImageGen):
    BACKEND_NAME: str = "AUTOMATIC1111"

    def __init__(self, api_host: str, api_port: int):
        self._api: webuiapi.WebUIApi = webuiapi.WebUIApi(host=api_host, port=api_port)
        self._model_cache: List[str] = []
        self._module_cache: List[str] = []

    @override
    def gen_image(self, prompt: str, input_image: Image.Image = None, dimensions: Tuple[int, int] = (256, 256), controlnet_units: Optional[List[ControlNetUnit]] = None, **kwargs) -> Optional[str]:
        if input_image:
            kwargs['input_image'] = input_image
            func = self._api.img2img
        else:
            func = self._api.txt2img

        width, height = dimensions
        kwargs.setdefault('width', width)
        kwargs.setdefault('height', height)
        kwargs['prompt'] = prompt
        kwargs['controlnet_units'] = controlnet_units
        return func(**kwargs)

    @override
    def get_controlnet_models(self) -> List[str]:
        if len(self._model_cache) == 0:
            ret = self._api.custom_get("controlnet/model_list")
            self._model_cache = ret["model_list"]
        return self._model_cache.copy()

    @override
    def get_controlnet_modules(self) -> List[str]:
        if len(self._module_cache) == 0:
            ret = self._api.custom_get("controlnet/module_list")
            self._module_cache = ret["module_list"]
        return self._module_cache.copy()

    @override
    def get_txt2img_method(self) -> Callable:
        return webuiapi.WebUIApi.txt2img

    @override
    def get_img2img_method(self) -> Callable:
        return webuiapi.WebUIApi.img2img
