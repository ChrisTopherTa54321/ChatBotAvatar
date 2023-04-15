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
sys.path.append(os.path.join(script_dir, "external", "repos"))


from utils.text_utils import TextUtils
from utils.shared import Shared
#fmt: on

logging.basicConfig(stream=sys.stdout)
logger = logging.getLogger(__file__)


###############################
# program entry point
#
if __name__ == "__main__":
    logger.info("Starting program")
    Shared.init(root_dir=script_dir)
    args = Shared.getInstance().args
    os.makedirs(args.temp_dir, exist_ok=True)

    if args.verbose:
        logging.basicConfig(stream=sys.stdout, level=logging.INFO, force=True)

    TextUtils.settings.data_dir = args.data_dir

    # Attempt to bind to each port a few times, and then increment the port
    port = args.port
    while port < args.port + args.port_increment_cnt:
        i = 0
        while i != args.bind_retry_cnt:
            try:
                Shared.getInstance().ui.launch(listen=args.listen, port=port)
                exit()
            except OSError as e:
                logger.warning(f"Failed to bind port: {str(e)}")
                time.sleep(0.25)
            i += 1
        port += 1
        logger.warning(f"Trying new port {port}...")
