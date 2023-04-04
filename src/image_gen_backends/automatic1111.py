import webuiapi
from image_gen import ImageGen
from typing_extensions import override
from typing import Optional, Tuple
from PIL import Image
import webuiapi


class Automatic1111(ImageGen):
    BACKEND_NAME: str = "AUTOMATIC1111"

    def __init__(self, api_host: str, api_port: int):
        self._api: webuiapi.WebUIApi = webuiapi.WebUIApi(host=api_host, port=api_port)

    @override
    def gen_image(self, prompt: str, input_image: Image.Image = None, dimensions: Tuple[int, int] = (256, 256), match_img: bool = False, match_pose: bool = False, **kwargs) -> Optional[str]:
        if input_image is None or (match_img is False and match_pose is False):
            return self._txt2img(prompt=prompt, dimensions=dimensions, **kwargs)

        if input_image and match_pose:
            return self._posematch(prompt=prompt, input_image=input_image, dimensions=dimensions, match_img=match_img, **kwargs)

        if input_image and match_img:
            return self._img2img(prompt=prompt, input_image=input_image, dimensions=dimensions, **kwargs)

    def _posematch(self, prompt: str, input_image: Image.Image, dimensions: Tuple[int, int], match_img: bool, **kwargs):
        control_net: webuiapi.ControlNetUnit = webuiapi.ControlNetUnit(
            input_image=input_image, module="normal_map", model="control_normal-fp16 [63f96f7c]")

        if match_img:
            return self._img2img(prompt=prompt, input_image=input_image, dimensions=dimensions, controlnet_units=[control_net], **kwargs)
        else:
            return self._txt2img(prompt=prompt, dimensions=dimensions, controlnet_units=[control_net], **kwargs)

    def _txt2img(self, prompt: str, dimensions: Tuple[int, int], **kwargs):
        width, height = dimensions
        return self._api.txt2img(prompt=prompt, width=width, height=height, **kwargs)

    def _img2img(self, prompt: str, input_image: Image.Image, dimensions: Tuple[int, int], **kwargs):
        width, height = dimensions
        return self._api.img2img(images=[input_image], prompt=prompt, cfg_scale=6.5, denoising_strength=0.6, **kwargs)
