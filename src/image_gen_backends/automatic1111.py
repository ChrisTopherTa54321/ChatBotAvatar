import webuiapi
from image_gen import ImageGen
from typing_extensions import override
from typing import Optional
import webuiapi


class Automatic1111(ImageGen):
    def __init__(self, api_host: str, api_port: int):
        self._api: webuiapi.WebUIApi = webuiapi.WebUIApi(host=api_host, port=api_port)

    @override
    def gen_image(self, prompt: str) -> Optional[str]:
        return self._api.txt2img(prompt=prompt)
