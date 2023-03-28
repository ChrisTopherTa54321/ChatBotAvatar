''' Shared global configuration parameters '''
from __future__ import annotations
import argparse
import os

from image_gen import ImageGen
from chat import Chat
from tts import Tts
from ui import Ui
from avatar.manager import Manager
from utils.voice_factory import VoiceFactory
from typing import Dict, Any, Type


class Shared:
    _inst: Shared = None

    def __init__(self, root_dir: str):
        self._root_dir: str = root_dir
        self._args: argparse.Namespace = self._parse_args()

        self._image_gen: ImageGen = None
        self._voice_factory: VoiceFactory = None
        self._ui: Ui = None
        self._chat: Chat = None

        self._data: Dict[Any, Any] = {}

        self._avatar_manager: Manager = Manager(avatar_dir=self._args.avatar_dir)

    def _init_from_settings(self, args: argparse.Namespace):
        ''' Load backends for items specified in params'''
        # Select Image Generator backend
        if args.image_gen_backend == "automatic1111":
            from image_gen_backends.automatic1111 import Automatic1111
            self._image_gen = Automatic1111(api_host=args.image_gen_webui_host,
                                            api_port=args.image_gen_webui_port)
        else:
            raise Exception(f"Unsupported ImageGen backend: {args.image_gen_backend}")

        # Select Chat backend
        if args.chat_backend == "chatgpt":
            from chat_backends.chatgpt import ChatGpt
            self._chat = ChatGpt(api_key=args.openai_api_key, initial_instructions=args.chat_instructions)
        else:
            raise Exception(f"Unsupported chat backend: {args.chat_backend}")

        # Select TTS backend
        self._voice_factory = VoiceFactory()
        if args.tts_backend == "azure":
            from tts_backends.azure_tts import AzureTts
            tts = AzureTts(api_key=args.azure_api_key, api_region=args.azure_api_region)
            self._voice_factory.register_tts(AzureTts.BACKEND_NAME, tts)
        elif args.tts_backend == "coqui":
            from tts_backends.coqui_tts import CoquiTts
            tts = CoquiTts(use_gpu=args.coqui_use_gpu)
            self._voice_factory.register_tts(CoquiTts.BACKEND_NAME, tts)
        elif args.tts_backend == "pyttsx3":
            from tts_backends.pyttsx3_tts import Pyttsx3Tts
            tts = Pyttsx3Tts()
            self._voice_factory.register_tts(Pyttsx3Tts.BACKEND_NAME, tts)
        else:
            raise Exception(f"Unsupported TTS backend: {args.tts_backend}")

        # Select UI backend
        if args.ui_backend == "gradio":
            from ui_backends.gradio_ui import GradioUi
            self._ui = GradioUi(jobs=args.jobs)
        else:
            raise Exception(f"Unsupported UI backend: {args.ui_backend}")

    @classmethod
    def init(cls, root_dir: str):
        cls._inst = Shared(root_dir=root_dir)
        cls._inst._init_from_settings(cls._inst.args)

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

    def get_data(self, key: Any, class_type: Type) -> Any:
        return self._data.setdefault(key, class_type())

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
    def image_gen(self) -> ImageGen:
        return self._image_gen

    @property
    def chat(self) -> Chat:
        return self._chat

    @property
    def ui(self) -> Ui:
        return self._ui

    @property
    def avatar_manager(self) -> Manager:
        return self._avatar_manager

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
