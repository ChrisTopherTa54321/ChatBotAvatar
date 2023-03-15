''' ChatBot main entry point '''
import argparse
import logging
import sys
import gradio as gr

from src.webui import WebUI

logging.basicConfig(stream=sys.stdout)
logger = logging.getLogger(__file__)

# fmt: off
#sys.path.append(os.path.join(pathlib.Path(__file__), "src"))
# submodules_dir = os.path.join(pathlib.Path(__file__).parent.resolve(), "submodules")
# sys.path.append(submodules_dir)
# from src.config import Config
# from src.contextChecker import ContextChecker
# from src.mqttClient import MqttClient
# from src.watchedObject import WatchedObject
# from src.watcher import Watcher
# fmt: on


def parseArgs():
    parser = argparse.ArgumentParser(description="ChatBot",
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--verbose', '-v', help="Verbose", action='store_true', default=False)
    parser.add_argument('--listen', help="Listen on public network interface", action='store_true', default=False)
    parser.add_argument('--port', '-p', help="Port to listen on", type=int, default=5981)

    return parser.parse_args()


###############################
# program entry point
#
if __name__ == "__main__":
    logger.info("Starting program")
    args = parseArgs()
    if args.verbose:
        logging.basicConfig(stream=sys.stdout, level=logging.DEBUG, force=True)

    with gr.Blocks() as app:
        ui = WebUI(args)
        ui.buildInterface()
        server_name = "0.0.0.0" if args.listen else None
        app.launch(server_name="0.0.0.0", server_port=args.port)
