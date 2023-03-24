''' Shared global configuration parameters '''
from __future__ import annotations
import argparse
import os

from image_gen import ImageGen


class Shared:
    _inst: Shared = None

    def __init__(self, root_dir: str):
        self._root_dir: str = root_dir
        self._args: argparse.Namespace = self._parse_args()

        self._image_gen: ImageGen = None

        # Select Image Generator backend
        if self._args.image_gen_backend == "automatic1111":
            from image_gen_backends.automatic1111 import Automatic1111
            self._image_gen = Automatic1111(api_host=self._args.image_gen_webui_host,
                                            api_port=self._args.image_gen_webui_port)
        else:
            raise Exception(f"Unsupported ImageGen backend: {self._args.image_gen_backend}")

    @classmethod
    def init(cls, root_dir: str):
        cls._inst = Shared(root_dir=root_dir)

    @classmethod
    def getInstance(cls):
        if not cls._inst:
            raise Exception("Not initialized")
        return cls._inst

    @property
    def args(self):
        if not self._args:
            self._args = self._parse_args()
        return self._args

    @property
    def data_dir(self):
        return os.path.join(self.root_dir, self.args.data_dir)

    @property
    def root_dir(self):
        return self._root_dir

    @root_dir.setter
    def root_dir(self, new_path: str):
        self._root_dir = new_path

    @property
    def image_gen(self):
        return self._image_gen

    def _parse_args(self):
        parser = argparse.ArgumentParser(description="ChatBot",
                                         formatter_class=argparse.ArgumentDefaultsHelpFormatter)
        parser.add_argument('--verbose', '-v', help="Verbose", action='store_true', default=False)
        parser.add_argument('--listen', help="Listen on public network interface", action='store_true', default=False)
        parser.add_argument('--port', '-p', help="Port to listen on", type=int, default=5981)
        parser.add_argument("--bind-retry-cnt",
                            help="Number of times to retry if listening port busy, -1 for infinite", default=3)
        parser.add_argument("--port-increment-cnt",
                            help="Number of times to increment port if port still busy after bind-retry-cnt", default=5)
        parser.add_argument("--openai-api-key", help="OpenAI API key", type=str,
                            default=os.getenv("OPENAI_API_KEY", "No Key Set"))
        parser.add_argument("--azure-api-key", help="Azure API key", type=str,
                            default=os.getenv("AZURE_API_KEY", ""))
        parser.add_argument("--azure-api-region", help="Azure API Region",
                            default=os.getenv("AZURE_API_REGION", "centralus"))
        parser.add_argument("--data-dir", help="Data directory",  default="models")
        parser.add_argument("--avatar-dir", help="Avatar directory",  default="avatar")
        parser.add_argument("--tts-backend", choices=["pyttsx3", "azure", "coqui"], default="pyttsx3")
        parser.add_argument("--ui-backend", choices=["gradio"], default="gradio")
        parser.add_argument("--image-gen-backend", choices=["automatic1111"], default="automatic1111")
        parser.add_argument("--image-gen-webui-host", help="Automatic1111 webui host", default="localhost")
        parser.add_argument("--image-gen-webui-port", help="Automatic1111 webui port", default="7860")
        parser.add_argument("--jobs", help="Max concurrent Gradio jobs", default=3)
        parser.add_argument("--chat-backend", choices=["chatgpt"], default="chatgpt")
        parser.add_argument("--coqui-use-gpu", help="Use GPU for coqui TTS", action="store_true", default=False)
        parser.add_argument("--chat-instructions", help="Initial directions to give Chat backend",
                            default="You are an AI-driven chatbot")
        parser.add_argument("--temp-dir", help="Directory to write temporary files", default="tmp")

        return parser.parse_args()
