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

# Taken from https://github.com/eyaler/avatars4all
URL = "https://drive.google.com/uc?id=1dwHujX7RVNCvdR1RR93z0FS2T2yzqup9"
CHECKPOINT = os.path.join(Shared.getInstance().data_dir, "wav2lip", "wav2lip_gan.pth")


class LipSync:
    def __init__(self, profile: Profile, wav_filename: Path):
        ''' Initialize a LipSync object with a profile and the audio file '''
        self._profile: Profile = profile
        self._wav_file: Path = Path(wav_filename)

        if not os.path.exists(CHECKPOINT):
            gdown.download(url=URL, output=CHECKPOINT)

    def render(self, output_path: Path):
        '''
        Render lipsync to output file

        Args:
            output_path (Path): output path
        '''
        args = ["python", "-m", "wav2lip",
                "--checkpoint_path", CHECKPOINT,
                "--face", self._profile.preview_image,
                "--audio", self._wav_file,
                "--outfile", output_path]
        output = subprocess.check_output(args)
        logger.warn(f"{output}")
        pass
