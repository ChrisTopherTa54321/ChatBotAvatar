''' ChatBot main entry point '''
import argparse
import logging
import os
import sys
import gradio as gr
import pathlib
import glob

from src.textutils import TextUtils
from src.webui import WebUI
from src.chatgpt import ChatGpt
from src.azuretts import AzureTts

logging.basicConfig(stream=sys.stdout)
logger = logging.getLogger(__file__)

script_dir = pathlib.Path(__file__).parent.resolve()


def parseArgs():
    parser = argparse.ArgumentParser(description="ChatBot",
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--verbose', '-v', help="Verbose", action='store_true', default=False)
    parser.add_argument('--listen', help="Listen on public network interface", action='store_true', default=False)
    parser.add_argument('--port', '-p', help="Port to listen on", type=int, default=5981)
    parser.add_argument("--openai-api-key", help="OpenAI API key", type=str,
                        default=os.getenv("OPENAI_API_KEY", "No Key Set"))
    parser.add_argument("--azure-api-key", help="Azure API key", type=str,
                        default=os.getenv("AZURE_API_KEY", "No Key Set"))
    parser.add_argument("--azure-api-region", help="Azure API Region",
                        default=os.getenv("AZURE_API_REGION", "centralus"))
    parser.add_argument("--data_dir", help="Data directory",  default="models")

    return parser.parse_args()


###############################
# program entry point
#
if __name__ == "__main__":
    logger.info("Starting program")
    args = parseArgs()
    if args.verbose:
        logging.basicConfig(stream=sys.stdout, level=logging.DEBUG, force=True)

    scripts = glob.glob(os.path.join(script_dir, "javascript", "*.js"))

    with gr.Blocks() as app:
        TextUtils.settings.data_dir = args.data_dir
        chatGpt = ChatGpt(api_key=args.openai_api_key)
        azureTts = AzureTts(api_key=args.azure_api_key, api_region=args.azure_api_region)
        ui = WebUI(chatInterface=chatGpt, ttsInterface=azureTts, args=args)
        ui.buildInterface()
        ui.injectScripts(scripts)
        server_name = "0.0.0.0" if args.listen else None
        app.launch(server_name="0.0.0.0", server_port=args.port)
