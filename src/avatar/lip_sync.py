''' Handles running Wav2Lip on an Avatar '''
from avatar.profile import Profile
from pathlib import Path
from typing import List
from utils.shared import Shared
import os
import subprocess
import logging
import gdown

logger = logging.getLogger(__file__)


class LipSync:
    # Taken from https://github.com/eyaler/avatars4all
    URL = "https://drive.google.com/uc?id=1dwHujX7RVNCvdR1RR93z0FS2T2yzqup9"
    CHECKPOINT = os.path.join(Shared.getInstance().data_dir, "wav2lip", "wav2lip_gan.pth")

    @classmethod
    def render(cls, input_image_or_video: Path, input_audio: Path, output_path: Path):
        '''
        Render lipsync to output file

        Args:
            output_path (Path): output path
        '''
        if not cls._check_models():
            raise Exception("Missing Wav2Lip checkpoint")

        args = ["python", "-m", "wav2lip",
                "--checkpoint_path", LipSync.CHECKPOINT,
                "--face", input_image_or_video,
                "--audio", input_audio,
                "--outfile", output_path]
        output = subprocess.check_output(args)
        logger.warn(f"{output}")

    @classmethod
    def _check_models(cls) -> bool:
        ''' Checks for and attempts to download the lipsync models. Returns true if models exist.'''
        if not os.path.exists(LipSync.CHECKPOINT):
            os.makedirs(os.path.dirname(LipSync.CHECKPOINT), exist_ok=True)
            gdown.download(url=LipSync.URL, output=LipSync.CHECKPOINT)
        return os.path.exists(LipSync.CHECKPOINT)
