''' Handles running Thin-Plate-Spline-Motion on an Avatar '''
from avatar.profile import Profile
from pathlib import Path
from typing import List
from utils.shared import Shared

from tpsmm.tpsmm.demo import parseArgs, main

import os
import subprocess
import logging
import gdown
import pkg_resources

logger = logging.getLogger(__file__)


class MotionMatch:
    # Taken from https://github.com/yoyo-nb/Thin-Plate-Spline-Motion-Model
    URL = "https://drive.google.com/uc?id=1-CKOjv_y_TzNe-dwQsjjeVxJUuyBAb5X"
    CHECKPOINT = os.path.join(Shared.getInstance().data_dir, "tpsmm", "vox.pth.tar")
    CONFIG = os.path.join("external", "repos", "tpsmm", "tpsmm",  os.path.join("config", "vox-256.yaml"))

    @classmethod
    def render(cls, source_image: Path, driving_video: Path, output_path: Path):
        '''
        Render MotionMatch to output file

        Args:
            output_path (Path): output path
        '''
        if not cls._check_models():
            raise Exception("Missing Thin Plate Spline Motion Model checkpoint")

        args = ["--checkpoint", MotionMatch.CHECKPOINT,
                "--config", MotionMatch.CONFIG,
                "--source_image", source_image,
                "--driving_video", driving_video,
                "--result_video", output_path]
        main(parseArgs(args))

    @classmethod
    def _check_models(cls) -> bool:
        if not os.path.exists(MotionMatch.CHECKPOINT):
            os.makedirs(os.path.dirname(MotionMatch.CHECKPOINT), exist_ok=True)
            gdown.download(url=MotionMatch.URL, output=MotionMatch.CHECKPOINT)
        return os.path.exists(MotionMatch.CHECKPOINT)
