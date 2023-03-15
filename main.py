''' ChatBot main entry point '''
import argparse
import logging
import os
import sys
import pathlib
import glob
import time

from src.text_utils import TextUtils
from src.webui import WebUI
from src.chatgpt import ChatGpt
from src.azure_tts import AzureTts
from src.pyttsx3_tts import Pyttsx3Tts

logging.basicConfig(stream=sys.stdout)
logger = logging.getLogger(__file__)

script_dir = pathlib.Path(__file__).parent.resolve()


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
    parser.add_argument("--jobs", help="Max concurrent Gradio jobs", default=3)

    return parser.parse_args()


###############################
# program entry point
#
if __name__ == "__main__":
    logger.info("Starting program")
    args = parseArgs()
    if args.verbose:
        logging.basicConfig(stream=sys.stdout, level=logging.INFO, force=True)

    scripts = glob.glob(os.path.join(script_dir, "javascript", "*.js"))

    TextUtils.settings.data_dir = args.data_dir
    chatGpt = ChatGpt(api_key=args.openai_api_key)
    if args.azure_api_key:
        tts = AzureTts(api_key=args.azure_api_key, api_region=args.azure_api_region)
    else:
        tts = Pyttsx3Tts()
    ui = WebUI(chatInterface=chatGpt, ttsInterface=tts)
    ui.buildInterface()
    ui.injectScripts(scripts)

    # Attempt to bind to each port a few times, and then increment the port
    port = args.port
    while port < args.port + args.port_increment_cnt:
        i = 0
        while i != args.bind_retry_cnt:
            try:
                ui.run(listen=args.listen, port=port, jobs=args.jobs)
                exit()
            except OSError as e:
                logger.warning(f"Failed to bind port: {str(e)}")
                time.sleep(0.25)
            i += 1
        port += 1
        logger.warning(f"Changing to port {port}...")
