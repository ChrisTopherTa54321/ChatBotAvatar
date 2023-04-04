import webuiapi
from image_gen import ImageGen
from typing_extensions import override
from typing import Optional, Tuple, List
from PIL import Image
import webuiapi
from webuiapi import ControlNetUnit


class Automatic1111(ImageGen):
    BACKEND_NAME: str = "AUTOMATIC1111"

    def __init__(self, api_host: str, api_port: int):
        self._api: webuiapi.WebUIApi = webuiapi.WebUIApi(host=api_host, port=api_port)

    @override
    def gen_image(self, prompt: str, input_image: Image.Image = None, dimensions: Tuple[int, int] = (256, 256), controlnet_units: Optional[List[ControlNetUnit]] = None, **kwargs) -> Optional[str]:
        if input_image:
            kwargs['input_image'] = input_image
            func = self._api.img2img
        else:
            func = self._api.txt2img
        kwargs['width'], kwargs['height'] = dimensions
        return func(prompt=prompt, controlnet_units=controlnet_units, **kwargs)

    @override
    def get_controlnet_models(self) -> List[str]:
        ret = self._api.custom_get("controlnet/model_list")
        return ret['model_list']

    @override
    def get_controlnet_modules(self) -> List[str]:
        ret = self._api.custom_get("controlnet/module_list")
        return ret['module_list']
