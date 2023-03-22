''' Shared global configuration parameters '''
from __future__ import annotations
import argparse
import os


class Shared:
    _inst: Shared = None

    def __init__(self):
        self._args: argparse.Namespace = None
        self._root_dir: str = None

    @classmethod
    def getInstance(cls):
        if not Shared._inst:
            Shared._inst = Shared()
        return Shared._inst

    @property
    def args(self):
        if not self._args:
            self._args = self._parse_args()
        return self._args

    @property
    def root_dir(self):
        return self._root_dir

    @root_dir.setter
    def root_dir(self, new_path: str):
        self._root_dir = new_path

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
        parser.add_argument("--jobs", help="Max concurrent Gradio jobs", default=3)
        parser.add_argument("--chat-backend", choices=["chatgpt"], default="chatgpt")
        parser.add_argument("--coqui-use-gpu", help="Use GPU for coqui TTS", action="store_true", default=False)
        parser.add_argument("--chat-instructions", help="Initial directions to give Chat backend",
                            default="You are an AI-driven chatbot")
        parser.add_argument("--temp-dir", help="Directory to write temporary files",
                            default=os.path.join(self.root_dir, "tmp"))

        return parser.parse_args()
