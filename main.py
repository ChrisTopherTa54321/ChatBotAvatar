''' ChatBot main entry point '''
import argparse
import logging
import os
import pathlib
import time

#fmt: off
import sys
script_dir = pathlib.Path(__file__).parent.resolve()
sys.path.append(os.path.join(script_dir, "src"))

from chat import Chat
from tts import Tts
from ui import Ui

from utils.text_utils import TextUtils
#fmt: on

logging.basicConfig(stream=sys.stdout)
logger = logging.getLogger(__file__)


def parseArgs():
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
    parser.add_argument("--tts-backend", choices=["pyttsx3", "azure", "coqui"], default="pyttsx3")
    parser.add_argument("--ui-backend", choices=["gradio"], default="gradio")
    parser.add_argument("--jobs", help="Max concurrent Gradio jobs", default=3)
    parser.add_argument("--chat-backend", choices=["chatgpt"], default="chatgpt")
    parser.add_argument("--coqui-use-gpu", help="Use GPU for coqui TTS", action="store_true", default=False)
    parser.add_argument("--chat-instructions", help="Initial directions to give Chat backend",
                        default="You are an AI-driven chatbot")

    return parser.parse_args()


###############################
# program entry point
#
if __name__ == "__main__":
    logger.info("Starting program")
    args = parseArgs()
    if args.verbose:
        logging.basicConfig(stream=sys.stdout, level=logging.INFO, force=True)

    TextUtils.settings.data_dir = args.data_dir

    chat: Chat = None
    ui: Ui = None
    tts: Tts = None

    # Select Chat backend
    if args.chat_backend == "chatgpt":
        from chat_backends.chatgpt import ChatGpt
        chat = ChatGpt(api_key=args.openai_api_key, initial_instructions=args.chat_instructions)
    else:
        raise Exception(f"Unsupported chat backend: {args.chat_backend}")

    # Select TTS backend
    if args.tts_backend == "azure":
        from tts_backends.azure_tts import AzureTts
        tts = AzureTts(api_key=args.azure_api_key, api_region=args.azure_api_region)
    elif args.tts_backend == "coqui":
        from tts_backends.coqui_tts import CoquiTts
        tts = CoquiTts(use_gpu=args.coqui_use_gpu)
    elif args.tts_backend == "pyttsx3":
        from tts_backends.pyttsx3_tts import Pyttsx3Tts
        tts = Pyttsx3Tts()
    else:
        raise Exception(f"Unsupported TTS backend: {args.tts_backend}")

    # Select UI backend
    if args.ui_backend == "gradio":
        from ui_backends.gradio_ui import GradioUi
        ui = GradioUi(chat_interface=chat, tts_interface=tts, jobs=args.jobs)
    else:
        raise Exception(f"Unsupported UI backend: {args.ui_backend}")

    # Attempt to bind to each port a few times, and then increment the port
    port = args.port
    while port < args.port + args.port_increment_cnt:
        i = 0
        while i != args.bind_retry_cnt:
            try:
                ui.launch(listen=args.listen, port=port)
                exit()
            except OSError as e:
                logger.warning(f"Failed to bind port: {str(e)}")
                time.sleep(0.25)
            i += 1
        port += 1
        logger.warning(f"Trying new port {port}...")
